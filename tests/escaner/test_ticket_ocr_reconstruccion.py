"""Test de regresión: ticket_ocr.extraer_texto debe reconstruir las líneas
por coordenadas (image_to_data), no fiarse del renderizado interno de
Tesseract (image_to_string).

Antes del fix, dos palabras de una misma línea visual pero con un hueco
grande entre medias (p.ej. nombre del artículo ... precio alineado a la
derecha) podían llegar a ParserMejorado en líneas de texto separadas si
Tesseract decidía cortar ahí, sin ninguna forma de corregirlo aguas abajo.
"""
import io
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

from stockhogar.integraciones import ticket_ocr


def _datos_tesseract_dos_lineas():
    return {
        "text": ["2", "LECHE", "ENTERA", "2,50", "PAN", "INTEGRAL", "1,49"],
        "left": [10, 30, 95, 480, 10, 55, 480],
        "top": [100, 102, 101, 103, 140, 141, 142],
        "width": [15, 60, 70, 50, 40, 70, 50],
        "height": [20, 20, 20, 20, 20, 20, 20],
        "conf": [95, 92, 90, 91, 90, 90, 90],
    }


def test_extraer_texto_usa_image_to_data_y_reconstruye_por_coordenadas(tmp_path):
    ruta_imagen = tmp_path / "ticket.png"
    Image.new("RGB", (50, 50), "white").save(ruta_imagen)

    with patch(
        "stockhogar.integraciones.ticket_ocr.pytesseract.image_to_data",
        return_value=_datos_tesseract_dos_lineas(),
    ) as mock_image_to_data, patch(
        "stockhogar.integraciones.ticket_ocr.pytesseract.image_to_string"
    ) as mock_image_to_string:
        texto = ticket_ocr.extraer_texto(str(ruta_imagen))

    mock_image_to_data.assert_called_once()
    mock_image_to_string.assert_not_called()
    assert texto == "2 LECHE ENTERA 2,50\nPAN INTEGRAL 1,49"


def test_extraer_texto_propaga_timeout_como_error_legible(tmp_path):
    ruta_imagen = tmp_path / "ticket.png"
    Image.new("RGB", (50, 50), "white").save(ruta_imagen)

    with patch(
        "stockhogar.integraciones.ticket_ocr.pytesseract.image_to_data",
        side_effect=RuntimeError("Tesseract process timeout"),
    ):
        try:
            ticket_ocr.extraer_texto(str(ruta_imagen))
            assert False, "debia lanzar RuntimeError"
        except RuntimeError as e:
            assert "tardó demasiado" in str(e)
