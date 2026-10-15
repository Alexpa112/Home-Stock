"""Tests de /api/idiomas/traducir con entradas hostiles."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class TraducirTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.nombre = "idi_" + uuid.uuid4().hex[:6]
        with self.app.app_context():
            db = get_db()
            self.uid = db.execute(
                "INSERT INTO usuarios (nombre_usuario,password_hash,fecha_creacion) VALUES (?,?,?)",
                (self.nombre, generate_password_hash("password123"), ahora())).lastrowid
            db.commit()
        self.c = self.app.test_client()
        with self.c.session_transaction() as s:
            s["usuario"] = self.nombre
            s["usuario_id"] = self.uid

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE id=?", (self.uid,))
            db.commit()

    def test_claves_no_texto_se_ignoran(self):
        r = self.c.post("/api/idiomas/traducir", json={"idioma": "fr", "claves": [[1], {"a": 1}, None, 5, "guardar"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.get_json()["traducciones"]), ["guardar"])

    def test_lista_demasiado_larga(self):
        r = self.c.post("/api/idiomas/traducir", json={"claves": ["a"] * 2001})
        self.assertEqual(r.status_code, 400)

    def test_claves_no_lista(self):
        r = self.c.post("/api/idiomas/traducir", json={"claves": "x"})
        self.assertEqual(r.status_code, 400)

    def test_sin_sesion(self):
        r = self.app.test_client().post("/api/idiomas/traducir", json={"claves": ["a"]})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
