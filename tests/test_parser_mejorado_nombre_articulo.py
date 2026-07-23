"""Test de regresión: el ParserMejorado no debe romper el nombre del
artículo cuando la cantidad va suelta delante del nombre (formato típico
de ticket "2 COCA COLA   1,80"), ni cuando la cantidad viene con unidad
real pegada al nombre ("LECHE ENTERA 1L   1,20").

Antes del fix, el regex de limpieza de nombre aceptaba cualquier palabra
tras un número como si fuera una unidad, así que "2 COCA COLA" perdía la
palabra "COCA" (se interpretaba "2 coca" como cantidad+unidad), rompiendo
el nombre y con ello el reconocimiento de categoría en el matcher.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado, TipoUnidad


def test_cantidad_suelta_delante_del_nombre_no_rompe_palabras():
    parser = ParserMejorado()
    texto = "2 COCA COLA           1,80\n"
    productos = parser.parsear(texto)

    assert len(productos) == 1
    assert productos[0].nombre == "Coca Cola"
    assert productos[0].cantidad == 2
    assert productos[0].precio_total == 1.80


def test_cantidad_con_unidad_real_se_extrae_y_limpia_bien():
    parser = ParserMejorado()
    texto = "LECHE ENTERA 1L        1,20\n"
    productos = parser.parsear(texto)

    assert len(productos) == 1
    assert productos[0].nombre == "Leche Entera"
    assert productos[0].cantidad == 1.0
    assert productos[0].unidad == TipoUnidad.LITRO
    assert productos[0].precio_total == 1.20


def test_articulo_sin_cantidad_explicita_se_reconoce_completo():
    parser = ParserMejorado()
    texto = "TOMATE                 0,90\n"
    productos = parser.parsear(texto)

    assert len(productos) == 1
    assert productos[0].nombre == "Tomate"
    assert productos[0].cantidad == 1
    assert productos[0].precio_total == 0.90


def test_varios_articulos_con_y_sin_cantidad_en_la_misma_linea():
    parser = ParserMejorado()
    texto = (
        "2 COCA COLA           1,80\n"
        "ARROZ SOS 1KG          3,00\n"
        "3 YOGUR NATURAL        2,10\n"
        "TOMATE                 0,90\n"
        "TOTAL                   10,50\n"
    )
    productos = parser.parsear(texto)
    nombres = {p.nombre for p in productos}

    assert nombres == {"Coca Cola", "Arroz Sos", "Yogur Natural", "Tomate"}
