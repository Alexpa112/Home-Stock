"""Correccion fina de inclinacion del ticket (+-10 grados).

Antes solo se corregian giros de mas de 5 grados (Hough), pero una foto hecha a
mano se tuerce 1-5: justo la zona sin corregir. Con esa deriva el reconstructor
de lineas mezclaba palabras de renglones distintos.
"""
import io
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stockhogar.servicios.ocr.procesador_imagen import ProcesadorImagen

_LINEAS = [
    "MERCADONA S.A.  A-46103834", "C/ ALCALA 123  28009 MADRID", "12/10/2026 18:32",
    "1 LECHE ENTERA 1L             0,89", "2 PAN DE MOLDE        1,85    3,70",
    "1 TOMATE PERA", "  0,850 kg   1,89 EUR/kg      1,61", "1 HUEVOS CAMPEROS            2,45",
    "4 YOGUR NATURAL       0,55    2,20", "TOTAL (EUR)                  8,85",
]


def _ticket(angulo=0.0):
    try:
        fuente = ImageFont.truetype("DejaVuSansMono.ttf", 22)
    except OSError:
        fuente = ImageFont.load_default()
    img = Image.new("L", (760, 40 + 32 * len(_LINEAS)), 250)
    d = ImageDraw.Draw(img)
    for i, linea in enumerate(_LINEAS):
        d.text((20, 20 + 32 * i), linea, font=fuente, fill=20)
    if angulo:
        img = img.rotate(angulo, expand=True, fillcolor=250, resample=Image.BICUBIC)
    return np.array(img)


class InclinacionTests(unittest.TestCase):
    def setUp(self):
        self.p = ProcesadorImagen()

    def test_estima_el_angulo_con_su_signo_hasta_9_grados(self):
        for giro in (-9, -6, -3.5, -2, -1, 1, 2, 3.5, 6, 9):
            with self.subTest(giro=giro):
                estimado = self.p._estimar_inclinacion_texto(_ticket(giro))
                self.assertAlmostEqual(estimado, -giro, delta=0.5)

    def test_un_ticket_recto_no_se_toca(self):
        self.assertEqual(self.p._estimar_inclinacion_texto(_ticket(0)), 0.0)
        gris = _ticket(0)
        self.assertIs(self.p._corregir_inclinacion_fina(gris), gris)

    def test_una_imagen_sin_texto_no_provoca_giros_ni_errores(self):
        self.assertEqual(self.p._estimar_inclinacion_texto(np.full((400, 300), 250, np.uint8)), 0.0)
        self.assertEqual(self.p._estimar_inclinacion_texto(np.zeros((400, 300), np.uint8)), 0.0)

    def test_tras_procesar_el_texto_queda_horizontal(self):
        for giro in (-3.5, 2, 3.5):
            with self.subTest(giro=giro):
                b = io.BytesIO()
                Image.fromarray(_ticket(giro)).convert("RGB").save(b, "PNG")
                salida = self.p.procesar(b.getvalue())
                self.assertAlmostEqual(self.p._estimar_inclinacion_texto(salida), 0.0, delta=0.75)

    def test_el_tope_es_10_grados(self):
        self.assertEqual(ProcesadorImagen._INCLINACION_MAXIMA, 10.0)


if __name__ == "__main__":
    unittest.main()
