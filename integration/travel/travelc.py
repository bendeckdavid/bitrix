from __future__ import annotations

import re

import httpx

from integration.travel import compositor

BASE = compositor.BASE.removesuffix("/home")  # raíz del sitio (sin /home)
_HDRS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}


class CompositorError(Exception):
    pass


def field(html: str, suffix: str) -> str:
    """Nombre completo de un campo del formulario JSF por su sufijo estable."""
    m = re.search(r'name="([^"]*' + re.escape(suffix) + r'[^"]*)"', html)
    if not m:
        raise CompositorError(f"Campo del formulario no encontrado: {suffix}")
    return m.group(1)


def base_form(html: str) -> dict:
    """Campos comunes del POST JSF (botón startTrip + ViewState + cabeceras de ajax)."""
    st = re.search(r'id="([^"]*startTrip[^"]*)"', html)
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
    if not st or not vs:
        raise CompositorError("No se pudo leer el formulario de búsqueda (startTrip/ViewState).")
    sid = st.group(1)
    return {
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": sid,
        "javax.faces.partial.execute": "@all",
        sid: sid,
        "form_SUBMIT": "1",
        "javax.faces.ViewState": vs.group(1),
    }


def t(node) -> str:
    """Texto normalizado de un nodo selectolax (espacios colapsados)."""
    return " ".join(node.text().split()) if node else ""


async def resultados(qs: dict, build_form, results_path: str, extra: dict | None = None) -> str:
    """GET /home (ViewState) → POST JSF startTrip (crea el viaje) → GET <results_path>?tripId=N.

    `build_form(html)` arma el cuerpo del POST con los campos específicos (vuelo/hotel).
    Devuelve el HTML de la página de resultados (con los precios renderizados en COP).
    """
    ajax = {
        **_HDRS,
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE}/home",
    }
    async with httpx.AsyncClient(headers=_HDRS, timeout=120, follow_redirects=True) as c:
        html = (await c.get(f"{BASE}/home", params=qs)).text
        p = await c.post(f"{BASE}/home", params=qs, data=build_form(html), headers=ajax)
        m = re.search(r"tripId=(\d+)", p.text)
        if not m:
            raise CompositorError("La búsqueda no devolvió resultados para esos datos.")
        r = await c.get(f"{BASE}{results_path}", params={"tripId": m.group(1), **(extra or {})})
        return r.text


async def autocompletar(texto: str) -> list[tuple[str, str]]:
    """Sugerencias de destino del propio Travel Compositor: lista de (código, etiqueta).

    El `código` es el que TC acepta en `Destination::<código>` (no siempre es el IATA).
    """
    ajax = {
        **_HDRS,
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE}/home",
    }
    async with httpx.AsyncClient(headers=_HDRS, timeout=30, follow_redirects=True) as c:
        html = (await c.get(f"{BASE}/home", params={"tripType": "ONLY_FLIGHT", "lang": "ES"})).text
        cid = re.search(r'id="([^"]*endlocationOnlyFlight)"', html)
        vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
        if not cid or not vs:
            return []
        cid = cid.group(1)
        form = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": cid,
            "javax.faces.partial.execute": cid,
            "javax.faces.partial.render": cid,
            cid: cid,
            f"{cid}_query": texto,
            "javax.faces.ViewState": vs.group(1),
        }
        r = await c.post(f"{BASE}/home", data=form, headers=ajax)
    codes = re.findall(r'data-item-value="Destination::([^"]+)"', r.text)
    labels = re.findall(r'data-item-label="([^"]+)"', r.text)
    return list(zip(codes, labels))
