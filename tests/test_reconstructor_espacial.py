"""Tests de reconstructor_espacial: agrupa palabras de `image_to_data`
(coordenadas por palabra de Tesseract) en líneas visuales por proximidad
vertical, en vez de fiarse del renderizado interno de `image_to_string`.

No requieren imagen ni Tesseract real: se construyen dicts con la misma
forma que devuelve `pytesseract.image_to_data(..., output_type=Output.DICT)`.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.reconstructor_espacial import (
    reconstruir_lineas,
    lineas_a_texto,
    Palabra,
)


def _datos_tesseract(palabras):
    """Construye un dict con la forma de image_to_data a partir de tuplas
    (texto, izquierda, arriba, ancho, alto, confianza)."""
    datos = {"text": [], "left": [], "top": [], "width": [], "height": [], "conf": []}
    for texto, izquierda, arriba, ancho, alto, confianza in palabras:
        datos["text"].append(texto)
        datos["left"].append(izquierda)
        datos["top"].append(arriba)
        datos["width"].append(ancho)
        datos["height"].append(alto)
        datos["conf"].append(confianza)
    return datos


def test_palabras_en_la_misma_fila_forman_una_sola_linea():
    # "2 LECHE ENTERA 1L        2,50" - mismo Y, con un hueco grande entre
    # el nombre y el precio (alineado a la derecha), como en un ticket real.
    datos = _datos_tesseract([
        ("2", 10, 100, 15, 20, 95),
        ("LECHE", 30, 102, 60, 20, 92),
        ("ENTERA", 95, 101, 70, 20, 90),
        ("1L", 170, 100, 25, 20, 88),
        ("2,50", 480, 103, 50, 20, 91),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 1
    assert lineas[0].texto == "2 LECHE ENTERA 1L 2,50"


def test_dos_filas_distintas_no_se_fusionan():
    datos = _datos_tesseract([
        ("PAN", 10, 100, 40, 20, 90),
        ("INTEGRAL", 55, 101, 70, 20, 90),
        ("LECHE", 10, 140, 50, 20, 90),
        ("ENTERA", 65, 139, 60, 20, 90),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 2
    assert lineas[0].texto == "PAN INTEGRAL"
    assert lineas[1].texto == "LECHE ENTERA"


def test_orden_de_entrada_desordenado_se_corrige_izquierda_a_derecha():
    # Tesseract no siempre entrega las palabras de una línea en orden X;
    # el reconstructor debe ordenarlas él mismo dentro de cada línea.
    datos = _datos_tesseract([
        ("ENTERA", 95, 100, 70, 20, 90),
        ("2", 10, 101, 15, 20, 90),
        ("LECHE", 30, 100, 60, 20, 90),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 1
    assert lineas[0].texto == "2 LECHE ENTERA"


def test_tokens_vacios_se_descartan_sin_romper_agrupacion():
    # Tesseract devuelve entradas sin texto para marcadores de bloque/línea.
    datos = _datos_tesseract([
        ("", 0, 0, 0, 0, -1),
        ("  ", 5, 5, 5, 5, -1),
        ("PAN", 10, 100, 40, 20, 90),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 1
    assert lineas[0].texto == "PAN"


def test_confianza_baja_no_se_descarta():
    # Una palabra real pero borrosa (confianza baja) no debe perderse: es la
    # única información disponible sobre ese hueco del ticket.
    datos = _datos_tesseract([
        ("PRODUCTO", 10, 100, 80, 20, 12),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 1
    assert lineas[0].texto == "PRODUCTO"
    assert lineas[0].confianza_media == 12


def test_lista_vacia_no_rompe():
    assert reconstruir_lineas(_datos_tesseract([])) == []


def test_inclinacion_leve_no_fragmenta_la_linea():
    # Ligera deriva vertical de izquierda a derecha (papel algo inclinado
    # tras la corrección de orientación, que solo actúa a partir de 5°):
    # cada palabra está cerca de la anterior aunque el centro Y global se
    # desplace varios píxeles a lo largo de toda la línea.
    datos = _datos_tesseract([
        ("YOGUR", 10, 100, 50, 20, 90),
        ("NATURAL", 65, 104, 70, 20, 90),
        ("0,75", 480, 109, 40, 20, 90),
    ])

    lineas = reconstruir_lineas(datos)

    assert len(lineas) == 1
    assert lineas[0].texto == "YOGUR NATURAL 0,75"


def test_lineas_a_texto_separa_con_saltos_de_linea():
    datos = _datos_tesseract([
        ("PAN", 10, 100, 40, 20, 90),
        ("LECHE", 10, 140, 50, 20, 90),
    ])

    texto = lineas_a_texto(reconstruir_lineas(datos))

    assert texto == "PAN\nLECHE"


def test_caja_de_palabra_calcula_bordes_y_centro():
    palabra = Palabra(texto="X", izquierda=10, arriba=20, ancho=30, alto=40, confianza=90)

    assert palabra.derecha == 40
    assert palabra.abajo == 60
    assert palabra.centro_x == 25
    assert palabra.centro_y == 40
