"""Tipos de datos del parser de tickets: unidades y linea interpretada."""
import unicodedata
from dataclasses import dataclass
from enum import Enum


def _sin_tildes(texto: str) -> str:
    """Quita diacríticos (á->a, ñ->n...) para comparar palabras clave sin
    depender de que el OCR acierte los acentos."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


class TipoUnidad(Enum):
    """Tipos de unidades detectadas en tickets."""
    UNIDAD = "ud"
    KILOGRAMO = "kg"
    GRAMO = "g"
    LITRO = "l"
    MILILITRO = "ml"
    PAQUETE = "paq"
    DESCONOCIDA = "desconocida"


@dataclass
class LineaTicketMejorada:
    """Línea mejorada con más contexto."""
    nombre: str
    cantidad: float
    unidad: TipoUnidad
    cantidad_texto: str  # "2 kg", "1.5 l", etc.
    precio_unitario: float = 0
    precio_total: float = 0
    confianza_nombre: float = 100
    confianza_cantidad: float = 100
    es_promocion: bool = False
    linea_original: str = ""
    descuento: float = 0  # importe descontado de precio_total (lineas "Desc. -0,30")
