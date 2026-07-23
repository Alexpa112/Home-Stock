"""Tests de regresion para POST /api/listas/<id>/compartir.

Cubre dos bugs:
1. La busqueda de usuario destino por nombre no usaba COLLATE NOCASE,
   a diferencia de login/registro, asi que compartir con "Ana" fallaba si
   el usuario se registro como "ana".
2. Un fallo inesperado al compartir devolvia el texto crudo de la excepcion
   de Python al cliente en vez de un mensaje generico controlado.
"""
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class CompartirListaTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        self.nombre_propietario = f"test_prop_{uuid.uuid4().hex[:8]}"
        self.nombre_destino = f"Test_Destino_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_propietario, generate_password_hash("password123"), ahora()),
            )
            self.propietario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_destino, generate_password_hash("password123"), ahora()),
            )
            self.destino_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista de test", self.propietario_id, ahora(), ahora()),
            )
            self.lista_id = cur.lastrowid
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_propietario
            sess["usuario_id"] = self.propietario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM permisos_lista WHERE lista_id = ?", (self.lista_id,))
            db.execute("DELETE FROM invitaciones_lista WHERE lista_id = ?", (self.lista_id,))
            db.execute("DELETE FROM listas WHERE id = ?", (self.lista_id,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.propietario_id, self.destino_id))
            db.commit()

    def test_compartir_con_nombre_en_minusculas_encuentra_al_usuario(self):
        resp = self.client.post(
            f"/api/listas/{self.lista_id}/compartir",
            json={"usuario": self.nombre_destino.lower(), "nivel": "editar"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            permiso = db.execute(
                "SELECT nivel FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
                (self.lista_id, self.destino_id),
            ).fetchone()
            self.assertIsNotNone(permiso, "El usuario destino deberia tener permiso sobre la lista")
            self.assertEqual(permiso["nivel"], "editar")

    def test_compartir_con_nombre_en_mayusculas_encuentra_al_usuario(self):
        resp = self.client.post(
            f"/api/listas/{self.lista_id}/compartir",
            json={"usuario": self.nombre_destino.upper(), "nivel": "ver"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_fallo_inesperado_al_compartir_por_email_no_expone_texto_crudo(self):
        mensaje_interno_sensible = "boom: credenciales SMTP invalidas en servidor interno XYZ"
        with patch(
            "stockhogar.rutas.permisos.EmailService.enviar_invitacion_lista",
            side_effect=RuntimeError(mensaje_interno_sensible),
        ):
            resp = self.client.post(
                f"/api/listas/{self.lista_id}/compartir",
                json={"email": "destino@example.com", "nivel": "editar"},
            )

        self.assertEqual(resp.status_code, 500)
        cuerpo = resp.get_json()
        self.assertNotIn(mensaje_interno_sensible, cuerpo.get("error", ""))


if __name__ == "__main__":
    unittest.main()
