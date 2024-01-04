import http.client
import json
import re

from .web_service import WebService

class ElectronicBilling(WebService):
  soapv12 = True
  WSDL = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
  URL = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
  WSDL_TEST = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
  URL_TEST = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx"

  def __init__(self, afip):
    super(ElectronicBilling, self).__init__(afip, { "service": "wsfe" })

  # Create PDF
  def createPDF(self, data: dict):
    conn = http.client.HTTPSConnection("app.afipsdk.com")

    headers = {
        "Content-Type": "application/json",
        "sdk-version-number": self.afip.sdk_version_number,
        "sdk-library": "python",
        "sdk-environment": self.afip.environment
    }

    if self.afip.access_token: headers["Authorization"] = "Bearer %s" % self.afip.access_token

    conn.request("POST", "/api/v1/pdfs", json.dumps(data), headers)

    res = conn.getresponse()
    
    data = res.read()

    if res.getcode() >= 400:
        raise Exception(data.decode("utf-8"))

    response_data = json.loads(data.decode("utf-8"))

    return { 
      "file": response_data["file"], 
      "file_name": response_data["file_name"]
    }

  # Gets last voucher number
  def getLastVoucher(self, sales_point: int, type: int):
    req = {
      "PtoVta": sales_point,
      "CbteTipo": type
    }

    return self.executeRequest("FECompUltimoAutorizado", req)["CbteNro"]

  # Create a voucher from AFIP
  def createVoucher(self, data: dict, return_response: bool = False):
    # Reassign data to avoid modify te original object
    data = data.copy()

    req = {
      "FeCAEReq": {
        "FeCabReq": {
          "CantReg": data["CbteHasta"] - data["CbteDesde"] + 1,
          "PtoVta": data["PtoVta"],
          "CbteTipo": data["CbteTipo"]
        },
        "FeDetReq": {
          "FECAEDetRequest": data
        }
      }
    }

    data.pop("CantReg")
    data.pop("PtoVta")
    data.pop("CbteTipo")

    if data.get("Tributos"): data["Tributos"] = { "Tributo": data["Tributos"] }
    if data.get("Iva"): data["Iva"] = { "AlicIva": data["Iva"] }
    if data.get("CbtesAsoc"): data["CbtesAsoc"] = { "CbteAsoc": data["CbtesAsoc"] }
    if data.get("Compradores"): data["Compradores"] = { "Comprador": data["Compradores"] }
    if data.get("Opcionales"): data["Opcionales"] = { "Opcional": data["Opcionales"] }

    results = self.executeRequest("FECAESolicitar", req)

    if return_response == True:
      return results
    
    if type(results["FeDetResp"]["FECAEDetResponse"]) in (tuple, list):
      results["FeDetResp"]["FECAEDetResponse"] = results["FeDetResp"]["FECAEDetResponse"][0]

    return {
      "CAE": results["FeDetResp"]["FECAEDetResponse"]["CAE"],
      "CAEFchVto": self.formatDate(results["FeDetResp"]["FECAEDetResponse"]["CAEFchVto"])
    }

  # Create next voucher from AFIP
  def createNextVoucher(self, data: dict):
    # Reassign data to avoid modify te original object
    data = data.copy()

    lastVoucher = self.getLastVoucher(data["PtoVta"], data["CbteTipo"])

    voucherNumber = lastVoucher + 1

    data["CbteDesde"] = voucherNumber
    data["CbteHasta"] = voucherNumber

    res = self.createVoucher(data)

    res["voucherNumber"] = voucherNumber

    return res

  # Get complete voucher information
  def getVoucherInfo(self, number: int, sales_point: int, type: int):
    req = {
      "FeCompConsReq": {
        "CbteNro": number,
        "PtoVta": sales_point,
        "CbteTipo": type
      }
    }

    return self.executeRequest("FECompConsultar", req)

  # Create CAEA
  def createCAEA(self, period: int, fortnight: int):
    req = {
      "Periodo": period,
      "Orden": fortnight
    }

    return self.executeRequest("FECAEASolicitar", req)["ResultGet"]

  # Get CAEA
  def getCAEA(self, period: int, fortnight: int):
    req = {
      "Periodo": period,
      "Orden": fortnight
    }

    return self.executeRequest("FECAEAConsultar", req)["ResultGet"]

  # Asks to AFIP Servers for available sales points
  def getSalesPoints(self):
    return self.executeRequest("FEParamGetPtosVenta")["ResultGet"]["PtoVenta"]

  # Asks to AFIP Servers for available voucher types
  def getVoucherTypes(self):
    return self.executeRequest("FEParamGetTiposCbte")["ResultGet"]["CbteTipo"]

  # Asks to AFIP Servers for voucher concepts availables
  def getConceptTypes(self):
    return self.executeRequest("FEParamGetTiposConcepto")["ResultGet"]["ConceptoTipo"]

  # Asks to AFIP Servers for document types availables
  def getDocumentTypes(self):
    return self.executeRequest("FEParamGetTiposDoc")["ResultGet"]["DocTipo"]

  # Asks to AFIP Servers for available aliquotes
  def getAliquotTypes(self):
    return self.executeRequest("FEParamGetTiposIva")["ResultGet"]["IvaTipo"]

  # Asks to AFIP Servers for available currencies
  def getCurrenciesTypes(self):
    return self.executeRequest("FEParamGetTiposMonedas")["ResultGet"]["Moneda"]

  # Asks to AFIP Servers for available voucher optional data
  def getOptionsTypes(self):
    return self.executeRequest("FEParamGetTiposOpcional")["ResultGet"]["OpcionalTipo"]

  # Asks to AFIP Servers for available tax types
  def getTaxTypes(self):
    return self.executeRequest("FEParamGetTiposTributos")["ResultGet"]["TributoTipo"]

  # Asks to web service for servers status
  def getServerStatus(self):
    return self.executeRequest("FEDummy")

  # Change date from AFIP used format (yyyymmdd) to yyyy-mm-dd
  def formatDate(self, date: int) -> str:
    m = re.search(r"(\d{4})(\d{2})(\d{2})", str(date))

    return "%s-%s-%s" %(m.group(1), m.group(2), m.group(3))

  # Sends request to AFIP servers
  def executeRequest(self, operation: str, params: dict = {}):
    params.update(self.getWSInitialRequest(operation))

    results = super(ElectronicBilling, self).executeRequest(operation, params)

    self.__checkErrors(operation, results)

    return results["%sResult" % operation]

  # Prepare default request parameters for most operations
  def getWSInitialRequest(self, operation: str):
    if operation == "FEDummy":
      return {}
    
    ta = self.getTokenAuthorization()

    return {
      "Auth": {
        "Token": ta["token"],
        "Sign": ta["sign"],
        "Cuit": self.afip.CUIT
      }
    }

  # Check if occurs an error on Web Service request
  def __checkErrors(self, operation: str, results: dict):
    res = results["%sResult" %operation]

    if operation == "FECAESolicitar" and res["FeDetResp"]:
      if type(res["FeDetResp"]["FECAEDetResponse"]) in (tuple, list):
        res["FeDetResp"]["FECAEDetResponse"] = res["FeDetResp"]["FECAEDetResponse"][0]

      if res["FeDetResp"]["FECAEDetResponse"].get("Observaciones") and res["FeDetResp"]["FECAEDetResponse"]["Resultado"] != "A":
        res["Errors"] = { "Err": res["FeDetResp"]["FECAEDetResponse"]["Observaciones"]["Obs"] }

    if res.get("Errors"):
      err = res["Errors"]["Err"][0] if type(res["Errors"]["Err"]) in (tuple, list) else res["Errors"]["Err"]

      raise Exception("(%s) %s" % (err["Code"], err["Msg"])) 
