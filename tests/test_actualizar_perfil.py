"""Tests de regresion para PUT /api/auth/perfil.

Cubre dos cosas:

- El bug original: actualizar_perfil permitia cambiar nombre_usuario sin
  comprobar duplicados (a diferencia de registrar(), que si lo hace), lo que
  provocaba un 500 sin controlar por violacion de la UNIQUE de usuarios.
- Los hallazgos A-3 y A-3b de la auditoria 2026-08: el endpoint aceptaba un
  campo `password` y lo aplicaba SIN pedir la actual (mientras
  /api/auth/cambiar-password si la exige), asi que con una sesion robada se
  tomaba la cuenta de forma permanente; y no existia forma alguna de fijar el
  email, de modo que quien se registraba con usuario+contraseña no podia
  recuperarla nunca.
"""
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.servicios.email_service import EmailService


class ActualizarPerfilTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        self.nombre_a = f"test_a_{uuid.uuid4().hex[:8]}"
        self.nombre_b = f"test_b_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_a, generate_password_hash("password123"), ahora()),
            )
            self.usuario_a_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_b, generate_password_hash("password123"), ahora()),
            )
            self.usuario_b_id = cur.lastrowid
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_a
            sess["usuario_id"] = self.usuario_a_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_a_id, self.usuario_b_id))
            db.commit()

    def test_no_permite_cambiar_a_nombre_de_otro_usuario(self):
        resp = self.client.put("/api/auth/perfil", json={"usuario": self.nombre_b, "password_actual": "password123"})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
            self.assertEqual(fila["nombre_usuario"], self.nombre_a, "El nombre no debe haber cambiado")

    def test_no_permite_cambiar_a_nombre_de_otro_usuario_con_distintas_mayusculas(self):
        resp = self.client.put("/api/auth/perfil", json={"usuario": self.nombre_b.upper(), "password_actual": "password123"})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_permite_cambiar_a_un_nombre_libre(self):
        nuevo_nombre = f"{self.nombre_a}_nuevo"
        resp = self.client.put("/api/auth/perfil", json={"usuario": nuevo_nombre, "password_actual": "password123"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
            self.assertEqual(fila["nombre_usuario"], nuevo_nombre)

    def test_permite_conservar_el_propio_nombre(self):
        resp = self.client.put("/api/auth/perfil", json={"usuario": self.nombre_a, "password_actual": "password123"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_permite_cambiar_nombre_a_mostrar_sin_afectar_al_usuario_de_login(self):
        resp = self.client.put("/api/auth/perfil", json={"nombre": "Alejandro"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["nombre"], "Alejandro")

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT nombre_usuario, nombre FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
            self.assertEqual(fila["nombre_usuario"], self.nombre_a, "El usuario de login no debe cambiar")
            self.assertEqual(fila["nombre"], "Alejandro")

    def test_permite_repetir_nombre_a_mostrar_entre_usuarios(self):
        resp_a = self.client.put("/api/auth/perfil", json={"nombre": "Mismo Nombre"})
        self.assertEqual(resp_a.status_code, 200, resp_a.get_data(as_text=True))

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_b
            sess["usuario_id"] = self.usuario_b_id

        resp_b = self.client.put("/api/auth/perfil", json={"nombre": "Mismo Nombre"})
        self.assertEqual(resp_b.status_code, 200, resp_b.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()


class PerfilNoCambiaPasswordTests(ActualizarPerfilTests):
    """A-3: PUT /api/auth/perfil ya no cambia la contraseña."""

    def test_rechaza_el_campo_password(self):
        resp = self.client.put("/api/auth/perfil", json={"password": "otraPassword999"})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

        # Y la contraseña original sigue siendo valida.
        self.client.post("/api/auth/logout")
        resp = self.client.post(
            "/api/auth/login", json={"usuario": self.nombre_a, "password": "password123"}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_cambiar_el_login_exige_la_password_actual(self):
        resp = self.client.put(
            "/api/auth/perfil",
            json={"usuario": f"{self.nombre_a}_x", "password_actual": "incorrecta"},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))
        with self.app.app_context():
            fila = get_db().execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
        self.assertEqual(fila["nombre_usuario"], self.nombre_a)

    def test_el_nombre_a_mostrar_no_exige_reautenticacion(self):
        """Es un dato cosmetico, no sirve para recuperar la cuenta."""
        resp = self.client.put("/api/auth/perfil", json={"nombre": "Alias"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))


class PerfilFijarEmailTests(ActualizarPerfilTests):
    """A-3b: sin esto, una cuenta local no podia tener email NUNCA."""

    def test_permite_fijar_el_email_y_queda_sin_verificar(self):
        correo = f"{uuid.uuid4().hex[:8]}@ejemplo.com"
        with patch.object(EmailService, "enviar_verificacion_email", return_value=True) as enviado:
            resp = self.client.put(
                "/api/auth/perfil",
                json={"email": correo, "password_actual": "password123"},
            )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["email"], correo)
        self.assertFalse(resp.get_json()["email_verificado"])
        enviado.assert_called_once()

        with self.app.app_context():
            fila = get_db().execute(
                "SELECT email, email_verificado FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
        self.assertEqual(fila["email"], correo)
        self.assertEqual(fila["email_verificado"], 0)

    def test_exige_la_password_actual(self):
        resp = self.client.put(
            "/api/auth/perfil",
            json={"email": "x@ejemplo.com", "password_actual": "incorrecta"},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_rechaza_un_email_mal_formado(self):
        resp = self.client.put(
            "/api/auth/perfil",
            json={"email": "no-es-un-email", "password_actual": "password123"},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_no_permite_reutilizar_el_email_de_otra_cuenta(self):
        correo = f"{uuid.uuid4().hex[:8]}@ejemplo.com"
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE usuarios SET email = ? WHERE id = ?", (correo, self.usuario_b_id))
            db.commit()
        resp = self.client.put(
            "/api/auth/perfil",
            json={"email": correo, "password_actual": "password123"},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))
