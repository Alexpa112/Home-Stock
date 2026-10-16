"""Test de /api/auth/estado devolviendo usuario_id (ver docs/REDISENO_GASTOS.md,
Fase 0): el front de gastos necesita saber que usuario_id es "yo" para
distinguirlo en el balance, sin comparar por nombre."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class EstadoUsuarioIdTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.nombre_usuario = f"test_estado_uid_{uuid.uuid4().hex[:8]}"

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE nombre_usuario = ?", (self.nombre_usuario,))
            db.commit()

    def test_estado_sin_sesion_no_devuelve_usuario_id(self):
        client = self.app.test_client()
        estado = client.get("/api/auth/estado").get_json()
        self.assertIsNone(estado["usuario_id"])
        self.assertIsNone(estado["usuario"])

    def test_estado_con_sesion_devuelve_el_usuario_id_correcto(self):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = self.nombre_usuario
            sess["usuario_id"] = self.usuario_id

        estado = client.get("/api/auth/estado").get_json()
        self.assertEqual(estado["usuario_id"], self.usuario_id)
        self.assertEqual(estado["usuario"], self.nombre_usuario)


if __name__ == "__main__":
    unittest.main()
