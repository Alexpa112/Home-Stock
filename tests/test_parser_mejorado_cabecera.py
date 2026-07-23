"""Test de regresión: el ParserMejorado (parser realmente usado en
/api/tickets/analizar) no debe colar líneas de cabecera del ticket
(nombre de tienda, dirección, CIF, teléfono) ni de fidelización
(puntos, monedero, saldo) como si fueran productos.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado


TICKET_EJEMPLO = """MERCADONA S.A.
CIF A12345678
Avda de la Industria 23
28100 Alcobendas
Tel 912345678
www.mercadona.es
Ticket 000123
Fecha 22/07/2026 18:30
LECHE ENTERA 1L        1,20
PAN DE MOLDE           1,50
MANZANAS 1KG   2,30
TOTAL                   5,00
TARJETA VISA
Ha ganado 10 puntos fidelidad
Saldo monedero: 3,50 EUR
Gracias por su visita
"""


def test_cabecera_y_fidelizacion_no_son_productos():
    parser = ParserMejorado()
    productos = parser.parsear(TICKET_EJEMPLO)

    nombres = [p.nombre for p in productos]

    assert len(productos) == 3
    assert any("Leche" in n for n in nombres)
    assert any("Pan" in n for n in nombres)
    assert any("Manzanas" in n for n in nombres)

    for n in nombres:
        assert "Tel" not in n
        assert "Cif" not in n
        assert "Alcobendas" not in n
        assert "Monedero" not in n
        assert "Fidelidad" not in n
