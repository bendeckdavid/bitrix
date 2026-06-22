from __future__ import annotations

import re

import httpx
from selectolax.parser import HTMLParser, Node

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bitrix-scraper/1.0)"}
TIMEOUT = httpx.Timeout(15.0)

_CORTES = (
    "la oferta aplica únicamente",
    "miles de personas han vivido",
    "por qué confiar en nosotros",
    "preguntas frecuentes",
    "reserva tus vacaciones en oferta",
    "buscas más promociones",
    "descubre nuestras actividades opcionales",
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("\xa0", " ")).strip()


def _dentro_de_tabla(node: Node) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.tag == "table":
            return True
        parent = parent.parent
    return False


def _tabla_markdown(table: Node) -> str:
    filas = []
    for tr in table.css("tr"):
        celdas = [_clean(c.text(separator=" ")) for c in tr.css("td, th")]
        if any(celdas):
            filas.append(" | ".join(celdas))
    return "\n".join(filas)


def contenido_a_texto(html: str) -> str:
    tree = HTMLParser(html)
    post = tree.css_first('div[data-elementor-type="wp-post"]') or tree.body
    if post is None:
        return ""

    prosa: list[str] = []
    for node in post.traverse(include_text=False):
        if node.tag not in ("h1", "h2", "h3", "h4", "h5", "p") or _dentro_de_tabla(node):
            continue
        texto = _clean(node.text(separator=" "))
        if not texto:
            continue
        if any(c in texto.lower() for c in _CORTES):
            break  # a partir de aquí es boilerplate repetido
        prefijo = "## " if node.tag in ("h1", "h2", "h3", "h4", "h5") else ""
        prosa.append(prefijo + texto)

    partes = ["\n".join(prosa)]
    for table in post.css("table"):
        md = _tabla_markdown(table)
        if md:
            partes.append("TABLA:\n" + md)

    return "\n\n".join(partes).strip()


async def descargar(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return resp.text
