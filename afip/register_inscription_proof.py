from .web_service import WebService

class RegisterInscriptionProof(WebService):
  soapv12 = False
  WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL"
  URL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5"
  WSDL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL"
  URL_TEST = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5"
  
  def __init__(self, afip):
    super(RegisterInscriptionProof, self).__init__(afip, { "service": "ws_sr_constancia_inscripcion" })

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

    return self.executeRequest("getPersona_v2", params)

  # Asks to web service for taxpayers details
  def getTaxpayersDetails(self, identifiers: list):
    # Get token and sign
    ta = self.getTokenAuthorization()

    # Prepare params
    params = {
      "token": ta["token"],
      "sign": ta["sign"],
      "cuitRepresentada": self.afip.CUIT,
      "idPersona": identifiers
    }

    return self.executeRequest("getPersonaList_v2", params)["persona"]

  # Asks to web service for servers status
  def getServerStatus(self):
    return self.executeRequest("dummy")

  # Send request to AFIP servers
  def executeRequest(self, operation, params = {}):
    results = super(RegisterInscriptionProof, self).executeRequest(operation, params)

    if operation == "getPersona_v2":
      return results["personaReturn"]
    elif operation == "getPersonaList_v2":
      return results["personaListReturn"]
    else:
      return results["return"]
