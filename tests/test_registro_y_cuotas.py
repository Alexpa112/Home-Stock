"""Tests (S-05): interruptor de registro publico y cuotas basicas por usuario
(limite de hogares propios, limite diario de escaneos OCR).
"""
import base64
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.servicios.ocr.claude_ocr import ClaudeOCR

# PNG 1x1 valido: /api/tickets/analizar valida el contenido real de la imagen
# (S-16), no solo la extension, asi que unos bytes cualesquiera no sirven.
_PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


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

        # La cuota es de "escanear un ticket", asi que hace falta un hogar
        # activo: /api/tickets/analizar exige permiso 'ver' (A-1).
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, ?, ?)",
                ("Hogar cuota", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()
        with self.client.session_transaction() as sess:
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.execute("DELETE FROM uso_ocr_diario WHERE usuario_id = ?", (self.usuario_id,))
            db.commit()

    def _subir_ticket(self):
        """Sube por /api/tickets/analizar, que es la ruta que usa el frontend.

        Antes este test atacaba /api/ocr/procesar-ticket, que nadie llamaba:
        pasaba en verde mientras la ruta real no tenia ninguna cuota (A-6).
        """
        from io import BytesIO
        return self.client.post(
            "/api/tickets/analizar",
            data={"foto": (BytesIO(_PNG_MINIMO), "ticket.png")},
            content_type="multipart/form-data",
        )

    def test_limite_diario_ocr_se_respeta(self):
        # Se simula que el motor de nube esta disponible y responde: es el
        # unico camino que consume cuota.
        with patch("stockhogar.rutas.tickets.LIMITE_OCR_DIARIO", 2), \
             patch.object(ClaudeOCR, "disponible", return_value=True), \
             patch.object(ClaudeOCR, "procesar", return_value={"productos": []}):
            for _ in range(2):
                resp = self._subir_ticket()
                self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

            resp = self._subir_ticket()
            self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))

    def test_el_pipeline_local_no_consume_cuota(self):
        """Tesseract es gratuito: solo el motor de nube gasta cuota."""
        with patch("stockhogar.rutas.tickets.LIMITE_OCR_DIARIO", 1), \
             patch.object(ClaudeOCR, "disponible", return_value=False), \
             patch("stockhogar.rutas.tickets.ticket_ocr.extraer_texto", return_value=""):
            for _ in range(3):
                resp = self._subir_ticket()
                self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_sin_permiso_sobre_el_hogar_no_se_puede_escanear(self):
        """Antes /api/tickets/analizar no comprobaba ningun permiso (A-1)."""
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"ajeno_{uuid.uuid4().hex[:8]}", generate_password_hash("password123"), ahora()),
            )
            ajeno_id = cur.lastrowid
            db.commit()
        try:
            with self.client.session_transaction() as sess:
                sess["usuario_id"] = ajeno_id
                # Apunta al hogar del otro usuario: no tiene ningun permiso.
                sess["hogar_actual_id"] = self.hogar_id
            resp = self._subir_ticket()
            self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))
        finally:
            with self.app.app_context():
                db = get_db()
                db.execute("DELETE FROM usuarios WHERE id = ?", (ajeno_id,))
                db.commit()


if __name__ == "__main__":
    unittest.main()
