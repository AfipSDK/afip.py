import http.client
import json

class WebService:
  def __init__(self, afip, options: dict = {}):
    self.afip = afip
    self.options = options
    self.WSDL = options.get('WSDL')
    self.URL = options.get('URL')
    self.WSDL_TEST = options.get('WSDL_TEST')
    self.URL_TEST = options.get('URL_TEST')
    self.soapv12 = options.get('soapV1_2')

    if not(options.get('service')):
      raise Exception("service field is required in options")
    
  # Gets token authorization for an AFIP Web Service
  #
  # If force is true it forces to create a new TA
  def getTokenAuthorization(self, force = False) -> dict:
    return self.afip.getServiceTA(self.options.get('service'), force)

  # Sends request to AFIP servers
  def executeRequest(self, method, params = {}) -> dict:
    conn = http.client.HTTPSConnection("app.afipsdk.com")

    payload = {
      "method": method,
      "params": params,
      "environment": self.afip.environment,
      "wsid": self.options.get('service'),
      "url": self.URL if self.afip.production else self.URL_TEST,
      "wsdl": self.WSDL if self.afip.production else self.WSDL_TEST,
      "soap_v_1_2": self.soapv12
    }

    headers = {
      "Content-Type": "application/json",
      "sdk-version-number": self.afip.sdk_version_number,
      "sdk-library": "python",
      "sdk-environment": self.afip.environment
    }

    if self.afip.access_token: headers["Authorization"] = "Bearer %s" % self.afip.access_token

    conn.request("POST", "/api/v1/afip/requests", json.dumps(payload), headers)

    res = conn.getresponse()
    
    data = res.read()

    if res.getcode() >= 400:
      raise Exception(data.decode("utf-8"))

    return json.loads(data.decode("utf-8"))