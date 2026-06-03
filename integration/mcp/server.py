import difflib
from typing import Annotated

import httpx
from pydantic import Field
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from integration.scrape import store
from integration.scrape.extract import extraer
from integration.scrape.render import to_markdown
from integration.scrape.clean import contenido_a_texto, descargar

mcp = FastMCP("Bitrix IA")


@mcp.tool
async def scrape_destino(url: str, nombre: str, codigo: str) -> str:
    try:
        html = await descargar(url)
    except httpx.HTTPStatusError as e:
        raise ValueError(f"No se pudo abrir la página (HTTP {e.response.status_code}): {url}")
    contenido = contenido_a_texto(html)
    if not contenido:
        raise ValueError("No se encontró contenido en la página")
    data = await extraer(contenido, url)
    store.save(codigo, nombre, url, data)
    return to_markdown(data)


def _catalogo() -> str:
    db = store.load()
    if not db:
        return "(Base de datos vacía: ejecuta scrape_destino para poblarla.)"
    return "\n".join(f"- {cod} → {r['nombre']}" for cod, r in sorted(db.items()))


_GET_DESTINO_DESC = (
    "Devuelve la ficha COMPLETA de un destino turístico de AVIOA ya guardado en la base de "
    "datos local, en formato markdown listo para responder a un cliente. Incluye: nombre de "
    "la oferta, resumen (titular, qué incluye / qué NO incluye, notas y avisos), lista de "
    "hoteles con su precio, una TABLA de tarifas (cada fila = fecha de viaje; cada columna = "
    "hotel/plan/acomodación; precios en pesos colombianos; '🔥' marca una fecha en oferta y "
    "'AGOTADO' una fecha sin cupo) y las condiciones de pago/abono.\n\n"
    "Úsala siempre que el cliente pregunte por precios, fechas disponibles, hoteles o "
    "detalles de un destino concreto, en lugar de responder de memoria.\n\n"
    "El parámetro `codigo` debe ser EXACTAMENTE uno de los códigos del catálogo de abajo "
    "(no distingue mayúsculas ni espacios sobrantes). No inventes códigos ni URLs.\n\n"
    "Catálogo disponible (codigo → destino):\n" + _catalogo()
)


@mcp.tool(description=_GET_DESTINO_DESC)
async def get_destino(
    codigo: Annotated[str, Field(description="Código exacto del destino del catálogo, p. ej. 'CUN-MED' (Cancún) o 'CTG-BOG' (Cartagena desde Bogotá).")],
) -> str:
    db = store.load()
    if not db:
        raise ToolError(
            "La base de datos de destinos está vacía. Antes de consultar, hay que ejecutar "
            "scrape_destino(url, nombre, codigo) para guardar al menos un destino."
        )
    cod = codigo.strip().upper()
    registro = db.get(cod)
    if registro is None:
        sugerencias = difflib.get_close_matches(cod, db, n=2)
        pista = f" ¿Quizá quisiste {' o '.join(sugerencias)}?" if sugerencias else ""
        raise ToolError(
            f"No existe ningún destino con código '{codigo}'.{pista} "
            f"Elige EXACTAMENTE uno de estos {len(db)} códigos válidos: {', '.join(sorted(db))}."
        )
    return to_markdown(registro["data"])
