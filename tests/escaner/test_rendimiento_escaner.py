"""Optimizaciones de tiempo del escaner: que no cambien el resultado."""
import io
import unittest

import cv2
import numpy as np
from PIL import Image

from stockhogar.integraciones import ocr_rapid
from stockhogar.servicios.ocr.procesador_imagen import ProcesadorImagen
from stockhogar.utils.imagenes import validar_formato


def _png(ancho=300, alto=200):
    b = io.BytesIO()
    Image.new("RGB", (ancho, alto), (250, 250, 250)).save(b, "PNG")
    return b.getvalue()


class ValidarFormatoTests(unittest.TestCase):
    def test_valida_sin_recodificar(self):
        self.assertIsNone(validar_formato(_png(), "png"))

    def test_rechaza_formato_distinto_basura_y_bombas(self):
        self.assertEqual(validar_formato(_png(), "jpg"), "err_formato_no_permitido")
        self.assertEqual(validar_formato(b"no es una imagen", "png"), "err_formato_no_permitido")
        b = io.BytesIO()
        Image.new("1", (9000, 9000)).save(b, "PNG")
        self.assertEqual(validar_formato(b.getvalue(), "png"), "err_formato_no_permitido")

    def test_extension_no_cubierta_se_deja_pasar(self):
        self.assertIsNone(validar_formato(b"cualquier cosa", "heic"))


class AplanarIluminacionTests(unittest.TestCase):
    def test_fondo_reducido_equivale_al_completo(self):
        rng = np.random.default_rng(1)
        gris = np.full((1000, 800), 235, np.uint8)
        gris[:, :400] = (gris[:, :400] * np.linspace(0.45, 1, 400)).astype(np.uint8)  # sombra
        for y in range(40, 960, 40):
            gris[y:y + 6, 60:700] = rng.integers(20, 60)
        rapido = ProcesadorImagen._aplanar_iluminacion(gris)
        papel = cv2.dilate(gris, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        completo = cv2.divide(gris, cv2.GaussianBlur(papel, (0, 0), sigmaX=max(15, 800 // 60)), scale=255)
        self.assertLess(float(np.abs(rapido.astype(int) - completo.astype(int)).mean()), 3.0)
        # y la sombra queda aplanada: ambos lados del papel salen casi igual de claros
        self.assertLess(abs(float(rapido[100:900, 20:60].mean()) - float(rapido[100:900, 740:780].mean())), 12)

    def test_imagen_pequena_no_se_reduce(self):
        gris = np.full((200, 300), 200, np.uint8)
        self.assertEqual(ProcesadorImagen._aplanar_iluminacion(gris).shape, gris.shape)


class AjustesDelMotorTests(unittest.TestCase):
    def test_clasificador_de_angulo_apagado_por_defecto(self):
        self.assertFalse(ocr_rapid._USAR_CLASIFICADOR)

    def test_lado_maximo_por_defecto(self):
        img = np.full((4000, 2500, 3), 255, np.uint8)
        _, buf = cv2.imencode(".png", img)
        salida = ProcesadorImagen().procesar_para_motor_neuronal(buf.tobytes())
        self.assertLessEqual(max(salida.shape[:2]), 1600)


if __name__ == "__main__":
    unittest.main()
