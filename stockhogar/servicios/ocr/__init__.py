"""Módulo OCR para procesamiento de tickets.

GestorOCR y GroqOCR se eliminaron en la auditoria 2026-08 (A-7 y B-9): ninguno
tenia uso -- el unico consumidor era POST /api/ocr/procesar-ticket, que el
frontend nunca llamo -- y ambos leian el catalogo `productos` sin filtrar por
hogar y enviaban imagen + catalogo a un proveedor externo saltandose el opt-out
`usuario_ocr_local` y la cuota diaria. GroqOCR ademas apuntaba a un modelo sin
vision (habria fallado al activarlo) y a un cuarto proveedor que no figura en
la politica de privacidad. El escaner real vive en rutas/tickets.py: ClaudeOCR
como motor principal y el pipeline local (ExtractorTexto + ParserMejorado +
MatcherInteligente) como respaldo.
"""
from .procesador_imagen import ProcesadorImagen
from .extractor_texto import ExtractorTexto
from .parseador_ticket import ParseadorTicket
from .matcher_productos import MatcherProductos
from .parser_mejorado import ParserMejorado
from .matcher_inteligente import MatcherInteligente
from .procesador_tickets_v2 import ProcesadorTicketsV2, crear_respuesta_usuario
from .claude_ocr import ClaudeOCR

__all__ = [
    "ProcesadorImagen",
    "ExtractorTexto",
    "ParseadorTicket",
    "MatcherProductos",
    "ParserMejorado",
    "MatcherInteligente",
    "ProcesadorTicketsV2",
    "crear_respuesta_usuario",
    "ClaudeOCR",
]
