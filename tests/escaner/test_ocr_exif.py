"""Regresion: ProcesadorImagen debe respetar el tag EXIF Orientation.

Bug real: procesar() decodificaba con cv2.imdecode directo, que ignora EXIF,
mientras el metodo que si lo corregia (_decodificar_respetando_exif) existia
pero nunca se llamaba. Fotos verticales de movil (iOS/Android) llegaban
giradas a Tesseract y el OCR no reconocia nada.
"""
import io
import sys
import os

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.procesador_imagen import ProcesadorImagen


def _imagen_con_exif_rotado(orientation):
    """Genera un JPEG en bytes: pixeles en horizontal (200x100) con un tag
    EXIF Orientation que indica "rotar para verse en vertical (100x200)",
    igual que graban las camaras de movil."""
    img = Image.new("RGB", (200, 100), "white")
    buf = io.BytesIO()
    exif = img.getexif()
    exif[0x0112] = orientation  # tag Orientation
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_procesar_aplica_rotacion_exif_vertical():
    procesador = ProcesadorImagen()
    imagen_bytes = _imagen_con_exif_rotado(6)  # 6 = rotar 90 CW al mostrar

    resultado = procesador._decodificar_respetando_exif(imagen_bytes)

    assert resultado is not None
    alto, ancho = resultado.shape[:2]
    # Pixeles originales 200x100 (horizontal); con EXIF 6 aplicado deben
    # quedar en pie: 100x200 (alto > ancho).
    assert alto == 200 and ancho == 100


def test_procesar_sin_exif_no_falla():
    procesador = ProcesadorImagen()
    img = Image.new("RGB", (50, 50), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    resultado = procesador.procesar(buf.getvalue())

    assert resultado is not None
    assert isinstance(resultado, np.ndarray)
