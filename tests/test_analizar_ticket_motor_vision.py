"""Tests de regresion de /api/tickets/analizar con el motor de vision.

1) Articulo nuevo -> 500. _items_desde_ia no rellenaba las claves que
   crear_respuesta_usuario() -> sugerir_correccion() lee por indice
   ("alternativas", "razon_precio", "cantidad_sugerida", "es_promocion"), y esa
   funcion entra en la rama de "alternativas" para todo articulo con
   confianza_match < 0.7, es decir para CUALQUIER articulo que no estuviera ya
   en el catalogo. Resultado: en cuanto Claude reconocia un producto nuevo -lo
   normal con un catalogo pequeño- el escaner respondia "Ha ocurrido un error
   interno". Solo parecia funcionar con el pipeline local, que si las rellenaba.

2) Lista vacia -> sin reintento. El fallback al pipeline local se activaba solo
   si la llamada FALLABA (items is None). Si Claude respondia bien pero sin
   articulos -foto oscura, ticket arrugado- el usuario recibia "0 articulos"
   sin haberse intentado Tesseract.
"""
import io
import unittest
import uuid
from unittest.mock import patch

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

TEXTO_OCR = "LECHE ENTERA 1L   1,20\nPAN INTEGRAL      0,90\nTOTAL             2,10\n"


class _ClaudeFalso:
    """Motor de vision que devuelve lo que se le indique."""

    respuesta = {"productos": []}

    def disponible(self):
        return True

    def procesar(self, imagen_bytes, productos_catalogo, mime=None):
        return type(self).respuesta


class AnalizarTicketMotorVisionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_fb_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista fallback", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

        buffer = io.BytesIO()
        Image.new("RGB", (400, 700), (255, 255, 255)).save(buffer, format="JPEG")
        self.foto = buffer.getvalue()
        _ClaudeFalso.respuesta = {"productos": []}

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _analizar(self):
        return self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(self.foto), "ticket.jpg")},
            content_type="multipart/form-data",
        )

    def test_articulo_nuevo_no_rompe_la_respuesta(self):
        """Un articulo que no esta en el catalogo (confianza_match 0) devolvia
        500 al construir sus sugerencias."""
        _ClaudeFalso.respuesta = {
            "productos": [
                {"nombre_ticket": "Chorizo de Pamplona", "cantidad": 1, "unidad": "ud", "producto_id": None}
            ]
        }
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            resp = self._analizar()

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        item = datos["items"][0]
        self.assertEqual(item["nombre"], "Chorizo De Pamplona")
        self.assertIsNone(item["producto_id"])
        # Se marca para revision y se ofrece la lista (vacia) de alternativas.
        self.assertEqual(item["sugerencias"]["correcciones"][0]["tipo"], "match_bajo")
        self.assertEqual(item["sugerencias"]["correcciones"][0]["alternativas"], [])
        self.assertTrue(datos["resumen"]["requiere_revision"])
        self.assertEqual(datos["resumen"]["items_sin_match"], 1)

    def test_articulo_del_catalogo_se_devuelve_emparejado(self):
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, icono, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, ?, ?, ?)",
                ("Leche entera 1L", "Bebidas", "🥛", ahora(), ahora()),
            )
            producto_id = cur.lastrowid
            db.commit()

        _ClaudeFalso.respuesta = {
            "productos": [
                {"nombre_ticket": "LCH ENT 1L", "cantidad": 2, "unidad": "ud", "producto_id": producto_id}
            ]
        }
        try:
            with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
                resp = self._analizar()

            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
            item = resp.get_json()["items"][0]
            self.assertEqual(item["producto_id"], producto_id)
            self.assertEqual(item["nombre"], "Leche entera 1L")
            self.assertEqual(item["icono"], "🥛")
        finally:
            with self.app.app_context():
                db = get_db()
                db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
                db.commit()

    def test_sin_articulos_reconocidos_se_intenta_el_pipeline_local(self):
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            with patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto",
                       return_value=TEXTO_OCR) as extraer:
                resp = self._analizar()

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        extraer.assert_called_once()
        nombres = [item["nombre"] for item in resp.get_json()["items"]]
        self.assertIn("Leche Entera", nombres)

    def test_con_articulos_reconocidos_no_se_gasta_tesseract(self):
        _ClaudeFalso.respuesta = {
            "productos": [
                {"nombre_ticket": "Leche entera 1L", "cantidad": 2, "unidad": "ud", "producto_id": None}
            ]
        }
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            with patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto") as extraer:
                resp = self._analizar()

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        extraer.assert_not_called()
        items = resp.get_json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["cantidad"], 2)

    def test_si_ambos_motores_fallan_la_respuesta_sigue_siendo_valida(self):
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            with patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto",
                       side_effect=RuntimeError("tesseract no instalado")):
                resp = self._analizar()

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["items"], [])


if __name__ == "__main__":
    unittest.main()
