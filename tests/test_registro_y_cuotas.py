"""Tests (S-05): interruptor de registro publico y cuotas basicas por usuario
(limite de hogares propios, limite diario de escaneos OCR).
"""
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class RegistroAbiertoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

    def test_registro_cerrado_devuelve_403(self):
        with patch("stockhogar.rutas.auth.REGISTRO_ABIERTO", False):
            resp = self.client.post(
                "/api/auth/registrar",
                json={
                    "usuario": f"test_{uuid.uuid4().hex[:8]}",
                    "password": "password123",
                    "acepta_terminos": True,
                },
            )
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))


class LimiteHogaresTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora()),
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

    def test_limite_hogares_por_usuario_se_respeta(self):
        with patch("stockhogar.rutas.hogares.LIMITE_HOGARES_POR_USUARIO", 2):
            for i in range(2):
                resp = self.client.post("/api/hogares", json={"nombre": f"Hogar {i}"})
                self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))

            resp = self.client.post("/api/hogares", json={"nombre": "Hogar de mas"})
            self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))


class LimiteOcrDiarioTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora()),
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
            db.execute("DELETE FROM uso_ocr_diario WHERE usuario_id = ?", (self.usuario_id,))
            db.commit()

    def _subir_ticket(self):
        from io import BytesIO
        return self.client.post(
            "/api/ocr/procesar-ticket",
            data={"archivo": (BytesIO(b"fake-image-bytes"), "ticket.png")},
            content_type="multipart/form-data",
        )

    def test_limite_diario_ocr_se_respeta(self):
        resultado_ok = {"exito": True, "confianza_ocr": 90, "texto_original": "", "productos": []}
        with patch("stockhogar.rutas.ocr_tickets.LIMITE_OCR_DIARIO", 2), \
             patch("stockhogar.rutas.ocr_tickets.gestor_ocr.procesar_ticket", return_value=resultado_ok):
            for _ in range(2):
                resp = self._subir_ticket()
                self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

            resp = self._subir_ticket()
            self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
