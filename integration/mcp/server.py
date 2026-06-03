import httpx
from fastmcp import FastMCP

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
