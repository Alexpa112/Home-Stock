"""Módulo OCR para procesamiento de tickets."""
from .procesador_imagen import ProcesadorImagen
from .extractor_texto import ExtractorTexto
from .parseador_ticket import ParseadorTicket
from .matcher_productos import MatcherProductos
from .gestor_ocr import GestorOCR

__all__ = [
    "ProcesadorImagen",
    "ExtractorTexto",
    "ParseadorTicket",
    "MatcherProductos",
    "GestorOCR",
]
