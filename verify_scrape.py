"""Verificador del scraper sobre las páginas oficiales de avioa.

- SIEMPRE valida la limpieza (descargar + contenido_a_texto), sin coste.
- Si hay OPENAI_API_KEY, además corre la extracción end-to-end.

Vuelca el texto limpio (y el JSON si hay key) en VAL_DIR para inspección, e
imprime un resumen con señales de fallo (vacío, boilerplate colado, sin tabla).

Uso:
    uv run python verify_scrape.py            # todas las URLs oficiales
    uv run python verify_scrape.py <url> ...  # subconjunto
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from core.settings import get_settings
from integration.scrape.clean import contenido_a_texto, descargar

BASE = "https://avioa.co/destinos/"
SLUGS = [
    # Medellín
    "cartagena-med", "san-andres-med", "punta-cana-med", "eje-cafetero-med",
    "cancun-med", "santa-marta-med", "panama-med", "la-guajira-med", "europa-med",
    "ciudad-de-mexico-y-cancun-med", "amazonas-med", "cuba-med", "orlando-disney-med",
    "curazao-med", "peru-med", "rio-de-janeiro-med", "turquia-med", "boyaca-med",
    "europa-17-dias", "crucero-por-el-caribe", "aruba-med",
    # Bogotá
    "cartagena-bog", "san-andres-bog", "santa-marta-bog", "cancun-bog",
    "punta-cana-bog", "panama-bog", "curazao-desde-bog",
]
DEFAULT = [BASE + s + "/" for s in SLUGS]

VAL_DIR = Path("/tmp/avioa_val")
VAL_DIR.mkdir(parents=True, exist_ok=True)

# Si aparece en el texto limpio, el corte de boilerplate falló (o no hubo marcador).
_BOILERPLATE = ("medios de pago", "preguntas frecuentes", "por qué confiar",
                "síguenos", "política de", "todos los derechos", "qué opinan nuestros")

_HAS_KEY = bool(get_settings().openai_api_key)
if _HAS_KEY:
    from integration.scrape.extract import extraer
    from integration.scrape.render import to_markdown


async def run(url: str) -> dict:
    slug = url.rstrip("/").split("/")[-1]
    try:
        html = await descargar(url)
    except Exception as e:  # noqa: BLE001
        return {"slug": slug, "error": f"{type(e).__name__}: {e}"}
    texto = contenido_a_texto(html)
    (VAL_DIR / f"{slug}.txt").write_text(texto)

    low = texto.lower()
    info = {
        "slug": slug,
        "html_kb": round(len(html) / 1024),
        "chars": len(texto),
        "tablas": texto.count("TABLA:"),
        "filas_tabla": sum(1 for ln in texto.splitlines() if " | " in ln),
        "boilerplate": [b for b in _BOILERPLATE if b in low],
    }
    if _HAS_KEY and texto:
        try:
            data = await extraer(texto, url)
            (VAL_DIR / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
            (VAL_DIR / f"{slug}.md").write_text(to_markdown(data))  # salida real (la que recibe el LLM)
            info["hoteles"] = [h["nombre"] for h in data["hoteles"]]
            info["n_tarifas"] = len(data["tarifas"])
            info["cols"] = [p["columna"] for p in data["tarifas"][0]["precios"]] if data["tarifas"] else []
        except Exception as e:  # noqa: BLE001
            info["extract_error"] = f"{type(e).__name__}: {e}"
    return info


async def main(urls: list[str]) -> None:
    sem = asyncio.Semaphore(6)

    async def guarded(u: str) -> dict:
        async with sem:
            return await run(u)

    results = await asyncio.gather(*(guarded(u) for u in urls))
    print(f"\n{'slug':<26} {'kb':>4} {'chars':>6} {'tab':>3} {'filas':>5}  flags")
    print("-" * 78)
    for r in sorted(results, key=lambda x: x["slug"]):
        if "error" in r:
            print(f"{r['slug']:<26}  DESCARGA ERROR: {r['error']}")
            continue
        flags = []
        if r["chars"] < 200:
            flags.append("VACÍO/CORTO")
        if r["tablas"] == 0:
            flags.append("SIN-TABLA")
        if r["boilerplate"]:
            flags.append("BOILERPLATE:" + ",".join(r["boilerplate"]))
        if r.get("extract_error"):
            flags.append("EXTRACT:" + r["extract_error"])
        print(f"{r['slug']:<26} {r['html_kb']:>4} {r['chars']:>6} {r['tablas']:>3} {r['filas_tabla']:>5}  {' '.join(flags) or 'ok'}")
        if "n_tarifas" in r:
            print(f"{'':<26} → hoteles={r['hoteles']} tarifas={r['n_tarifas']} cols={r['cols']}")
    print(f"\nArtefactos en {VAL_DIR}  (key OpenAI: {'sí' if _HAS_KEY else 'NO → solo limpieza'})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEFAULT))
