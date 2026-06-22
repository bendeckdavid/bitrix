from __future__ import annotations

import re
from datetime import date

from selectolax.parser import HTMLParser

from integration.travel import compositor, travelc


def _form(ciudad: dict, entrada: str, salida: str):
    def build(html: str) -> dict:
        f = travelc.field
        return {
            **travelc.base_form(html),
            f(html, "destinationOnlyAccommodation_input"): ciudad["name"] or ciudad["code"],
            f(html, "destinationOnlyAccommodation_hinput"): f"Destination::{ciudad['code']}",
            f(html, "departureOnlyAccommodation:input"): entrada,
            f(html, "arrivalOnlyAccommodation:input"): salida,
            f(html, "directSubmit"): "true",
        }
    return build


def _parse(html: str, n: int) -> list[dict]:
    hoteles: list[dict] = []
    for card in HTMLParser(html).css(".c-card"):
        nombre = travelc.t(card.css_first(".c-card__title"))
        ptxt = travelc.t(card.css_first(".c-price__primary"))
        if not nombre or not re.search(r"\d", ptxt):
            continue
        hoteles.append({
            "nombre": nombre,
            "precio": int(re.sub(r"\D", "", ptxt)),
            "precio_texto": ptxt,
            "rating": travelc.t(card.css_first(".c-rating__score")),
            "grado": travelc.t(card.css_first(".c-rating__grade")),
            "regimen": next((travelc.t(d) for d in card.css(".c-card__detail") if travelc.t(d)), ""),
        })
        if len(hoteles) >= n:
            break
    return hoteles


async def buscar(
    ciudad: dict,
    fecha_entrada: date,
    fecha_salida: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
    n: int = 5,
) -> list[dict]:
    """Busca hoteles en Travel Compositor (httpx, sin navegador) y devuelve los primeros `n` con precio COP.

    `ciudad`: dict de `places.buscar` ({code, name, ...}). El precio (total de la estancia) lo
    renderiza el servidor en COP. Flujo: GET /home → POST JSF → GET accommodationAvailability.xhtml.
    """
    qs = dict(compositor.params_hotel(ciudad["code"], fecha_entrada, fecha_salida, adultos, ninos_edades))
    entrada = fecha_entrada.strftime("%d/%m/%Y")
    salida = fecha_salida.strftime("%d/%m/%Y")
    html = await travelc.resultados(qs, _form(ciudad, entrada, salida),
                                    "/accommodation/accommodationAvailability.xhtml")
    return _parse(html, n)
