from typing import Optional

from pydantic import BaseModel, Field


class Precio(BaseModel):
    columna: str = Field(description="Nombre de la columna de la tabla: un hotel, un plan, o un tipo de acomodación (DOBLE, NIÑO, SENCILLA...).")
    valor: Optional[int] = Field(description="Precio en pesos colombianos como entero (p. ej. 1219000), o null si la celda no es un precio (AGOTADO, un recorrido de crucero, etc.).")
    texto: Optional[str] = Field(description="Texto original de la celda cuando no es un número, p. ej. 'AGOTADO' o el recorrido del crucero. null si es un precio normal.")


class Tarifa(BaseModel):
    fecha: str = Field(description="Fecha o rango de fechas del viaje, sin la palabra OFERTA ni emojis.")
    es_oferta: bool = Field(description="True si la fila está marcada como OFERTA.")
    precios: list[Precio] = Field(description="Un Precio por cada columna de precio de la fila.")


class Hotel(BaseModel):
    nombre: str
    descripcion: Optional[str] = Field(description="Descripción del hotel si aparece, si no null.")
    precio_adulto: Optional[int] = Field(description="Precio por adulto en COP si aparece, si no null.")
    precio_nino: Optional[int] = Field(description="Precio por niño en COP si aparece, si no null.")


class Resumen(BaseModel):
    titular: Optional[str] = Field(description="Titular tipo 'VIAJA 4 DÍAS 3 NOCHES DESDE $...' o equivalente.")
    descripcion: Optional[str] = Field(description="Frase(s) descriptivas introductorias del destino.")
    incluye: Optional[str] = Field(description="Texto de lo que incluye el plan.")
    no_incluye: Optional[str] = Field(description="Texto de lo que NO incluye el plan.")
    nota: Optional[str] = Field(description="Nota con asterisco sobre tarifas/acomodación.")


class Destino(BaseModel):
    oferta: Optional[str] = Field(description="Nombre de la oferta, p. ej. 'OFERTA SAN ANDRÉS'.")
    resumen: Resumen
    aclaraciones: Optional[str] = Field(description="Avisos importantes (vacunas, requisitos). null si no hay.")
    hoteles: list[Hotel] = Field(description="Hoteles/alojamientos del destino. Vacío si el destino no lista hoteles (tours, cruceros).")
    tarifas: list[Tarifa] = Field(description="Filas de la tabla de fechas y precios.")
    condiciones: Optional[str] = Field(description="Condiciones de pago/abono ('Separa con...').")
