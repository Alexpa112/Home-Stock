"""Test de regresion: POST /api/tickets/analizar manda el PDF entero a Claude
en vez de rasterizar solo su primera pagina.

_convertir_pdf_a_imagen usa `pdftoppm -singlefile`, que saca unicamente la
primera pagina. Como la conversion se hacia siempre antes de elegir motor, en
una factura de varias hojas se perdian todos los articulos de la segunda en
adelante. Ahora el PDF llega tal cual al motor de vision (que lee todas las
paginas) y solo se rasteriza si hay que recurrir a Tesseract.
"""
import io
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

PDF_MINIMO = b"%PDF-1.4\n% factura de prueba\n" + b"0" * 200


class _ClaudeFalso:
    """Motor de vision de mentira que registra con que se le llama."""

    disponible_valor = True
    llamadas = []

    def disponible(self):
        return type(self).disponible_valor

    def procesar(self, imagen_bytes, productos_catalogo, mime=None):
        type(self).llamadas.append({"bytes": imagen_bytes, "mime": mime})
        # Devuelve un articulo a proposito: con la lista vacia el flujo
        # reintentaria con el pipeline local (ver test_analizar_ticket_fallback)
        # y el PDF si acabaria rasterizado, que es justo lo que estos tests
        # quieren descartar.
        return {"productos": [
            {"nombre_ticket": "LECHE ENTERA 1L", "cantidad": 1, "unidad": "ud", "producto_id": None}
        ]}


class AnalizarTicketPdfTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_pdf_{uuid.uuid4().hex[:8]}"
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
                ("Lista PDF", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

        _ClaudeFalso.llamadas = []
        _ClaudeFalso.disponible_valor = True

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _subir(self, datos, nombre):
        return self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(datos), nombre)},
            content_type="multipart/form-data",
        )

    def test_pdf_llega_entero_al_motor_de_vision_sin_rasterizar(self):
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            with patch("stockhogar.rutas.tickets._convertir_pdf_a_imagen") as convertir:
                resp = self._subir(PDF_MINIMO, "factura.pdf")

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        convertir.assert_not_called()
        self.assertEqual(len(_ClaudeFalso.llamadas), 1)
        llamada = _ClaudeFalso.llamadas[0]
        self.assertEqual(llamada["mime"], "application/pdf")
        self.assertTrue(llamada["bytes"].startswith(b"%PDF-"))

    def test_imagen_normal_no_declara_mime_de_pdf(self):
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (300, 500), (255, 255, 255)).save(buffer, format="JPEG")

        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            resp = self._subir(buffer.getvalue(), "ticket.jpg")

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertIsNone(_ClaudeFalso.llamadas[0]["mime"])

    def test_sin_motor_de_vision_el_pdf_si_se_rasteriza_para_tesseract(self):
        _ClaudeFalso.disponible_valor = False
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            with patch("stockhogar.rutas.tickets._convertir_pdf_a_imagen", return_value=None) as convertir:
                resp = self._subir(PDF_MINIMO, "factura.pdf")

        convertir.assert_called_once()
        self.assertEqual(resp.status_code, 500)

    def test_fichero_que_no_es_pdf_pero_se_llama_pdf_se_rechaza(self):
        """Sin la conversion previa hay que validar la firma a mano (S-16)."""
        with patch("stockhogar.rutas.tickets.ClaudeOCR", _ClaudeFalso):
            resp = self._subir(b"esto no es un pdf en absoluto", "falso.pdf")

        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))
        self.assertEqual(_ClaudeFalso.llamadas, [])


if __name__ == "__main__":
    unittest.main()
