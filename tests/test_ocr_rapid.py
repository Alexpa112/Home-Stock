"""Motor neuronal de OCR (RapidOCR): espacios, letras/digitos y degradacion."""
import unittest
from unittest.mock import patch

import numpy as np

from stockhogar.integraciones import ocr_rapid, ticket_ocr


def _cajas(texto, paso=10.0, ancho=8.0, espacios_vacios=False):
    """Cajas por caracter de un texto en paso fijo; un espacio ocupa su celda
    (o NO se emite caja y deja un hueco doble si espacios_vacios)."""
    cajas, x = [], 0.0
    for ch in texto:
        cajas.append([[x, 0], [x + ancho, 0], [x + ancho, 20], [x, 20]])
        x += paso
    return cajas


class ConEspaciosTests(unittest.TestCase):
    def test_reinserta_los_espacios_que_el_modelo_se_come(self):
        # "LECHE ENTERA" leido como "LECHEENTERA": el hueco de una celda entre E y E.
        texto = "LECHEENTERA"
        cajas = _cajas(texto)
        for i in range(5, len(cajas)):          # desde la segunda palabra, desplazada una celda
            for p in cajas[i]:
                p[0] += 10.0
        self.assertEqual(ocr_rapid._con_espacios(texto, cajas), "LECHE ENTERA")

    def test_no_parte_palabras_de_paso_regular(self):
        self.assertEqual(ocr_rapid._con_espacios("TOMATE", _cajas("TOMATE")), "TOMATE")

    def test_una_letra_estrecha_no_crea_un_espacio(self):
        # La "I" ocupa su celda pero es mas estrecha: su hueco libre es grande y NO hay espacio.
        cajas = _cajas("PAISANO")
        cajas[2] = [[20 + 2, 0], [20 + 6, 0], [20 + 6, 20], [20 + 2, 20]]
        self.assertEqual(ocr_rapid._con_espacios("PAISANO", cajas), "PAISANO")

    def test_si_las_cajas_no_casan_se_devuelve_el_texto_tal_cual(self):
        self.assertEqual(ocr_rapid._con_espacios("ABCDEF", _cajas("ABC")), "ABCDEF")


class ConfusionesTests(unittest.TestCase):
    def test_digito_dentro_de_una_palabra_es_una_letra(self):
        self.assertEqual(ocr_rapid._arreglar_confusiones("BR0C0LI QUE5O"), "BROCOLI QUESO")

    def test_tamanos_y_cantidades_no_se_tocan(self):
        for t in ("LECHE 1L", "ARROZ 500G", "2 x 1,85", "AGUA 1,5L", "A1 SALSA", "CAFE 3X"):
            with self.subTest(t=t):
                self.assertEqual(ocr_rapid._arreglar_confusiones(t), t)


class DegradacionTests(unittest.TestCase):
    def test_si_el_motor_no_esta_se_usa_tesseract(self):
        with patch.object(ocr_rapid, "disponible", return_value=False):
            self.assertIsNone(ticket_ocr._texto_con_motor_neuronal(b"x"))

    def test_si_el_motor_falla_se_usa_tesseract(self):
        with patch.object(ocr_rapid, "disponible", return_value=True), \
                patch.object(ticket_ocr._procesador_imagen, "procesar_para_motor_neuronal", side_effect=ValueError("x")):
            self.assertIsNone(ticket_ocr._texto_con_motor_neuronal(b"x"))

    def test_variable_de_entorno_fuerza_tesseract(self):
        with patch.dict("os.environ", {"DREAME_OCR": "tesseract"}):
            self.assertIsNone(ticket_ocr._texto_con_motor_neuronal(b"x"))

    def test_poca_lectura_neuronal_cae_a_tesseract(self):
        class _L:
            texto, y_centro, confianza_media = "SIN IMPORTES", 10.0, 90.0
        with patch.object(ticket_ocr, "_texto_con_motor_neuronal", return_value=("SIN IMPORTES", 0)), \
                patch.object(ticket_ocr._procesador_imagen, "procesar", return_value=np.full((10, 10), 255, np.uint8)), \
                patch.object(ticket_ocr, "_leer_pagina", return_value=([_L()], 95.0)) as leer, \
                patch.object(ticket_ocr, "_texto_con_relectura", return_value="TESSERACT"), \
                patch("builtins.open", unittest.mock.mock_open(read_data=b"x")):
            self.assertEqual(ticket_ocr.extraer_texto("x.jpg"), "TESSERACT")
        leer.assert_called()


@unittest.skipUnless(ocr_rapid.disponible(), "RapidOCR no instalado")
class MotorRealTests(unittest.TestCase):
    def test_lee_un_ticket_dibujado(self):
        import cv2
        img = np.full((260, 700, 3), 255, np.uint8)
        for i, linea in enumerate(["LECHE ENTERA 1L 0,89", "PAN DE MOLDE 2 x 1,85 3,70", "TOTAL 4,59"]):
            cv2.putText(img, linea, (20, 60 + 70 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 2)
        texto = "\n".join(l.texto for l in ocr_rapid.leer_lineas(img))
        for esperado in ("0,89", "3,70", "4,59"):
            self.assertIn(esperado, texto)


if __name__ == "__main__":
    unittest.main()
