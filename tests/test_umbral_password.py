"""Test de regresion: el umbral minimo de contraseña debe ser 8 caracteres
en todos los endpoints, no solo en el registro.

Antes, registrar() exigia 8 caracteres pero actualizar_perfil y
cambiar_password solo exigian 4, debilitando la politica de contraseñas
justo despues del alta.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class UmbralPasswordTests(unittest.TestCase):
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

    def test_actualizar_perfil_rechaza_password_corta_de_menos_de_8(self):
        resp = self.client.put("/api/auth/perfil", json={"password": "abc1234"})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_actualizar_perfil_acepta_password_de_8_o_mas(self):
        resp = self.client.put("/api/auth/perfil", json={"password": "abc12345"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_cambiar_password_rechaza_nueva_password_corta_de_menos_de_8(self):
        resp = self.client.post(
            "/api/auth/cambiar-password",
            json={
                "password_actual": "password123",
                "password_nueva": "abc1234",
                "password_confirmacion": "abc1234",
            },
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_cambiar_password_acepta_nueva_password_de_8_o_mas(self):
        resp = self.client.post(
            "/api/auth/cambiar-password",
            json={
                "password_actual": "password123",
                "password_nueva": "abc12345",
                "password_confirmacion": "abc12345",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
