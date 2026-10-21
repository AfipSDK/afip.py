<!-- PROJECT SHIELDS -->
[![PyPI][pip-shield]](https://pypi.org/project/afip.py/)
[![Contributors][contributors-shield]](https://github.com/afipsdk/afip.py/graphs/contributors)
[![Closed issues][issues-shield]](https://github.com/afipsdk/afip.py/issues)
[![License][license-shield]](https://github.com/afipsdk/afip.py/blob/master/LICENSE.txt)


<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/afipsdk/afip.py">
    <img src="https://github.com/afipsdk/afipsdk.github.io/blob/master/images/logo-colored.png" alt="Logo" width="130" height="130">
  </a>

  <h3 align="center">Afip.py</h3>

  <p align="center">
    Librería para conectarse a los Web Services de AFIP en Python
    <br />
    <a href="https://docs.afipsdk.com"><strong>Explorar documentación »</strong></a>
    <br />
    <br />
    <a href="https://discord.gg/A6TuHEyAZm"><strong>Comunidad Afip SDK</strong></a>
    <br />
    <br />
    <a href="https://github.com/afipsdk/afip.py/issues">Reportar un bug</a>
  </p>
</p>


<!-- DOCS -->
## Documentación
[Explorar documentación](https://docs.afipsdk.com)

<!-- FACTURA SDK -->
## Factura SDK
La librería también incluye [Factura SDK](https://afipsdk.com/docs/facturasdk/), para emitir comprobantes de punta a punta (certificado, punto de venta, autorización en ARCA, PDF y webhooks) con el access token de un proyecto Factura SDK:

```python
from afip import Afip

afip = Afip({ "access_token": "fsk_dev_…" })

# Responde enseguida con el comprobante en cola; el resultado llega a tu webhook
invoice = afip.FacturaSDK.createInvoice(data, idempotency_key="venta-0001")

# En tu endpoint de webhook: verifica la firma y devuelve el evento
event = afip.FacturaSDK.constructWebhookEvent(raw_body, signature_header, secret)
```

Emisores, certificados, comprobantes, webhooks y automatizaciones están en `afip.FacturaSDK`. Los errores de la API llegan como `FacturaSDKError`, con `status`, `data_errors` y `errors`. Si además usás los web services de Afip SDK, pasá el token de Factura SDK en `facturasdk_access_token`.

<!-- COMUNITY -->
## Comunidad
[Comunidad Afip SDK](https://discord.gg/A6TuHEyAZm)


<!-- ABOUT THE PROJECT -->
## Acerca del proyecto
Con más de 100k descargas, desde el 2017, Afip SDK es la plataforma preferida entre los desarrolladores para conectarse a los web services de ARCA.

<!-- CONTACT -->
### Contacto
Soporte de Afip SDK - ayuda@afipsdk.com

Link del proyecto: [https://github.com/afipsdk/afip.py](https://github.com/afipsdk/afip.py)


_Este software y sus desarrolladores no tienen ninguna relación con la AFIP._

<!-- MARKDOWN LINKS & IMAGES -->
[pip-shield]: https://static.pepy.tech/badge/afip.py
[contributors-shield]: https://img.shields.io/github/contributors/afipsdk/afip.py.svg?color=orange
[issues-shield]: https://img.shields.io/github/issues-closed-raw/afipsdk/afip.py.svg?color=blueviolet
[license-shield]: https://img.shields.io/github/license/afipsdk/afip.py.svg?color=blue
