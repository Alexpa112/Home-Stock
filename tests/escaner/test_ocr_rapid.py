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


class EleccionEntreMotoresTests(unittest.TestCase):
    def _extraer(self, neuronal, tesseract=None, tesseract_falla=False):
        with patch.object(ticket_ocr, "_texto_con_motor_neuronal", return_value=neuronal), \
                patch.object(ticket_ocr, "_texto_con_tesseract",
                             side_effect=(RuntimeError("lento") if tesseract_falla else None),
                             return_value=tesseract), \
                patch("builtins.open", unittest.mock.mock_open(read_data=b"x")):
            return ticket_ocr.extraer_texto("x.jpg")

    def test_neuronal_con_importes_suficientes_no_llama_a_tesseract(self):
        with patch.object(ticket_ocr, "_texto_con_motor_neuronal", return_value=("A 1,00\nB 2,00", 2)), \
                patch.object(ticket_ocr, "_texto_con_tesseract") as t, \
                patch("builtins.open", unittest.mock.mock_open(read_data=b"x")):
            self.assertEqual(ticket_ocr.extraer_texto("x.jpg"), "A 1,00\nB 2,00")
        t.assert_not_called()

    def test_si_los_dos_leen_poco_gana_el_que_lee_mas_importes(self):
        self.assertEqual(self._extraer(("PAN 1,00", 1), "PAN\nLECHE"), "PAN 1,00")
        self.assertEqual(self._extraer(("PAN", 0), "PAN 1,00"), "PAN 1,00")

    def test_empate_gana_el_neuronal(self):
        self.assertEqual(self._extraer(("NEURONAL", 0), "TESSERACT"), "NEURONAL")

    def test_si_tesseract_se_pasa_de_tiempo_se_devuelve_lo_del_neuronal(self):
        self.assertEqual(self._extraer(("PAN 1,00", 1), tesseract_falla=True), "PAN 1,00")

    def test_sin_neuronal_el_error_de_tesseract_sigue_siendo_error(self):
        with self.assertRaises(RuntimeError):
            self._extraer(None, tesseract_falla=True)

    def test_sin_neuronal_se_usa_tesseract_tal_cual(self):
        self.assertEqual(self._extraer(None, "TESSERACT"), "TESSERACT")


class ConcurrenciaTests(unittest.TestCase):
    def test_hay_un_limite_de_lecturas_simultaneas(self):
        self.assertTrue(hasattr(ocr_rapid, "_turno"))
        self.assertGreaterEqual(ocr_rapid._CONCURRENCIA, 1)
