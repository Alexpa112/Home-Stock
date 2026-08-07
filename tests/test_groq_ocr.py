"""Tests de GroqOCR (motor principal de reconocimiento de tickets) y de
que GestorOCR cae al pipeline local (Tesseract) cuando Groq no está
disponible o falla la llamada.

Sin red real: se mockea requests.post. Sin servidor externo ni stock.db real:
create_app()/test_client() con base de datos temporal (patrón estándar del
proyecto).
"""
import unittest
from unittest.mock import patch, MagicMock

from stockhogar import create_app
from stockhogar.db import get_db
from stockhogar.servicios.ocr.groq_ocr import GroqOCR
from stockhogar.servicios.ocr.gestor_ocr import GestorOCR


class GroqOCRTests(unittest.TestCase):
    def test_no_disponible_sin_api_key(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("GROQ_API_KEY", None)
            motor = GroqOCR()
            self.assertFalse(motor.disponible())
            self.assertIsNone(motor.procesar(b"fake", [{"id": 1, "nombre": "Leche"}]))

    @patch("stockhogar.servicios.ocr.groq_ocr.requests.post")
    def test_procesa_respuesta_valida(self, mock_post):
        respuesta_json = {
            "choices": [{
                "message": {
                    "content": (
                        '{"productos": [{"nombre_ticket": "LECHE PASC 1L", '
                        '"producto_id": 5, "cantidad": 2, "unidad": "ud"}]}'
                    )
                }
            }]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = respuesta_json
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {"GROQ_API_KEY": "clave_falsa"}):
            motor = GroqOCR()
            resultado = motor.procesar(b"fake", [{"id": 5, "nombre": "Leche entera"}])

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["productos"][0]["producto_id"], 5)
        self.assertEqual(resultado["productos"][0]["cantidad"], 2)

    @patch("stockhogar.servicios.ocr.groq_ocr.requests.post")
    def test_fallo_de_red_devuelve_none(self, mock_post):
        mock_post.side_effect = Exception("sin conexion")

        with patch.dict("os.environ", {"GROQ_API_KEY": "clave_falsa"}):
            motor = GroqOCR()
            resultado = motor.procesar(b"fake", [{"id": 1, "nombre": "Leche"}])

        self.assertIsNone(resultado)


class GestorOCRFallbackTests(unittest.TestCase):
    """Verifica que, si Groq falla, el gestor sigue funcionando con el
    pipeline local en vez de romperse."""

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)

    def test_claude_no_disponible_usa_pipeline_local(self):
        gestor = GestorOCR()
        with patch.object(gestor.claude, "disponible", return_value=False):
            with self.app.app_context():
                db = get_db()
                # Imagen invalida: el pipeline local debe fallar de forma
                # controlada (error en el dict de resultado), no reventar.
                resultado = gestor.procesar_ticket(b"no-es-una-imagen-real", db)

        self.assertFalse(resultado["exito"])
        self.assertIsNotNone(resultado["error"])

    def test_respuesta_ia_mapea_encontrado_y_no_encontrado(self):
        gestor = GestorOCR()
        respuesta_ia = {
            "productos": [
                {"nombre_ticket": "LECHE PASC 1L", "producto_id": 999999, "cantidad": 2, "unidad": "ud"},
                {"nombre_ticket": "ARTICULO RARO XYZ", "producto_id": None, "cantidad": 1, "unidad": "ud"},
            ]
        }
        catalogo = [{"id": 999999, "nombre": "Leche entera", "categoria": "Lácteos y Huevos", "icono": "🥛"}]

        productos = gestor._mapear_respuesta_ia(respuesta_ia, catalogo)

        self.assertEqual(len(productos), 2)
        self.assertTrue(productos[0]["encontrado"])
        self.assertEqual(productos[0]["nombre"], "Leche entera")
        self.assertEqual(productos[0]["cantidad"], 2)
        self.assertFalse(productos[1]["encontrado"])
        self.assertEqual(productos[1]["nombre"], "Articulo Raro Xyz")


if __name__ == "__main__":
    unittest.main()
