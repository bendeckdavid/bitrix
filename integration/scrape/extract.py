from __future__ import annotations

from openai import AsyncOpenAI

from core.settings import get_settings

from .schemas import Destino

MODEL = "gpt-5.4-mini"

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    return _client


_SYSTEM = """Eres un extractor de datos de páginas de paquetes turísticos de la agencia AVIOA.
Recibes el contenido de texto de una página de destino y devuelves sus datos estructurados.

Reglas:
- Extrae solo lo que aparece en el texto; no inventes ni completes datos.
- Precios: conviértelos a enteros en pesos colombianos (p. ej. "$1'219.000" -> 1219000). Si una celda dice "AGOTADO" u otro texto no numérico, pon valor=null y guarda el texto en el campo 'texto'.
- En la tabla de tarifas, la primera fila suele ser la cabecera con los nombres de columna (hoteles, planes, o DOBLE/NIÑO/SENCILLA). Usa esos nombres en 'columna'. No incluyas la fila de cabecera como una tarifa.
- Algunas páginas tienen una tabla de "EL PLAN INCLUYE" que describe planes: NO es la tabla de tarifas; úsala solo como contexto. La tabla de tarifas es la que tiene fechas y precios.
- 'hoteles' es para alojamientos. Si los encabezados de la sección son tours, cabinas de crucero o itinerarios, deja 'hoteles' vacío.
- Conserva el texto tal cual (con sus emojis) en los campos de prosa como incluye/no_incluye/aclaraciones."""


async def extraer(contenido: str, url: str) -> dict:
    response = await _get_client().responses.parse(
        model=MODEL,
        max_output_tokens=8000,
        instructions=_SYSTEM,
        input=f"Contenido de la página:\n\n{contenido}",
        text_format=Destino,
    )
    data = response.output_parsed.model_dump()
    data["url"] = url
    return data
