import http.client
import json

from .web_service import WebService
from .electronic_billing import ElectronicBilling
from .register_inscription_proof import RegisterInscriptionProof
from .register_scope_ten import RegisterScopeTen
from .register_scope_thirteen import RegisterScopeThirteen

class Afip:
  sdk_version_number = '1.0.0'

  def __init__(self, options: dict):
    if not(options.get("CUIT")):
      raise Exception("CUIT field is required in options")

    self.CUIT: int = options.get("CUIT")
    self.production: bool = options.get("production") if options.get("production") == True else False
    self.environment: str = "prod" if self.production == True else "dev"
    self.cert: str = options.get("cert")
    self.key: str = options.get("key")
    self.access_token: str = options.get("access_token")
  
    self.ElectronicBilling = ElectronicBilling(self)
    self.RegisterInscriptionProof = RegisterInscriptionProof(self)
    self.RegisterScopeTen = RegisterScopeTen(self)
    self.RegisterScopeThirteen = RegisterScopeThirteen(self)


  # Gets token authorization for an AFIP Web Service
  #
  # If force is true it forces to create a new TA
  def getServiceTA(self, service: str, force: bool = False) -> dict:
    conn = http.client.HTTPSConnection("app.afipsdk.com")

    payload = {
      "environment": self.environment,
      "tax_id": self.CUIT,
      "wsid": service,
      "force_create": force
    }

    if self.cert: payload["cert"] = self.cert
    if self.key: payload["key"] = self.key

    headers = {
      "Content-Type": "application/json",
      "sdk-version-number": self.sdk_version_number,
      "sdk-library": "python",
      "sdk-environment": self.environment
    }

    if self.access_token: headers["Authorization"] = "Bearer %s" % self.access_token

    conn.request("POST", "/api/v1/afip/auth", json.dumps(payload), headers)

    res = conn.getresponse()
    
    data = res.read()

    if res.getcode() >= 400:
      raise Exception(data.decode("utf-8"))

    return json.loads(data.decode("utf-8"))
  
  # Get last request and last response XML
  def getLastRequestXML(self) -> dict:
    conn = http.client.HTTPSConnection("app.afipsdk.com")

    headers = {
      "Content-Type": "application/json",
      "sdk-version-number": self.sdk_version_number,
      "sdk-library": "python",
      "sdk-environment": self.environment
    }

    if self.access_token: headers["Authorization"] = "Bearer %s" % self.access_token

    conn.request("GET", "/api/v1/afip/requests/last-xml", None, headers)

    res = conn.getresponse()
    
    data = res.read()

    if res.getcode() >= 400:
      raise Exception(data.decode("utf-8"))

    return json.loads(data.decode("utf-8"))
  

  # Create generic Web Service
  def webService(self, service, options: dict = {}) -> WebService:
    options['service'] = service
    options['generic'] = True

    return WebService(self, options)