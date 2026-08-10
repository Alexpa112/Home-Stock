"""Tests del ParserMejorado (pipeline local con Tesseract) sobre tres casos
que se le escapaban:

  * nombres con ruido de OCR ("T0MAT€5 FR€5C05"): la linea se descartaba
    porque se exigian 3 letras SEGUIDAS y los simbolos las separan;
  * lista de la compra sin cabecera ni precios: se perdia el primer articulo,
    porque la primera linea se daba por nombre de tienda siempre;
  * lineas de oferta/promocion: o se descartaba la linea entera (y con ella
    articulos reales como "OFERTA LECHE DESNATADA") o se colaba un articulo
    fantasma llamado "Oferta".
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado, TipoUnidad


def _nombres(texto):
    return [p.nombre for p in ParserMejorado().parsear(texto)]


def test_nombres_con_ruido_de_ocr_siguen_siendo_articulos():
    nombres = _nombres(
        "L€CH€ €NT€RA 1L        1,20\n"
        "T0MAT€5 FR€5C05 2kg    2,40\n"
        "TOTAL                  3,60\n"
    )
    assert len(nombres) == 2


def test_lista_sin_cabecera_ni_precios_no_pierde_el_primer_articulo():
    nombres = _nombres("Leche entera\nPan blanco\nManzanas\n")
    assert nombres == ["Leche Entera", "Pan Blanco", "Manzanas"]


def test_nombre_de_tienda_no_se_cuela_como_articulo():
    """La primera linea de un ticket con precios es el nombre de la tienda,
    aunque no contenga ninguna palabra tipica de cabecera."""
    nombres = _nombres(
        "LIDL\n"
        "LECHE ENTERA 1L   1,20\n"
        "PAN INTEGRAL      0,90\n"
        "TOTAL             2,10\n"
    )
    assert nombres == ["Leche Entera", "Pan Integral"]


def test_articulo_en_oferta_se_reconoce_como_articulo():
    nombres = _nombres(
        "OFERTA LECHE DESNATADA 1L   2,00\n"
        "PAN                         0,90\n"
        "TOTAL                       2,90\n"
    )
    assert nombres == ["Oferta Leche Desnatada", "Pan"]


def test_lineas_de_promocion_o_descuento_no_son_articulos():
    for ruido in ("OFERTA          -0,30", "PROMOCION 3X2", "AHORRO 0,50", "2X1"):
        nombres = _nombres(
            "LECHE 1L        1,20\n"
            f"{ruido}\n"
            "PAN             0,90\n"
            "TOTAL           2,10\n"
        )
        assert nombres == ["Leche", "Pan"], f"fallo con la linea {ruido!r}"


def test_precio_por_unidad_no_deja_la_unidad_pegada_al_nombre():
    """Con "@ 1.20€/kg" la limpieza dejaba el nombre como "Tomates /Kg"."""
    productos = ParserMejorado().parsear("Tomates 2kg @ 1.20€/kg    2,40\n")

    assert len(productos) == 1
    assert productos[0].nombre == "Tomates"
    assert productos[0].cantidad == 2
    assert productos[0].unidad == TipoUnidad.KILOGRAMO
