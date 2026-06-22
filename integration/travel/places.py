from __future__ import annotations

import json
import unicodedata
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

CITIES_FILE = Path("cities.json")


def _norm(s: str) -> str:
    """Minúsculas, sin tildes y sin espacios sobrantes, para comparar."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split()).lower()


@lru_cache
def _index() -> tuple[dict, dict]:
    ciudades = json.loads(CITIES_FILE.read_text())
    por_codigo = {c["code"]: c for c in ciudades}
    por_nombre: dict[str, dict] = {}
    for c in ciudades:
        if c.get("name"):
            por_nombre.setdefault(_norm(c["name"]), c)
    return por_codigo, por_nombre


def buscar(texto: str) -> dict | None:
    """Busca una ciudad por nombre o código IATA y devuelve {code, name, country_code}.

    Tolera tildes, mayúsculas y errores leves de escritura (aproxima al nombre más
    parecido). Si el texto no se parece a ninguna ciudad, devuelve None.
    """
    if not texto or not texto.strip():
        return None
    por_codigo, por_nombre = _index()
    if texto.strip().upper() in por_codigo:        # código IATA exacto ("BOG", "bog")
        return por_codigo[texto.strip().upper()]
    q = _norm(texto)
    if q in por_nombre:                            # nombre exacto ("Bogotá", "bogota")
        return por_nombre[q]
    cerca = get_close_matches(q, por_nombre, n=1, cutoff=0.6)  # typo → más cercano
    return por_nombre[cerca[0]] if cerca else None
