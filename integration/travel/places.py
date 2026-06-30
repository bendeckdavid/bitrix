from __future__ import annotations

import unicodedata

from integration.travel import travelc


def _norm(s: str) -> str:
    """Minúsculas, sin tildes y sin espacios sobrantes, para comparar."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split()).lower()


# Casos ambiguos: TC ordena primero un homónimo extranjero, así que fijamos el correcto.
_OVERRIDES = {
    "san andres": ("SAI-123", "San Andrés"),
    "san andres isla": ("SAI-123", "San Andrés"),
    "isla de san andres": ("SAI-123", "San Andrés"),
    "cuba": ("VRA", "Varadero"),
}

_cache: dict[str, dict | None] = {}


async def buscar(texto: str) -> dict | None:
    """Resuelve una ciudad/destino al código que usa Travel Compositor (`Destination::<code>`).

    Usa el autocompletado propio de TC (fuente de verdad de sus códigos) y devuelve
    `{code, name}` de la mejor sugerencia, o `None` si no hay ninguna. Los códigos de TC no
    siempre son el IATA (Santa Marta=SMC, San Andrés=SAI-123, etc.).
    """
    if not texto or not texto.strip():
        return None
    q = _norm(texto)
    if q in _OVERRIDES:
        code, name = _OVERRIDES[q]
        return {"code": code, "name": name}
    if q in _cache:
        return _cache[q]
    sugerencias = await travelc.autocompletar(texto)
    res = None
    if sugerencias:
        code, label = sugerencias[0]
        res = {"code": code, "name": label.split(",")[0].strip()}
    _cache[q] = res
    return res
