"""Tests de verificacion de email y restablecimiento de contraseña (S-07).

Cubre: un token de verificacion marca email_verificado; un token caducado o
ya usado se rechaza; solicitar-reset-password responde igual exista o no la
cuenta (anti-enumeracion); un token de reset valido cambia la contraseña e
invalida sesiones abiertas (S-08).
"""
import time
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.rutas.auth import _hash_token


class VerificacionEmailTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, email) VALUES (?, ?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123456"), ahora(), "destino@example.com"),
            )
            self.usuario_id = cur.lastrowid
            db.commit()
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM tokens_verificacion WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear_token(self, tipo, expira_en_segundos=3600, usado=0):
        token = uuid.uuid4().hex
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira, usado) VALUES (?, ?, ?, ?, ?)",
                (self.usuario_id, tipo, _hash_token(token), int(time.time()) + expira_en_segundos, usado),
            )
            db.commit()
        return token

    @patch("stockhogar.rutas.auth.EmailService.enviar_verificacion_email", return_value=True)
    def test_enviar_verificacion_email_crea_token(self, _mock_email):
        resp = self.client.post("/api/auth/enviar-verificacion-email")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT COUNT(*) AS n FROM tokens_verificacion WHERE usuario_id = ? AND tipo = 'verificar_email'",
                (self.usuario_id,),
            ).fetchone()
            self.assertEqual(fila["n"], 1)

    def test_verificar_email_con_token_valido_marca_email_verificado(self):
        token = self._crear_token("verificar_email")
        resp = self.client.get(f"/api/auth/verificar-email/{token}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT email_verificado FROM usuarios WHERE id = ?", (self.usuario_id,)).fetchone()
            self.assertEqual(fila["email_verificado"], 1)

    def test_verificar_email_con_token_caducado_se_rechaza(self):
        token = self._crear_token("verificar_email", expira_en_segundos=-10)
        resp = self.client.get(f"/api/auth/verificar-email/{token}")
        self.assertEqual(resp.status_code, 400)
        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT email_verificado FROM usuarios WHERE id = ?", (self.usuario_id,)).fetchone()
            self.assertEqual(fila["email_verificado"], 0)

    def test_verificar_email_con_token_ya_usado_se_rechaza(self):
        token = self._crear_token("verificar_email", usado=1)
        resp = self.client.get(f"/api/auth/verificar-email/{token}")
        self.assertEqual(resp.status_code, 400)

    def test_verificar_email_con_token_invalido_se_rechaza(self):
        resp = self.client.get("/api/auth/verificar-email/token-que-no-existe")
        self.assertEqual(resp.status_code, 400)


class ResetPasswordTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, email, email_verificado) "
                "VALUES (?, ?, ?, ?, 1)",
                (self.nombre_usuario, generate_password_hash("password123456"), ahora(), "reset@example.com"),
            )
            self.usuario_id = cur.lastrowid
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM tokens_verificacion WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    @patch("stockhogar.rutas.auth.EmailService.enviar_recuperacion_password", return_value=True)
    def test_solicitar_reset_responde_igual_exista_o_no_la_cuenta(self, _mock_email):
        resp_existente = self.client.post(
            "/api/auth/solicitar-reset-password", json={"usuario_o_email": self.nombre_usuario}
        )
        resp_inexistente = self.client.post(
            "/api/auth/solicitar-reset-password", json={"usuario_o_email": f"no_existe_{uuid.uuid4().hex[:8]}"}
        )
        self.assertEqual(resp_existente.status_code, resp_inexistente.status_code)
        self.assertEqual(resp_existente.get_json(), resp_inexistente.get_json())

    @patch("stockhogar.rutas.auth.EmailService.enviar_recuperacion_password", return_value=True)
    def test_restablecer_password_con_token_valido_cambia_hash_e_invalida_sesiones(self, _mock_email):
        self.client.post("/api/auth/solicitar-reset-password", json={"usuario_o_email": self.nombre_usuario})
        with self.app.app_context():
            db = get_db()
            token_hash = db.execute(
                "SELECT token_hash FROM tokens_verificacion WHERE usuario_id = ? AND tipo = 'reset_password'",
                (self.usuario_id,),
            ).fetchone()["token_hash"]

        # No conocemos el token en claro (solo se guarda el hash) - lo
        # regeneramos con un token nuevo insertado directamente, mismo patron
        # que el resto de tests de este fichero.
        token = uuid.uuid4().hex
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM tokens_verificacion WHERE usuario_id = ?", (self.usuario_id,))
            db.execute(
                "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira) VALUES (?, 'reset_password', ?, ?)",
                (self.usuario_id, _hash_token(token), int(time.time()) + 3600),
            )
            db.commit()

        # Sesion abierta ANTES de restablecer, con la session_version actual.
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["session_version"] = 0

        resp = self.client.post(
            "/api/auth/restablecer-password", json={"token": token, "password_nueva": "otraPassword123"}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT password_hash, session_version FROM usuarios WHERE id = ?", (self.usuario_id,)).fetchone()
            self.assertTrue(check_password_hash(fila["password_hash"], "otraPassword123"))
            self.assertGreater(fila["session_version"], 0)

        # La sesion vieja (session_version=0) ya no es valida.
        resp_perfil = self.client.put("/api/auth/perfil", json={"nombre": "x"})
        self.assertEqual(resp_perfil.status_code, 401)

    def test_restablecer_password_con_token_invalido_se_rechaza(self):
        resp = self.client.post(
            "/api/auth/restablecer-password", json={"token": "no-existe", "password_nueva": "otraPassword123"}
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
