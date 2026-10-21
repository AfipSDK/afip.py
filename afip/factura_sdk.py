import hashlib
import hmac
import http.client
import json
import time
from urllib.parse import urlencode, urlsplit

# Automations (ARCA with the tax password, verification) take from seconds to a couple of minutes;
# an invoice is authorized in the background in seconds
AUTOMATION_INTERVAL = 3
AUTOMATION_ATTEMPTS = 60
INVOICE_INTERVAL = 2
INVOICE_ATTEMPTS = 60

PENDING_INVOICE_STATUSES = ("queued", "processing")


class FacturaSDKError(Exception):
  """Error of the Factura SDK API

  Carries the HTTP status and the body of the response: `message`, the problems by field in
  `data_errors` and the rules the invoice did not meet in `errors`
  (https://afipsdk.com/docs/facturasdk/errors)
  """

  def __init__(self, message: str, status: int = None, data=None):
    super().__init__(message)

    # HTTP status of the response
    self.status = status
    # Decoded body of the response
    self.data = data

    # A failed automation answers { status: 'error', data: { message, data_errors, errors } }
    detail = _detail_of(data)

    # Problems by field, nested like the request, or None
    self.data_errors = detail.get("data_errors") if isinstance(detail.get("data_errors"), dict) else None
    # Rules that were not met, each with code and message, or None
    self.errors = detail.get("errors") if isinstance(detail.get("errors"), list) else None

  # Build the error from a failed response of the API
  @classmethod
  def fromResponse(cls, status: int, body):
    text = body.decode("utf-8") if isinstance(body, bytes) else (body or "")

    try:
      data = json.loads(text) if text else None
    except ValueError:
      data = None

    detail = _detail_of(data)
    parts = []

    if detail.get("message"):
      parts.append(detail["message"])

    if isinstance(detail.get("errors"), list):
      parts.extend("%s: %s" % (error.get("code"), error.get("message")) for error in detail["errors"])

    if isinstance(detail.get("data_errors"), dict):
      parts.extend(_flatten_data_errors(detail["data_errors"]))

    if parts:
      message = " ".join(parts)
    elif data is None and text:
      message = text
    else:
      message = "Factura SDK respondió %s" % status

    return cls(message, status, data)


# Where the message, data_errors and errors live in a body: the body itself, or `data` when the
# body is a failed automation
def _detail_of(data):
  if not isinstance(data, dict):
    return {}

  if data.get("status") == "error" and isinstance(data.get("data"), dict):
    return data["data"]

  return data


# { receiver: { vat_condition: 'mensaje' } } -> ['receiver.vat_condition: mensaje']
def _flatten_data_errors(errors: dict, prefix: str = ""):
  lines = []

  for field, value in errors.items():
    path = "%s.%s" % (prefix, field) if prefix else field

    if isinstance(value, dict):
      lines.extend(_flatten_data_errors(value, path))
    else:
      lines.append("%s: %s" % (path, value))

  return lines


