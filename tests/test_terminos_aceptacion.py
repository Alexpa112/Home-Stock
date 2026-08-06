"""Tests de la aceptacion de Terminos y Condiciones / Politica de Privacidad.

Cubre: el registro manual exige la casilla de aceptacion, /api/auth/estado
marca terminos_pendientes cuando la version guardada no coincide con la
vigente (usuarios antiguos u OAuth), el endpoint de aceptacion actualiza esa
version, y la configuracion legal publica es accesible sin sesion.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.config import DOMINIO_PUBLICO, EMAIL_CONTACTO_LEGAL, TITULAR_LEGAL, VERSION_TERMINOS
from stockhogar.db import ahora, get_db


class RegistroExigeAceptarTerminosTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE nombre_usuario = ?", (self.nombre_usuario,))
            db.commit()

    def test_registro_sin_aceptar_terminos_falla(self):
        resp = self.client.post(
            "/api/auth/registrar",
            json={"usuario": self.nombre_usuario, "password": "password123"},
        )
        self.assertEqual(resp.status_code, 400)

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT id FROM usuarios WHERE nombre_usuario = ?", (self.nombre_usuario,)
            ).fetchone()
            self.assertIsNone(fila)

    def test_registro_aceptando_terminos_guarda_version_y_fecha(self):
        resp = self.client.post(
            "/api/auth/registrar",
            json={"usuario": self.nombre_usuario, "password": "password123", "acepta_terminos": True},
        )
        self.assertEqual(resp.status_code, 201)

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT terminos_version_aceptada, terminos_fecha_aceptacion FROM usuarios WHERE nombre_usuario = ?",
                (self.nombre_usuario,),
            ).fetchone()
            self.assertEqual(fila["terminos_version_aceptada"], VERSION_TERMINOS)
            self.assertIsNotNone(fila["terminos_fecha_aceptacion"])

        estado = self.client.get("/api/auth/estado").get_json()
        self.assertFalse(estado["terminos_pendientes"])


class EstadoYAceptacionTerminosTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, terminos_version_aceptada) "
                "VALUES (?, ?, ?, ?)",
                (self.nombre_usuario, generate_password_hash("password123"), ahora(), "2020-01-01-version-vieja"),
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

    def test_estado_marca_pendiente_si_la_version_no_coincide(self):
        estado = self.client.get("/api/auth/estado").get_json()
        self.assertTrue(estado["terminos_pendientes"])

    def test_aceptar_terminos_actualiza_version_y_desmarca_pendiente(self):
        resp = self.client.post("/api/auth/aceptar-terminos")
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT terminos_version_aceptada FROM usuarios WHERE id = ?", (self.usuario_id,)
            ).fetchone()
            self.assertEqual(fila["terminos_version_aceptada"], VERSION_TERMINOS)

        estado = self.client.get("/api/auth/estado").get_json()
        self.assertFalse(estado["terminos_pendientes"])

    def test_aceptar_terminos_sin_sesion_da_401(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        resp = self.client.post("/api/auth/aceptar-terminos")
        self.assertEqual(resp.status_code, 401)


class ConfiguracionLegalPublicaTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

    def test_config_legal_accesible_sin_sesion(self):
        resp = self.client.get("/api/legal/config")
        self.assertEqual(resp.status_code, 200)
        datos = resp.get_json()
        self.assertEqual(datos["titular"], TITULAR_LEGAL)
        self.assertEqual(datos["email_contacto"], EMAIL_CONTACTO_LEGAL)
        self.assertEqual(datos["dominio"], DOMINIO_PUBLICO)
        self.assertEqual(datos["version_terminos"], VERSION_TERMINOS)


if __name__ == "__main__":
    unittest.main()
