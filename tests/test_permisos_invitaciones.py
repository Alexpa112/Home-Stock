"""Tests de enlace compartible, aceptar invitación, actualizar y revocar
permisos. Cubre stockhogar/rutas/permisos.py, sin test previo."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class PermisosInvitacionesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.propietario_id, self.hogar_id, self.client_propietario = self._crear_usuario_con_lista("propietario")
        self.invitado_id, _, self.client_invitado = self._crear_usuario_con_lista("invitado")

    def _crear_usuario_con_lista(self, sufijo):
        nombre_usuario = f"test_{sufijo}_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                (f"Lista de {sufijo}", usuario_id, ahora(), ahora()),
            )
            hogar_id = cur.lastrowid
            db.commit()

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = hogar_id

        return usuario_id, hogar_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM invitaciones_hogar WHERE hogar_id = ?", (self.hogar_id,)
            )
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM hogares WHERE usuario_propietario_id IN (?, ?)",
                (self.propietario_id, self.invitado_id),
            )
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.propietario_id, self.invitado_id))
            db.commit()

    def test_generar_enlace_compartible_solo_propietario(self):
        resp = self.client_invitado.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

        resp = self.client_propietario.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertIn("codigo", resp.get_json())

    def test_aceptar_invitacion_da_acceso_y_la_invalida(self):
        resp = self.client_propietario.post(f"/api/hogares/{self.hogar_id}/enlace-compartible")
        codigo = resp.get_json()["codigo"]

        resp = self.client_invitado.post(f"/api/hogares/aceptar-invitacion/{codigo}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            permiso = db.execute(
                "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.invitado_id),
            ).fetchone()
        self.assertIsNotNone(permiso)

        resp_repetido = self.client_invitado.post(f"/api/hogares/aceptar-invitacion/{codigo}")
        self.assertEqual(resp_repetido.status_code, 400, resp_repetido.get_data(as_text=True))

    def test_actualizar_y_revocar_permiso(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'ver', ?)",
                (self.hogar_id, self.invitado_id, ahora()),
            )
            db.commit()

        resp = self.client_propietario.patch(
            f"/api/hogares/{self.hogar_id}/permisos/{self.invitado_id}", json={"nivel": "editar"}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            nivel = db.execute(
                "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.invitado_id),
            ).fetchone()["nivel"]
        self.assertEqual(nivel, "editar")

        resp = self.client_propietario.delete(f"/api/hogares/{self.hogar_id}/permisos/{self.invitado_id}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT 1 FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.invitado_id),
            ).fetchone()
        self.assertIsNone(fila)

    def test_no_se_puede_modificar_permiso_del_propietario(self):
        resp = self.client_propietario.patch(
            f"/api/hogares/{self.hogar_id}/permisos/{self.propietario_id}", json={"nivel": "ver"}
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
