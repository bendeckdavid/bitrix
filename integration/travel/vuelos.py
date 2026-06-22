from __future__ import annotations

import re
from datetime import date

import httpx
from selectolax.parser import HTMLParser

from integration.travel import compositor

BASE = "https://ofertas.avioa.co"
_HDRS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}


class VuelosError(Exception):
    pass


def _field(html: str, suffix: str) -> str:
    m = re.search(r'name="([^"]*' + re.escape(suffix) + r'[^"]*)"', html)
    if not m:
        raise VuelosError(f"Campo del formulario no encontrado: {suffix}")
    return m.group(1)


def _form(html: str, origen: dict, destino: dict, ida: str, retorno: str | None) -> dict:
    st = re.search(r'id="([^"]*startTrip[^"]*)"', html)
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
    if not st or not vs:
        raise VuelosError("No se pudo leer el formulario de búsqueda (startTrip/ViewState).")
    st = st.group(1)
    form = {
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": st,
        "javax.faces.partial.execute": "@all",
        st: st,
        _field(html, "sb-transport-trip-types"): "ROUND_TRIP" if retorno else "ONE_WAY",
        _field(html, "ClassOption"): "false",
        _field(html, "startlocationOnlyFlight_input"): origen["name"] or origen["code"],
        _field(html, "startlocationOnlyFlight_hinput"): f"Destination::{origen['code']}",
        _field(html, "endlocationOnlyFlight_input"): destino["name"] or destino["code"],
        _field(html, "endlocationOnlyFlight_hinput"): f"Destination::{destino['code']}",
        _field(html, "onlyFlightDeparture:input"): ida,
        _field(html, "directSubmit"): "true",
        "form_SUBMIT": "1",
        "javax.faces.ViewState": vs.group(1),
    }
    if retorno:
        form[_field(html, "onlyFlightArrival:input")] = retorno
    return form


def _t(node) -> str:
    return " ".join(node.text().split()) if node else ""


def _parse(html: str, n: int) -> list[dict]:
    vuelos: list[dict] = []
    for card in HTMLParser(html).css("[data-avail-position]")[:n]:
        ptxt = _t(card.css_first(".c-price__primary"))
        tramos = []
        for j in card.css(".c-transport-journey"):
            comp = _t(j.css_first(".c-transport-journey__name-company"))
            if not comp:
                continue
            horas = [_t(h) for h in j.css(".c-transport-journey__point-head")]
            aerop = [_t(i) for i in j.css(".c-transport-journey__point-info")]
            hdr = _t(j.css_first(".c-transport-journey__header"))
            esc = re.search(r"\d+\s*escala\w*", hdr)
            tramos.append({
                "compania": comp,
                "salida": horas[0] if horas else "",
                "origen": aerop[0] if aerop else "",
                "llegada": horas[1] if len(horas) > 1 else "",
                "destino": aerop[1] if len(aerop) > 1 else "",
                "duracion": _t(j.css_first(".c-transport-journey__path-info")),
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
    """Busca vuelos en Travel Compositor y devuelve los primeros `n` con precio (COP).

    `origen`/`destino`: dicts de `places.buscar` ({code, name, ...}). El precio lo renderiza
    el servidor (displayCurrency=COP), así que basta httpx: GET /home (ViewState) → POST JSF
    (crea el viaje) → GET onlyTransportAvail.xhtml (HTML con las tarjetas).
    """
    qs = dict(compositor.params(origen["code"], destino["code"], fecha_ida, fecha_retorno, adultos, ninos_edades))
    ida = fecha_ida.strftime("%d/%m/%Y")
    ret = fecha_retorno.strftime("%d/%m/%Y") if fecha_retorno else None
    ajax = {
        **_HDRS,
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE}/home",
    }
    async with httpx.AsyncClient(headers=_HDRS, timeout=90, follow_redirects=True) as c:
        html = (await c.get(f"{BASE}/home", params=qs)).text
        p = await c.post(f"{BASE}/home", params=qs, data=_form(html, origen, destino, ida, ret), headers=ajax)
        m = re.search(r"tripId=(\d+)", p.text)
        if not m:
            raise VuelosError("La búsqueda no devolvió resultados para esa ruta/fecha.")
        r = await c.get(f"{BASE}/transport/onlyTransportAvail.xhtml", params={"tripId": m.group(1), "flightPosition": "0"})
        return _parse(r.text, n)
