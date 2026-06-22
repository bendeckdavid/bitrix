from __future__ import annotations

import re
from datetime import date

from selectolax.parser import HTMLParser

from integration.travel import compositor, travelc

CompositorError = travelc.CompositorError


def _form(origen: dict, destino: dict, ida: str, retorno: str | None):
    def build(html: str) -> dict:
        f = travelc.field
        form = {
            **travelc.base_form(html),
            f(html, "sb-transport-trip-types"): "ROUND_TRIP" if retorno else "ONE_WAY",
            f(html, "ClassOption"): "false",
            f(html, "startlocationOnlyFlight_input"): origen["name"] or origen["code"],
            f(html, "startlocationOnlyFlight_hinput"): f"Destination::{origen['code']}",
            f(html, "endlocationOnlyFlight_input"): destino["name"] or destino["code"],
            f(html, "endlocationOnlyFlight_hinput"): f"Destination::{destino['code']}",
            f(html, "onlyFlightDeparture:input"): ida,
            f(html, "directSubmit"): "true",
        }
        if retorno:
            form[f(html, "onlyFlightArrival:input")] = retorno
        return form
    return build


def _parse(html: str, n: int) -> list[dict]:
    vuelos: list[dict] = []
    for card in HTMLParser(html).css("[data-avail-position]")[:n]:
        ptxt = travelc.t(card.css_first(".c-price__primary"))
        tramos = []
        for j in card.css(".c-transport-journey"):
            comp = travelc.t(j.css_first(".c-transport-journey__name-company"))
            if not comp:
                continue
            horas = [travelc.t(h) for h in j.css(".c-transport-journey__point-head")]
            aerop = [travelc.t(i) for i in j.css(".c-transport-journey__point-info")]
            hdr = travelc.t(j.css_first(".c-transport-journey__header"))
            esc = re.search(r"\d+\s*escala\w*", hdr)
            tramos.append({
                "compania": comp,
                "salida": horas[0] if horas else "",
                "origen": aerop[0] if aerop else "",
                "llegada": horas[1] if len(horas) > 1 else "",
                "destino": aerop[1] if len(aerop) > 1 else "",
                "duracion": travelc.t(j.css_first(".c-transport-journey__path-info")),
                "escalas": "Directo" if "Directo" in hdr else (esc.group(0) if esc else ""),
            })
        vuelos.append({
            "precio": int(re.sub(r"\D", "", ptxt)) if re.search(r"\d", ptxt) else None,
            "precio_texto": ptxt,
            "tramos": tramos,
        })
    return vuelos


async def buscar(
    origen: dict,
    destino: dict,
    fecha_ida: date,
    fecha_retorno: date | None = None,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
    n: int = 5,
) -> list[dict]:
    """Busca vuelos en Travel Compositor (httpx, sin navegador) y devuelve los primeros `n` con precio COP."""
    qs = dict(compositor.params(origen["code"], destino["code"], fecha_ida, fecha_retorno, adultos, ninos_edades))
    ida = fecha_ida.strftime("%d/%m/%Y")
    ret = fecha_retorno.strftime("%d/%m/%Y") if fecha_retorno else None
    html = await travelc.resultados(qs, _form(origen, destino, ida, ret),
                                    "/transport/onlyTransportAvail.xhtml", {"flightPosition": "0"})
    return _parse(html, n)
