"""Parser de tickets de supermercado.

    modelos.py      TipoUnidad y LineaTicketMejorada
    vocabulario.py  unidades y palabras de control        patrones.py   expresiones regulares e importes
    secciones.py    inicio/fin de la zona de articulos    lineas.py     clasificacion de lineas
    cantidades.py   cantidad, unidad e importes           nombres.py    limpieza del nombre
    parser.py       ParserMejorado (une las piezas)
"""
from .modelos import LineaTicketMejorada, TipoUnidad, _sin_tildes
from .parser import ParserMejorado

__all__ = ["LineaTicketMejorada", "ParserMejorado", "TipoUnidad", "_sin_tildes"]
