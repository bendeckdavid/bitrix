from __future__ import annotations


def _cop(v: int) -> str:
    return "$" + f"{v:,}".replace(",", ".")


def _celda(p: dict) -> str:
    return _cop(p["valor"]) if p["valor"] is not None else (p["texto"] or "")


def to_markdown(d: dict) -> str:
    titulo = d.get("oferta") or d["resumen"].get("titular") or "Destino"
    out: list[str] = [f"# {titulo} ({d['url']})"]

    r = d["resumen"]
    if r.get("titular") and r["titular"] != titulo:
        out.append(f"**{r['titular']}**")
    if r.get("descripcion"):
        out.append(r["descripcion"])
    for etiqueta, campo in (("Incluye", "incluye"), ("No incluye", "no_incluye"), ("Nota", "nota")):
        if r.get(campo):
            out.append(f"**{etiqueta}:** {r[campo]}")
    if d.get("aclaraciones"):
        out.append(f"**Importante:** {d['aclaraciones']}")

    if d["hoteles"]:
        out.append("\n## Hoteles")
        for h in d["hoteles"]:
            precio = [f"adulto {_cop(h['precio_adulto'])}"] if h.get("precio_adulto") is not None else []
            if h.get("precio_nino") is not None:
                precio.append(f"niño {_cop(h['precio_nino'])}")
            linea = f"- **{h['nombre']}**"
            if precio:
                linea += " — " + " · ".join(precio)
            if h.get("descripcion"):
                linea += f" — {h['descripcion']}"
            out.append(linea)

    if d["tarifas"]:
        cols = [p["columna"] for p in d["tarifas"][0]["precios"]]
        out.append("\n## Tarifas (COP)")
        out.append("| Fecha | " + " | ".join(cols) + " |")
        out.append("|" + "---|" * (len(cols) + 1))
        for t in d["tarifas"]:
            fecha = t["fecha"] + (" 🔥" if t["es_oferta"] else "")
            out.append(f"| {fecha} | " + " | ".join(_celda(p) for p in t["precios"]) + " |")

    if d.get("condiciones"):
        out.append(f"\n**Condiciones:** {d['condiciones']}")

    return "\n".join(out)
