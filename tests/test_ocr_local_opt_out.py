"""Test de opt-out del OCR en la nube (S-26): con usuario_ocr_local=1,
/api/tickets/analizar no debe llamar a Claude, aunque haya ANTHROPIC_API_KEY
configurada y el motor este disponible.
"""
import io
import unittest
import uuid
from unittest.mock import patch

from PIL import Image
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


def _jpeg_de_prueba() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="white").save(buffer, format="JPEG")
    return buffer.getvalue()


class OptOutOcrLocalTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123456"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            db.commit()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    @patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto", return_value="")
    @patch("stockhogar.rutas.tickets.ClaudeOCR.procesar")
    @patch("stockhogar.rutas.tickets.ClaudeOCR.disponible", return_value=True)
    def test_con_ocr_local_activo_no_llama_a_claude(self, _mock_disponible, mock_procesar, _mock_extraer):
        resp_pref = self.client.post("/api/auth/preferencia-ocr", json={"ocr_local": True})
        self.assertEqual(resp_pref.status_code, 200, resp_pref.get_data(as_text=True))

        resp = self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(_jpeg_de_prueba()), "ticket.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        mock_procesar.assert_not_called()

    @patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto", return_value="")
    def test_sin_claude_usa_tesseract_como_fallback(self, _mock_extraer):
        """Sin ANTHROPIC_API_KEY configurada: OCR usa Tesseract como fallback."""
        resp = self.client.post(
            "/api/tickets/analizar",
            data={"foto": (io.BytesIO(_jpeg_de_prueba()), "ticket.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        # Tesseract se llama, aunque la imagen vacía devuelve 0 items
        _mock_extraer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
