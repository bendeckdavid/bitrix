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
        out.append("\n## Hoteles (precio 'desde' / mínimo — el precio real de cada fecha está en la tabla de tarifas)")
        for h in d["hoteles"]:
            desde = [f"adulto desde {_cop(h['precio_adulto'])}"] if h.get("precio_adulto") is not None else []
            if h.get("precio_nino") is not None:
                desde.append(f"niño desde {_cop(h['precio_nino'])}")
            linea = f"- **{h['nombre']}**"
            if desde:
                linea += " — " + " · ".join(desde)
            if h.get("descripcion"):
                linea += f" — {h['descripcion']}"
            out.append(linea)

    if d["tarifas"]:
        cols = [p["columna"] for p in d["tarifas"][0]["precios"]]
        out.append("\n## Tarifas por fecha (COP) — fuente de verdad: usa SOLO la celda de la fecha + columna exactas")
        out.append("| Fecha | " + " | ".join(cols) + " |")
        out.append("|" + "---|" * (len(cols) + 1))
        for t in d["tarifas"]:
            fecha = t["fecha"] + (" 🔥" if t["es_oferta"] else "")
            out.append(f"| {fecha} | " + " | ".join(_celda(p) for p in t["precios"]) + " |")
        out.append(
            f"_Estas {len(d['tarifas'])} fechas son las únicas salidas con precio. No hay tarifa para otras "
            f"fechas, duraciones ni acomodaciones que las de esta ficha: si piden algo que no está en la "
            f"tabla, dilo y deriva a un asesor; nunca estimes ni interpoles un precio._"
        )

    if d.get("condiciones"):
        out.append(f"\n**Condiciones:** {d['condiciones']}")

    return "\n".join(out)
