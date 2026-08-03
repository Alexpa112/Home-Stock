"""Tests de GET /api/hogares/version: marca de version barata usada por el
polling silencioso del cliente (ver lib/usePollingRefresh.ts) para saber si
hay que recargar datos completos. Cubre stockhogar/rutas/hogares.py."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class VersionHogarTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"

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
                ("Lista inicial", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM articulos_compra WHERE hogar_id IN "
                "(SELECT id FROM hogares WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM permisos_hogar WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_version_cambia_al_anadir_articulo(self):
        resp = self.client.get("/api/hogares/version")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        version_inicial = resp.get_json()["version"]

        resp = self.client.post("/api/articulos", json={"nombre": "Leche"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))

        resp = self.client.get("/api/hogares/version")
        version_tras_anadir = resp.get_json()["version"]
        self.assertNotEqual(version_inicial, version_tras_anadir)

    def test_version_no_cambia_sin_modificaciones(self):
        resp1 = self.client.get("/api/hogares/version")
        resp2 = self.client.get("/api/hogares/version")
        self.assertEqual(resp1.get_json()["version"], resp2.get_json()["version"])

    def test_version_requiere_sesion(self):
        with self.app.test_client() as client_anonimo:
            resp = client_anonimo.get("/api/hogares/version")
            self.assertEqual(resp.status_code, 401)

    def test_version_sin_hogar_activo_devuelve_none(self):
        with self.client.session_transaction() as sess:
            sess.pop("hogar_actual_id", None)
        resp = self.client.get("/api/hogares/version")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsNone(data["hogar_id"])
        self.assertIsNone(data["version"])


if __name__ == "__main__":
    unittest.main()