class FacturaSDK:
  """SDK for Factura SDK: electronic invoicing end to end

  Issuers, certificates, invoices and webhooks of a Factura SDK project. The access token
  (fsk_dev_… for the sandbox, fsk_prod_… for production) decides the environment.

  https://afipsdk.com/docs/facturasdk/
  """

  # Base URL of the Factura SDK API
  api_url = "https://app.afipsdk.com/api/v1"
  timeout = 30

  def __init__(self, afip):
    self.afip = afip

    # Own token when the project of Afip SDK is another one; otherwise the access token of Afip
    self.access_token: str = getattr(afip, "facturasdk_access_token", None) or afip.access_token

    # Environment reported to the API: the one of the token when it is a Factura SDK token
    if self.access_token and self.access_token.startswith("fsk_prod_"):
      self.environment = "prod"
    elif self.access_token and self.access_token.startswith("fsk_dev_"):
      self.environment = "dev"
    else:
      self.environment = afip.environment

  # Invoices

  # Issue an invoice
  #
  # By default Factura SDK answers right away with the invoice queued and authorizes it in ARCA in
  # the background: the result arrives at your webhook. With wait the method polls until the
  # invoice is decided; with "sync": True in the data Factura SDK decides it within the request.
  # idempotency_key identifies the sale in your system: repeating it returns the same invoice
  # instead of issuing another one
  def createInvoice(self, data: dict, idempotency_key: str = None, wait: bool = False) -> dict:
    headers = { "Idempotency-Key": idempotency_key } if idempotency_key else None

    invoice = self._request("POST", "invoices", data, headers=headers)

    if wait and invoice.get("status") in PENDING_INVOICE_STATUSES:
      return self.waitForInvoice(invoice["id"])

    return invoice

  # Get an invoice with its current status. With wait, waits until it reaches a final status
  def getInvoice(self, id: str, wait: bool = False) -> dict:
    if wait:
      return self.waitForInvoice(id)

    return self._request("GET", "invoices/%s" % id)

  # Wait for an invoice to be decided: approved, rejected or failed
  #
  # Polls the invoice every 2 seconds for up to 2 minutes. The invoice keeps its course in
  # Factura SDK if the wait ends; the result still arrives at your webhook
  def waitForInvoice(self, id: str) -> dict:
    attempts = INVOICE_ATTEMPTS

    while attempts > 0:
      attempts -= 1

      invoice = self._request("GET", "invoices/%s" % id)

      if invoice.get("status") not in PENDING_INVOICE_STATUSES:
        return invoice

      time.sleep(INVOICE_INTERVAL)

    raise Exception("Error: Waiting for too long")

  # List invoices, newest first, with cursor pagination
  #
  # Filters: issuer_cuit, status, invoice_type, start, end, limit, cursor
  def getInvoices(self, params: dict = None) -> dict:
    return self._request("GET", "invoices", params=params)

  # Cancel an invoice that is still queued. It never gets issued
  def cancelInvoice(self, id: str) -> dict:
    return self._request("POST", "invoices/%s/cancel" % id)

  # Issuers

  # Create an issuer: a tax id that invoices. It is created pending and invoices once verified
  def createIssuer(self, data: dict) -> dict:
    return self._request("POST", "issuers", data)

  # Get an issuer
  def getIssuer(self, id: str) -> dict:
    return self._request("GET", "issuers/%s" % id)

  # List issuers, with cursor pagination
  #
  # Filters: tax_id, certificate_id, status, limit, cursor
  def getIssuers(self, params: dict = None) -> dict:
    return self._request("GET", "issuers", params=params)

  # Update an issuer: only the fields sent change
  def updateIssuer(self, id: str, data: dict) -> dict:
    return self._request("PUT", "issuers/%s" % id, data)

  # Delete an issuer. Its invoices remain
  def deleteIssuer(self, id: str) -> None:
    self._request("DELETE", "issuers/%s" % id)

  # Get the data of a tax id from its registration certificate in ARCA, to create the issuer
  # without typing them
  def lookupIssuer(self, tax_id) -> dict:
    return self._request("GET", "issuers/lookup", params={ "tax_id": tax_id })

  # List the sales points of a tax id in ARCA, with its tax password (tax_id, username, password)
  #
  # It is an automation: with wait returns it finished, with the sales points in "data"
  def getSalesPoints(self, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "issuers/sales-points", data), wait)

  # Create in ARCA a sales point for web services for a tax id, with its tax password (tax_id,
  # username, password and optionally vat_condition, number, name, system)
  #
  # It is an automation: with wait returns it finished, with the sales point in "data"
  def createSalesPoint(self, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "issuers/sales-points/create", data), wait)

  # Create a certificate for the issuer and assign it
  #
  # Uploaded (cert and key in PEM) it answers the certificate. Created in ARCA (source
  # "automation", with username and password) it is an automation: with wait returns it finished,
  # with the certificate in "data"
  def createIssuerCertificate(self, id: str, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "issuers/%s/certificate" % id, data), wait)

  # Accept in ARCA the delegation of the issuer to the owner of its certificate and authorize the
  # certificate to invoice for it, with the tax password of the certificate owner (username,
  # password)
  #
  # It is an automation: with wait returns it finished
  def createIssuerDelegation(self, id: str, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "issuers/%s/delegation" % id, data), wait)

  # Verify an issuer: issues a $1 invoice and the credit note that cancels it, and the issuer
  # becomes active. In production both vouchers are real
  #
  # It is an automation: with wait returns it finished, with verified, issuer, invoice and
  # credit_note in "data"
  def verifyIssuer(self, id: str, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "issuers/%s/verify" % id), wait)

  # Certificates

  # Add a certificate to the project
  #
  # Uploaded (cert and key in PEM) it answers the certificate. Created in ARCA (source
  # "automation", with tax_id, username and password) it is an automation: with wait returns it
  # finished, with the certificate in "data"
  def createCertificate(self, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "certificates", data), wait)

  # Get a certificate
  def getCertificate(self, id: str) -> dict:
    return self._request("GET", "certificates/%s" % id)

  # List certificates, with cursor pagination
  #
  # Filters: tax_id, status, limit, cursor
  def getCertificates(self, params: dict = None) -> dict:
    return self._request("GET", "certificates", params=params)

  # Revoke a certificate: it no longer signs
  def revokeCertificate(self, id: str) -> dict:
    return self._request("POST", "certificates/%s/revoke" % id)

  # Authorize a certificate in ARCA for the electronic billing web service (wsfe), with the tax
  # password of its owner (password and optionally username)
  #
  # It is an automation: with wait returns it finished
  def authorizeCertificate(self, id: str, data: dict, wait: bool = True) -> dict:
    return self._automation(self._request("POST", "certificates/%s/authorize" % id, data), wait)

  # Webhooks

  # Create the webhook endpoint (url): the URL where Factura SDK posts the result of each
  # invoice. The answer brings the secret, shown only this once
  def createWebhookEndpoint(self, data: dict) -> dict:
    return self._request("POST", "webhook-endpoints", data)

  # Get a webhook endpoint
  def getWebhookEndpoint(self, id: str) -> dict:
    return self._request("GET", "webhook-endpoints/%s" % id)

  # List webhook endpoints
  #
  # Filters: status
  def getWebhookEndpoints(self, params: dict = None) -> dict:
    return self._request("GET", "webhook-endpoints", params=params)

  # Update a webhook endpoint: url or status (active or inactive)
  def updateWebhookEndpoint(self, id: str, data: dict) -> dict:
    return self._request("PUT", "webhook-endpoints/%s" % id, data)

  # Generate a new secret for a webhook endpoint. From then on every delivery is signed with it
  def rotateWebhookEndpointSecret(self, id: str) -> dict:
    return self._request("POST", "webhook-endpoints/%s/rotate" % id)

  # Send a signed test event to a webhook endpoint
  def testWebhookEndpoint(self, id: str) -> dict:
    return self._request("POST", "webhook-endpoints/%s/test" % id)

  # List the deliveries of a webhook endpoint: what was sent, when and with what result
  #
  # Filters: status, invoice_id, limit, cursor
  def getWebhookDeliveries(self, id: str, params: dict = None) -> dict:
    return self._request("GET", "webhook-endpoints/%s/deliveries" % id, params=params)

  # Verify the signature of a webhook delivery
  #
  # The X-FacturaSDK-Signature header is "t=<timestamp>,v1=<signature>", where v1 is the
  # HMAC-SHA256 of "<timestamp>.<body>" with the secret of the endpoint. The body has to be the
  # raw one received, byte by byte. tolerance is how many seconds the timestamp may differ from now
  def verifyWebhookSignature(self, signature: str, body, secret: str, tolerance: int = 300) -> bool:
    if not isinstance(signature, str) or not secret:
      return False

    parts = dict(part.split("=", 1) if "=" in part else (part, "") for part in signature.split(","))

    try:
      timestamp = int(parts.get("t", ""))
    except ValueError:
      return False

    received = parts.get("v1", "")
    payload = body if isinstance(body, bytes) else str(body).encode("utf-8")

    expected = hmac.new(secret.encode("utf-8"), ("%d." % timestamp).encode("utf-8") + payload, hashlib.sha256).hexdigest()

    fresh = abs(int(time.time()) - timestamp) <= tolerance

    return fresh and hmac.compare_digest(expected, received)

  # Verify the signature of a webhook delivery and parse its event (event_id, type, created, data)
  #
  # Raises FacturaSDKError if the signature is not valid
  def constructWebhookEvent(self, body, signature: str, secret: str, tolerance: int = 300) -> dict:
    if not self.verifyWebhookSignature(signature, body, secret, tolerance):
      raise FacturaSDKError("La firma del webhook no es válida")

    return json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)

  # Automations

  # Get an automation. With wait, waits for it to finish
  #
  # Raises FacturaSDKError if the automation finished with an error
  def getAutomation(self, id: str, wait: bool = False) -> dict:
    if wait:
      return self.waitForAutomation(id)

    return self._request("GET", "automations/%s" % id)

  # Wait for an automation to finish. Polls it every 3 seconds for up to 3 minutes
  #
  # Raises FacturaSDKError if the automation finished with an error
  def waitForAutomation(self, id: str) -> dict:
    attempts = AUTOMATION_ATTEMPTS

    while attempts > 0:
      attempts -= 1

      automation = self._request("GET", "automations/%s" % id)

      if automation.get("status") != "in_process":
        return automation

      time.sleep(AUTOMATION_INTERVAL)

    raise Exception("Error: Waiting for too long")

  # Resolve the answer of an endpoint that may start an automation: when it did (202 with
  # automation_id) and wait is set, waits for it to finish
  def _automation(self, result, wait: bool):
    if wait and isinstance(result, dict) and result.get("automation_id"):
      return self.waitForAutomation(result["automation_id"])

    return result

  # Send a request to the Factura SDK API. Raises FacturaSDKError if the API answers an error
  def _request(self, method: str, path: str, data: dict = None, params: dict = None, headers: dict = None):
    url = urlsplit(self.api_url)
    target = "%s/%s" % (url.path.rstrip("/"), path)

    if params:
      target += "?" + urlencode(params)

    connection_class = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(url.hostname, url.port, timeout=self.timeout)

    request_headers = {
      "Content-Type": "application/json",
      "sdk-version-number": self.afip.sdk_version_number,
      "sdk-library": "python",
      "sdk-environment": self.environment
    }

    if self.access_token: request_headers["Authorization"] = "Bearer %s" % self.access_token
    if headers: request_headers.update(headers)

    try:
      connection.request(method, target, json.dumps(data) if data is not None else None, request_headers)

      response = connection.getresponse()
      status = response.status
      body = response.read()
    finally:
      connection.close()

    if status >= 400:
      raise FacturaSDKError.fromResponse(status, body)

    return json.loads(body.decode("utf-8")) if body else None
