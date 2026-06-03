import json
from pathlib import Path

DB_FILE = Path("destinos.json")


def save(codigo: str, nombre: str, url: str, data: dict) -> None:
    db = json.loads(DB_FILE.read_text()) if DB_FILE.exists() else {}
    db[codigo] = {"nombre": nombre, "url": url, "data": data}
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2))
