from __future__ import annotations

from datetime import date

BASE = "https://ofertas.avioa.co/home"
_FECHA = "%d/%m/%Y"  # SIEMPRE en este formato


def _distribution(adultos: int, ninos_edades: list[int]) -> str:
    """'2-0' (2 adultos, 0 niños), '2-1-0' (2 ad., 1 niño de 0 años),
    '2-2-10,4' (2 ad., 2 niños de 10 y 4 años)."""
    if not ninos_edades:
        return f"{adultos}-0"
    return f"{adultos}-{len(ninos_edades)}-{','.join(str(e) for e in ninos_edades)}"


def params(
    origen: str,
    destino: str,
    fecha_ida: date,
    fecha_retorno: date | None = None,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> list[tuple[str, str]]:
    """Parámetros de búsqueda (orden y valores crudos). Fuente única para el link y el scrape.

    Mapeo del proveedor: `departure` = origen (desde dónde), `destination` = destino (hacia dónde).
    Ida y vuelta si se pasa `fecha_retorno`; si no, solo ida (sin `arrivalDate`).
    `ninos_edades`: edades de cada niño; arma la `distribution` con los adultos.
    """
    p = [
        ("directSubmit", "true"),
        ("tripType", "ONLY_FLIGHT"),
        ("destination", f"Destination::{destino.strip().upper()}"),
        ("departure", f"Destination::{origen.strip().upper()}"),
        ("departureDate", fecha_ida.strftime(_FECHA)),
    ]
    if fecha_retorno is not None:
        p.append(("arrivalDate", fecha_retorno.strftime(_FECHA)))
    p += [
        ("roundTripFlight", "true" if fecha_retorno is not None else "false"),
        ("distribution", _distribution(adultos, ninos_edades or [])),
        ("businessCabin", "false"),
        ("lang", "ES"),
        ("displayCurrency", "COP"),
    ]
    return p


def url_vuelos(
    origen: str,
    destino: str,
    fecha_ida: date,
    fecha_retorno: date | None = None,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> str:
    """URL (deep-link) de búsqueda de vuelos de Travel Compositor. origen/destino = IATA de ciudad."""
    p = params(origen, destino, fecha_ida, fecha_retorno, adultos, ninos_edades)
    return BASE + "?" + "&".join(f"{k}={v}" for k, v in p)


def params_hotel(
    ciudad: str,
    fecha_entrada: date,
    fecha_salida: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> list[tuple[str, str]]:
    """Parámetros de búsqueda de HOTEL (valores crudos). Una sola ciudad (`hotelDestination`);
    `departureDate`=check-in, `arrivalDate`=check-out. Fijos: ES, sourceMarket=CO, COP, sin coche."""
    return [
        ("directSubmit", "true"),
        ("tripType", "ONLY_HOTEL"),
        ("distribution", _distribution(adultos, ninos_edades or [])),
        ("lang", "ES"),
        ("sourceMarket", "CO"),
        ("displayCurrency", "COP"),
        ("carRental", "false"),
        ("hotelDestination", f"Destination::{ciudad.strip().upper()}"),
        ("departureDate", fecha_entrada.strftime(_FECHA)),
        ("arrivalDate", fecha_salida.strftime(_FECHA)),
    ]


def url_hoteles(
    ciudad: str,
    fecha_entrada: date,
    fecha_salida: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> str:
    """URL (deep-link) de búsqueda de hoteles de Travel Compositor. ciudad = IATA de ciudad."""
    p = params_hotel(ciudad, fecha_entrada, fecha_salida, adultos, ninos_edades)
    return BASE + "?" + "&".join(f"{k}={v}" for k, v in p)


def params_paquete(
    origen: str,
    destino: str,
    fecha_ida: date,
    fecha_vuelta: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> list[tuple[str, str]]:
    """Parámetros de PAQUETE vuelo+hotel (valores crudos). Como vuelos (origen+destino,
    `departure`=origen/`destination`=destino) pero `tripType=FLIGHT_HOTEL` y sin `roundTripFlight`;
    `departureDate`/`arrivalDate` = inicio/fin del viaje (= check-in/check-out)."""
    return [
        ("directSubmit", "true"),
        ("tripType", "FLIGHT_HOTEL"),
        ("destination", f"Destination::{destino.strip().upper()}"),
        ("departure", f"Destination::{origen.strip().upper()}"),
        ("departureDate", fecha_ida.strftime(_FECHA)),
        ("arrivalDate", fecha_vuelta.strftime(_FECHA)),
        ("distribution", _distribution(adultos, ninos_edades or [])),
        ("businessCabin", "false"),
        ("lang", "ES"),
        ("displayCurrency", "COP"),
    ]


def url_paquetes(
    origen: str,
    destino: str,
    fecha_ida: date,
    fecha_vuelta: date,
    adultos: int = 1,
    ninos_edades: list[int] | None = None,
) -> str:
    """URL (deep-link) de búsqueda de paquetes vuelo+hotel. origen/destino = IATA de ciudad."""
    p = params_paquete(origen, destino, fecha_ida, fecha_vuelta, adultos, ninos_edades)
    return BASE + "?" + "&".join(f"{k}={v}" for k, v in p)
