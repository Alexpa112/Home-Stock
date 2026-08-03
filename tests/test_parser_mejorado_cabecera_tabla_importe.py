"""Test de regresión: la cabecera de la tabla de productos ("Descripción
P. Unit Importe", habitual en tickets Mercadona) no debe confundirse con
el cierre de la compra (TOTAL/TARJETA/...) solo porque contiene la
palabra "Importe". Antes de este fix, _detectar_fin_productos cortaba el
ticket en esa cabecera -ANTES de llegar a los productos reales- y
/api/tickets/analizar devolvía 0 items pese a que el OCR leía el ticket
correctamente (ver logs/stockhogar.log, 2026-08-03 20:23:02).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado


TICKET_MERCADONA_REAL = """MERCADONA, S.A. A-46103834
AVDA. MADRID, 108
36214 VIGO
TELÉFONO: 986616271
28/07/2026 19:15 OP: 4351106
FACTURA SIMPLIFICADA: 4140-016-609067
Descripción P. Unit Importe
1 POPITOS 1,50
1 FRESA-PASTEL DE QUES 3,00
1 HELADO LIMA LIMÓN 2,30
TOTAL (€) 6,80
TARJETA BANCARIA 6,80
IVA BASE IMPONIBLE (€) CUOTA (€)
10% 4.82 0,48
21% 1,24 0,26
"""


def test_cabecera_de_tabla_con_importe_no_corta_los_productos():
    parser = ParserMejorado()
    productos = parser.parsear(TICKET_MERCADONA_REAL)

    nombres = [p.nombre for p in productos]

    assert len(productos) == 3
    assert any("Popitos" in n for n in nombres)
    assert any("Fresa" in n for n in nombres)
    assert any("Helado" in n for n in nombres)
