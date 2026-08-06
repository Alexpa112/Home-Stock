"""Tests de regresion para POST /api/hogares/<id>/compartir.

Cubre:
1. La busqueda de usuario destino por nombre no usaba COLLATE NOCASE,
   a diferencia de login/registro, asi que compartir con "Ana" fallaba si
   el usuario se registro como "ana".
2. Un fallo inesperado al compartir devolvia el texto crudo de la excepcion
   de Python al cliente en vez de un mensaje generico controlado.
3. (S-10) Compartir por nombre de usuario crea una invitacion PENDIENTE en
   vez de dar acceso inmediato, y responde igual exista o no el usuario
   (sin permitir enumerarlos).
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
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista de test", self.propietario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_propietario
            sess["usuario_id"] = self.propietario_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM invitaciones_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.propietario_id, self.destino_id))
            db.commit()

    def test_compartir_con_nombre_en_minusculas_crea_invitacion_pendiente(self):
        resp = self.client.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"usuario": self.nombre_destino.lower(), "nivel": "editar"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            # Sin aceptar todavia: no debe haber permiso concedido.
            permiso = db.execute(
                "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.destino_id),
            ).fetchone()
            self.assertIsNone(permiso, "No deberia haber acceso hasta que el destino acepte la invitacion")

            invitacion = db.execute(
                "SELECT codigo_invitacion, nivel FROM invitaciones_hogar WHERE hogar_id = ? AND usuario_destino_id = ?",
                (self.hogar_id, self.destino_id),
            ).fetchone()
            self.assertIsNotNone(invitacion, "Deberia haberse creado una invitacion pendiente")
            self.assertEqual(invitacion["nivel"], "editar")

        # El destino acepta explicitamente: solo entonces obtiene el permiso.
        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_destino
            sess["usuario_id"] = self.destino_id
        resp_aceptar = self.client.post(f"/api/hogares/aceptar-invitacion/{invitacion['codigo_invitacion']}")
        self.assertEqual(resp_aceptar.status_code, 200, resp_aceptar.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            permiso = db.execute(
                "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
                (self.hogar_id, self.destino_id),
            ).fetchone()
            self.assertIsNotNone(permiso, "Tras aceptar, el destino deberia tener permiso sobre la lista")
            self.assertEqual(permiso["nivel"], "editar")

    def test_compartir_con_nombre_en_mayusculas_encuentra_al_usuario(self):
        resp = self.client.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"usuario": self.nombre_destino.upper(), "nivel": "ver"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_compartir_con_usuario_inexistente_responde_igual_que_con_uno_existente(self):
        """S-10: no debe poderse distinguir por la respuesta si el usuario existe."""
        resp_inexistente = self.client.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"usuario": f"no_existe_{uuid.uuid4().hex[:8]}", "nivel": "ver"},
        )
        resp_existente = self.client.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"usuario": self.nombre_destino, "nivel": "ver"},
        )
        self.assertEqual(resp_inexistente.status_code, resp_existente.status_code)
        self.assertEqual(resp_inexistente.get_json(), resp_existente.get_json())

    def test_compartir_respeta_limite_diario_de_invitaciones_por_hogar(self):
        """S-21: protege un hogar de ser usado para espamear invitaciones."""
        from stockhogar.config import LIMITE_INVITACIONES_DIARIO_POR_HOGAR

        with self.app.app_context():
            db = get_db()
            for i in range(LIMITE_INVITACIONES_DIARIO_POR_HOGAR):
                db.execute(
                    "INSERT INTO invitaciones_hogar (hogar_id, email_destino, nivel, codigo_invitacion, "
                    "fecha_creacion, fecha_expiracion) VALUES (?, ?, 'ver', ?, ?, ?)",
                    (self.hogar_id, f"relleno{i}@example.com", f"codigo-relleno-{i}-{uuid.uuid4().hex[:6]}", ahora(), ahora()),
                )
            db.commit()

        resp = self.client.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"email": "otro@example.com", "nivel": "ver"},
        )
        self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))

    def test_fallo_inesperado_al_compartir_por_email_no_expone_texto_crudo(self):
        mensaje_interno_sensible = "boom: credenciales SMTP invalidas en servidor interno XYZ"
        with patch(
            "stockhogar.rutas.permisos.EmailService.enviar_invitacion_lista",
            side_effect=RuntimeError(mensaje_interno_sensible),
        ):
            resp = self.client.post(
                f"/api/hogares/{self.hogar_id}/compartir",
                json={"email": "destino@example.com", "nivel": "editar"},
            )

        self.assertEqual(resp.status_code, 500)
        cuerpo = resp.get_json()
        self.assertNotIn(mensaje_interno_sensible, cuerpo.get("error", ""))


if __name__ == "__main__":
    unittest.main()
