from .web_service import WebService

class RegisterScopeThirteen(WebService):
  soapv12 = False
  WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"
  URL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13"
  WSDL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"
  URL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13"

  def __init__(self, afip):
    super(RegisterScopeThirteen, self).__init__(afip, { "service": "ws_sr_padron_a13" })

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

  # Asks to web service for tax id by document number
  def getTaxIDByDocument(self, document_number: int):
    # Get token and sign
    ta = self.getTokenAuthorization()

    # Prepare params
    params = {
      "token": ta["token"],
      "sign": ta["sign"],
      "cuitRepresentada": self.afip.CUIT,
      "documento": document_number
    }

    return self.executeRequest("getIdPersonaListByDocumento", params)["idPersona"]

  # Asks to web service for servers status
  def getServerStatus(self):
    return self.executeRequest("dummy")

  # Send request to AFIP servers
  def executeRequest(self, operation, params = {}):
    results = super(RegisterScopeThirteen, self).executeRequest(operation, params)

    if operation == "getPersona":
      return results["personaReturn"]
    elif operation == "getIdPersonaListByDocumento":
      return results["idPersonaListReturn"]
    else:
      return results["return"]
