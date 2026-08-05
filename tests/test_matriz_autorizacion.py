"""Matriz de autorizacion (S-15) sobre los endpoints de permisos.py ya
migrados a @requerir_hogar("propietario"): comprueba que anonimo, un usuario
sin relacion con el hogar, uno con nivel "ver", uno con nivel "editar" y el
propietario obtienen el codigo de estado esperado."""
import unittest
import uuid

import pytest
from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

ENDPOINTS_SOLO_PROPIETARIO = [
    ("GET", "/api/hogares/{hogar_id}/miembros"),
    ("POST", "/api/hogares/{hogar_id}/compartir"),
    ("POST", "/api/hogares/{hogar_id}/enlace-compartible"),
]


class MatrizAutorizacionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        sufijo = uuid.uuid4().hex[:8]

        with self.app.app_context():
            db = get_db()
            self.propietario_id = self._crear_usuario(db, f"prop_{sufijo}")
            self.usuario_ver_id = self._crear_usuario(db, f"ver_{sufijo}")
            self.usuario_editar_id = self._crear_usuario(db, f"editar_{sufijo}")
            self.usuario_ajeno_id = self._crear_usuario(db, f"ajeno_{sufijo}")

            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar matriz", self.propietario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'ver', ?)",
                (self.hogar_id, self.usuario_ver_id, ahora()),
            )
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.usuario_editar_id, ahora()),
            )
            db.commit()

    def _crear_usuario(self, db, nombre):
        cur = db.execute(
            "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
            (nombre, generate_password_hash("password123"), ahora()),
        )
        return cur.lastrowid

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM invitaciones_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM usuarios WHERE id IN (?, ?, ?, ?)",
                (self.propietario_id, self.usuario_ver_id, self.usuario_editar_id, self.usuario_ajeno_id),
            )
            db.commit()

    def _peticion(self, metodo, ruta, usuario_id=None, nombre_usuario=None):
        if usuario_id is not None:
            with self.client.session_transaction() as sess:
                sess["usuario"] = nombre_usuario or "x"
                sess["usuario_id"] = usuario_id
        else:
            with self.client.session_transaction() as sess:
                sess.clear()
        # /compartir exige email o nombre de usuario destino en el body; el
        # resto de endpoints de la matriz ignoran el body.
        cuerpo = {"email": "destino_matriz@example.com"} if "compartir" in ruta else {}
        return self.client.open(ruta, method=metodo, json=cuerpo)

    def test_matriz_endpoints_solo_propietario(self):
        for metodo, plantilla in ENDPOINTS_SOLO_PROPIETARIO:
            ruta = plantilla.format(hogar_id=self.hogar_id)
            with self.subTest(endpoint=f"{metodo} {ruta}", rol="anonimo"):
                resp = self._peticion(metodo, ruta, usuario_id=None)
                self.assertEqual(resp.status_code, 401)

            with self.subTest(endpoint=f"{metodo} {ruta}", rol="ajeno"):
                resp = self._peticion(metodo, ruta, usuario_id=self.usuario_ajeno_id)
                self.assertEqual(resp.status_code, 403)

            with self.subTest(endpoint=f"{metodo} {ruta}", rol="ver"):
                resp = self._peticion(metodo, ruta, usuario_id=self.usuario_ver_id)
                self.assertEqual(resp.status_code, 403)

            with self.subTest(endpoint=f"{metodo} {ruta}", rol="editar"):
                resp = self._peticion(metodo, ruta, usuario_id=self.usuario_editar_id)
                self.assertEqual(resp.status_code, 403)

            with self.subTest(endpoint=f"{metodo} {ruta}", rol="propietario"):
                resp = self._peticion(metodo, ruta, usuario_id=self.propietario_id)
                self.assertIn(resp.status_code, (200, 201))


if __name__ == "__main__":
    unittest.main()
