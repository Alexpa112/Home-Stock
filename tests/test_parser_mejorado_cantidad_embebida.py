"""Test de regresión: el ParserMejorado no debe confundir el tamaño del
envase impreso en el nombre (p.ej. "1L", "1,5L") con la cantidad realmente
comprada cuando esta va suelta al principio de la línea, ni debe crear un
producto fantasma con la línea de detalle de peso/precio de un artículo
vendido a granel (formato en dos líneas: nombre, luego peso/precio).

Antes del fix, "2 LECHE PASCUAL 1L" se leía como 1 litro (en vez de 2
unidades) y "TOMATE PERA KG" + "0,850 kg 1,89 EUR/kg 1,61" generaba un
segundo producto fantasma llamado "Eur/Kg".
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado, TipoUnidad


def test_cantidad_suelta_no_se_confunde_con_tamano_de_envase():
    parser = ParserMejorado()
    texto = "2 LECHE PASCUAL 1L        2,40\n3 COCA COLA 1,5L          5,85\n"
    productos = parser.parsear(texto)

    assert len(productos) == 2
    leche, cola = productos

    assert leche.nombre == "Leche Pascual"
    assert leche.cantidad == 2
    assert leche.unidad == TipoUnidad.UNIDAD

    assert cola.nombre == "Coca Cola"
    assert cola.cantidad == 3
    assert cola.unidad == TipoUnidad.UNIDAD


def test_linea_de_peso_a_granel_se_fusiona_con_el_articulo_anterior():
    parser = ParserMejorado()
    texto = (
        "MERCADONA S.A.\n"
        "CIF A12345678\n"
        "TOMATE PERA KG\n"
        "0,850 kg  1,89 EUR/kg     1,61\n"
        "TOTAL                      1,61\n"
    )
    productos = parser.parsear(texto)

    assert len(productos) == 1
    tomate = productos[0]
    assert "Tomate" in tomate.nombre
    assert tomate.cantidad == 0.85
    assert tomate.unidad == TipoUnidad.KILOGRAMO
    assert tomate.precio_unitario == 1.89
    assert tomate.precio_total == 1.61


def test_marcador_de_promocion_no_ensucia_el_nombre():
    parser = ParserMejorado()
    texto = "2X1 GALLETAS MARIA         1,80\n"
    productos = parser.parsear(texto)

    assert len(productos) == 1
    galletas = productos[0]
    assert galletas.nombre == "Galletas Maria"
    assert galletas.es_promocion is True
