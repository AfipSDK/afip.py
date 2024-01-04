from .web_service import WebService

class RegisterScopeTen(WebService):
  soapv12 = False
  WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL"
  URL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA10"
  WSDL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL"
  URL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10"

  def __init__(self, afip):
    super(RegisterScopeTen, self).__init__(afip, { "service": "ws_sr_padron_a10" })

  # Asks to web service for taxpayer details
  def getTaxpayerDetails(self, identifier: int):
    # Get token and sign
    ta = self.getTokenAuthorization()

    # Prepare params
    params = {
      "token": ta["token"],
      "sign": ta["sign"],
      "cuitRepresentada": self.afip.CUIT,
      "idPersona": identifier
    }

    return self.executeRequest("getPersona", params)

  # Asks to web service for servers status
  def getServerStatus(self):
    return self.executeRequest("dummy")

  # Send request to AFIP servers
  def executeRequest(self, operation, params = {}):
    results = super(RegisterScopeTen, self).executeRequest(operation, params)

    if operation == "getPersona":
      return results["personaReturn"]
    else:
      return results["return"]
