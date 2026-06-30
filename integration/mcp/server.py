import difflib
from typing import Annotated
from datetime import date, datetime

import httpx
from pydantic import Field
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from integration.scrape import store
from integration.scrape.extract import extraer
from integration.scrape.render import to_markdown
from integration.travel import compositor, places, vuelos, hoteles, paquetes, travelc
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
    "hoteles con su precio 'desde' (mínimo, no el de cualquier fecha), una TABLA de tarifas "
    "(cada fila = fecha de viaje; cada columna = hotel/plan/acomodación; precios en pesos "
    "colombianos; '🔥' marca una fecha en oferta y 'AGOTADO' una fecha sin cupo) y las "
    "condiciones de pago/abono. La TABLA es la ÚNICA fuente válida del precio exacto: solo las "
    "fechas listadas tienen salida; para una fecha, duración o acomodación que no esté en la "
    "tabla NO hay precio (no lo estimes: dilo y deriva a un asesor).\n\n"
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


def _fecha(s: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    raise ToolError(f"Fecha inválida '{s}'. Usa el formato AAAA-MM-DD (p. ej. 2026-07-01).")


async def _ciudad(texto: str, rol: str) -> dict:
    c = await places.buscar(texto)
    if c is None:
        raise ToolError(f"No reconozco la ciudad de {rol} '{texto}'. Indica una ciudad o código IATA válido.")
    return c


_BUSCAR_VUELOS_DESC = (
    "Cotiza vuelos en Travel Compositor: devuelve los más baratos EN VIVO (precio COP ida y vuelta "
    "por persona, horarios, duración y aerolínea) y el enlace para ver todo y reservar. Resuelve "
    "nombres de ciudad a su código IATA (acepta nombre o código; tolera tildes y errores leves de "
    "escritura). Úsala siempre que el cliente pregunte por precios u opciones de vuelos. No inventes "
    "precios: salen de la búsqueda; si la ruta/fecha no da resultados, igual entrega el enlace."
)


@mcp.tool(description=_BUSCAR_VUELOS_DESC)
async def buscar_vuelos(
    origen: Annotated[str, Field(description="Ciudad o código IATA de origen, p. ej. 'Cali' o 'CLO'.")],
    destino: Annotated[str, Field(description="Ciudad o código IATA de destino, p. ej. 'Bogotá' o 'BOG'.")],
    fecha_ida: Annotated[str, Field(description="Fecha de ida en formato AAAA-MM-DD.")],
    fecha_retorno: Annotated[str, Field(description="Fecha de retorno AAAA-MM-DD. Vacío = solo ida.")] = "",
    adultos: Annotated[int, Field(description="Número de adultos.", ge=1)] = 1,
    ninos_edades: Annotated[list[int], Field(description="Edad (en años) de cada niño; p. ej. [10, 4].")] = [],
    n: Annotated[int, Field(description="Cuántos vuelos (los más baratos) mostrar.", ge=1, le=15)] = 5,
) -> str:
    o = await _ciudad(origen, "origen")
    d = await _ciudad(destino, "destino")
    ida = _fecha(fecha_ida)
    ret = _fecha(fecha_retorno) if fecha_retorno.strip() else None
    edades = ninos_edades or None
    url = compositor.url_vuelos(o["code"], d["code"], ida, ret, adultos, edades)

    tramo = f"ida {ida:%d/%m/%Y}" + (f" · vuelta {ret:%d/%m/%Y}" if ret else " (solo ida)")
    out = [f"✈️ {o['name'] or o['code']} ({o['code']}) → {d['name'] or d['code']} ({d['code']}) · {tramo}"]
    try:
        res = await vuelos.buscar(o, d, ida, ret, adultos, edades, n=20)
    except travelc.CompositorError:
        res = []
    res = sorted(res, key=lambda v: v["precio"] if v["precio"] is not None else 10**12)[:n]
    if res:
        out.append("Más baratos (precio ida y vuelta por persona):")
        for i, v in enumerate(res, 1):
            t = v["tramos"][0] if v["tramos"] else {}
            partes = [p for p in (t.get("compania"), f"{t.get('salida', '')}→{t.get('llegada', '')}".strip("→"),
                                  t.get("escalas"), t.get("duracion"), v["precio_texto"]) if p]
            out.append(f"{i}. " + " · ".join(partes))
    else:
        out.append("No pude traer las opciones ahora mismo.")
    out.append(f"Ver todas y reservar: {url}")
    return "\n".join(out)


_BUSCAR_HOTELES_DESC = (
    "Cotiza hoteles en Travel Compositor: devuelve los más baratos EN VIVO (precio COP total de la "
    "estancia, valoración y régimen) y el enlace para ver todo y reservar. Resuelve el nombre de "
    "ciudad a su código IATA (acepta nombre o código; tolera tildes y errores leves de escritura). "
    "Úsala siempre que el cliente pregunte por precios u opciones de alojamiento. No inventes "
    "precios: salen de la búsqueda; si la ciudad/fecha no da resultados, igual entrega el enlace."
)


@mcp.tool(description=_BUSCAR_HOTELES_DESC)
async def buscar_hoteles(
    ciudad: Annotated[str, Field(description="Ciudad o código IATA del hotel, p. ej. 'Bogotá' o 'BOG'.")],
    fecha_entrada: Annotated[str, Field(description="Fecha de entrada / check-in en formato AAAA-MM-DD.")],
    fecha_salida: Annotated[str, Field(description="Fecha de salida / check-out en formato AAAA-MM-DD.")],
    adultos: Annotated[int, Field(description="Número de adultos.", ge=1)] = 1,
    ninos_edades: Annotated[list[int], Field(description="Edad (en años) de cada niño; p. ej. [10, 4].")] = [],
    n: Annotated[int, Field(description="Cuántos hoteles (los más baratos) mostrar.", ge=1, le=15)] = 5,
) -> str:
    c = await _ciudad(ciudad, "destino")
    entrada = _fecha(fecha_entrada)
    salida = _fecha(fecha_salida)
    edades = ninos_edades or None
    url = compositor.url_hoteles(c["code"], entrada, salida, adultos, edades)

    out = [f"🏨 Hoteles en {c['name'] or c['code']} ({c['code']}) · {entrada:%d/%m/%Y} → {salida:%d/%m/%Y}"]
    try:
        res = await hoteles.buscar(c, entrada, salida, adultos, edades, n=30)
    except travelc.CompositorError:
        res = []
    res = sorted(res, key=lambda h: h["precio"])[:n]
    if res:
        out.append("Más baratos (precio total de la estancia):")
        for i, h in enumerate(res, 1):
            valor = f"{h['rating']} {h['grado']}".strip() if h.get("rating") else ""
            extra = " · ".join(p for p in (h.get("regimen"), valor) if p)
            out.append(f"{i}. {h['nombre']} · {h['precio_texto']}" + (f" · {extra}" if extra else ""))
    else:
        out.append("No pude traer las opciones ahora mismo.")
    out.append(f"Ver todos y reservar: {url}")
    return "\n".join(out)


_BUSCAR_PAQUETES_DESC = (
    "Cotiza paquetes VUELO + HOTEL en Travel Compositor: devuelve EN VIVO el precio del paquete "
    "'desde' por persona (combinación más barata), el vuelo incluido, opciones de hotel y el enlace "
    "para armarlo y reservar. Resuelve nombres de ciudad a su código IATA. Úsala cuando el cliente "
    "quiera un viaje completo (vuelo + alojamiento juntos). El precio es por persona e incluye vuelo "
    "y hotel, y cambia según el hotel elegido. No inventes precios; si no hay resultados, da el enlace."
)


@mcp.tool(description=_BUSCAR_PAQUETES_DESC)
async def buscar_paquetes(
    origen: Annotated[str, Field(description="Ciudad o código IATA de origen, p. ej. 'Bogotá' o 'BOG'.")],
    destino: Annotated[str, Field(description="Ciudad o código IATA de destino, p. ej. 'Cali' o 'CLO'.")],
    fecha_ida: Annotated[str, Field(description="Fecha de ida / inicio del viaje en formato AAAA-MM-DD.")],
    fecha_vuelta: Annotated[str, Field(description="Fecha de regreso / fin del viaje en formato AAAA-MM-DD.")],
    adultos: Annotated[int, Field(description="Número de adultos.", ge=1)] = 1,
    ninos_edades: Annotated[list[int], Field(description="Edad (en años) de cada niño; p. ej. [10, 12].")] = [],
    n: Annotated[int, Field(description="Cuántas opciones de hotel mostrar.", ge=1, le=15)] = 5,
) -> str:
    o = await _ciudad(origen, "origen")
    d = await _ciudad(destino, "destino")
    ida = _fecha(fecha_ida)
    vuelta = _fecha(fecha_vuelta)
    edades = ninos_edades or None
    url = compositor.url_paquetes(o["code"], d["code"], ida, vuelta, adultos, edades)

    out = [f"🧳 Paquete vuelo+hotel · {o['name'] or o['code']} ({o['code']}) → {d['name'] or d['code']} ({d['code']}) · {ida:%d/%m/%Y} → {vuelta:%d/%m/%Y}"]
    try:
        res = await paquetes.buscar(o, d, ida, vuelta, adultos, edades, n=n)
    except travelc.CompositorError:
        res = {}
    if res.get("precio_desde"):
        out.append(f"Desde {res['precio_desde']} por persona (vuelo + hotel)")
        v = res.get("vuelo") or {}
        if v.get("compania"):
            linea = f"✈️ Vuelo incluido: {v['compania']} · {v.get('salida', '')}→{v.get('llegada', '')}"
            if v.get("escalas"):
                linea += f" · {v['escalas']}"
            out.append(linea)
        for h in res.get("hoteles") or []:
            out.append(f"🏨 {h['nombre']} ({h['extra']})")
    else:
        out.append("No pude traer las opciones ahora mismo.")
    out.append(f"Arma tu paquete y reserva aquí: {url}")
    return "\n".join(out)
