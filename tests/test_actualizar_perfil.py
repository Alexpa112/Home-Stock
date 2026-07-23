"""Tests de regresion para PUT /api/auth/perfil.

Cubre el bug donde actualizar_perfil permitia cambiar nombre_usuario sin
comprobar duplicados (a diferencia de registrar(), que si lo hace), lo que
provocaba un 500 sin controlar por violacion de la UNIQUE de la tabla
usuarios en vez de un error de validacion claro.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


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
        resp = self.client.put("/api/auth/perfil", json={"nombre": self.nombre_b})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
            self.assertEqual(fila["nombre_usuario"], self.nombre_a, "El nombre no debe haber cambiado")

    def test_no_permite_cambiar_a_nombre_de_otro_usuario_con_distintas_mayusculas(self):
        resp = self.client.put("/api/auth/perfil", json={"nombre": self.nombre_b.upper()})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_permite_cambiar_a_un_nombre_libre(self):
        nuevo_nombre = f"{self.nombre_a}_nuevo"
        resp = self.client.put("/api/auth/perfil", json={"nombre": nuevo_nombre})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?", (self.usuario_a_id,)
            ).fetchone()
            self.assertEqual(fila["nombre_usuario"], nuevo_nombre)

    def test_permite_conservar_el_propio_nombre(self):
        resp = self.client.put("/api/auth/perfil", json={"nombre": self.nombre_a})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
