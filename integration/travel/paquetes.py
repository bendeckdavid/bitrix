from __future__ import annotations

import re
from datetime import date

from selectolax.parser import HTMLParser

from integration.travel import compositor, travelc


def _form(origen: dict, destino: dict, ida: str, vuelta: str, edades: list[int]):
    def build(html: str) -> dict:
        f = travelc.field
        form = {
            **travelc.base_form(html),
            f(html, "startlocation_input"): origen["name"] or origen["code"],
            f(html, "startlocation_hinput"): f"Destination::{origen['code']}",
            f(html, "endlocation_input"): destino["name"] or destino["code"],
            f(html, "endlocation_hinput"): f"Destination::{destino['code']}",
            f(html, "flightPlusHotelDeparture:input"): ida,
            f(html, "flightPlusHotelArrival:input"): vuelta,
            f(html, "ClassOption"): "false",
            f(html, "directSubmit"): "true",
        }
        # edades de niños: campos dinámicos roomVH:distri:0:childAges:N:age (uno por niño)
        for campo, edad in zip(sorted(set(re.findall(r'name="([^"]*childAges:\d+:age)"', html))), edades):
            form[campo] = str(edad)
        return form
    return build


def _parse(html: str, n: int) -> dict:
    tree = HTMLParser(html)

    # precio del paquete por persona (el "desde": vuelo + hotel más económico)
    desde = ""
    for bottom in tree.css(".c-price__bottom"):
        if "paquete" in travelc.t(bottom).lower():
            parent = bottom.parent
            desde = travelc.t(parent.css_first(".c-price__primary")) if parent else ""
            break

    # vuelo incluido (primera tarjeta de vuelo del constructor)
    vuelo = {}
    fc = tree.css_first("[data-avail-position]")
    if fc:
        horas = [travelc.t(h) for h in fc.css(".c-transport-journey__point-head")]
        aerop = [travelc.t(i) for i in fc.css(".c-transport-journey__point-info")]
        hdr = travelc.t(fc.css_first(".c-transport-journey__header"))
        vuelo = {
            "compania": travelc.t(fc.css_first(".c-transport-journey__name-company")),
            "salida": horas[0] if horas else "",
            "origen": aerop[0] if aerop else "",
            "llegada": horas[1] if len(horas) > 1 else "",
            "destino": aerop[1] if len(aerop) > 1 else "",
            "escalas": "Directo" if "Directo" in hdr else "",
        }

    # opciones de hotel (base = incluido; resto = "+COP X" sobre el desde)
    hoteles = []
    for card in tree.css(".c-card"):
        nombre = travelc.t(card.css_first(".c-card__title"))
        if not nombre:
            continue
        extra = travelc.t(card.css_first(".c-price__primary"))
        hoteles.append({"nombre": nombre, "extra": extra or "incluido"})
        if len(hoteles) >= n:
            break

    return {"precio_desde": desde, "vuelo": vuelo, "hoteles": hoteles}


async def buscar(
    origen: dict,
    destino: dict,
    fecha_ida: date,
    fecha_vuelta: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
    n: int = 5,
) -> dict:
    """Busca paquetes vuelo+hotel en Travel Compositor (httpx, sin navegador).

    Devuelve {precio_desde, vuelo, hoteles}: el precio del paquete por persona (combinación más
    barata), el vuelo incluido y las opciones de hotel. Flujo: GET /home → POST JSF → GET
    /vmash/vmashAvailability.xhtml (el constructor del paquete, con precios en COP).
    """
    qs = dict(compositor.params_paquete(origen["code"], destino["code"], fecha_ida, fecha_vuelta, adultos, ninos_edades))
    ida = fecha_ida.strftime("%d/%m/%Y")
    vuelta = fecha_vuelta.strftime("%d/%m/%Y")
    html = await travelc.resultados(qs, _form(origen, destino, ida, vuelta, ninos_edades or []),
                                    "/vmash/vmashAvailability.xhtml")
    return _parse(html, n)
