"""Matriz de autorizacion (S-15) sobre los endpoints ya migrados a
@requerir_hogar (permisos.py y hogares.py): comprueba que anonimo, un
usuario sin relacion con el hogar, uno con nivel "ver", uno con nivel
"editar" y el propietario obtienen el codigo de estado esperado."""
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
    ("PUT", "/api/hogares/{hogar_id}"),
]

ENDPOINTS_VER_O_SUPERIOR = [
    ("GET", "/api/hogares/{hogar_id}"),
    ("POST", "/api/hogares/{hogar_id}/seleccionar"),
    ("GET", "/api/hogares/{hogar_id}/miembros-basico"),
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
        # /compartir exige email o nombre de usuario destino en el body; PUT
        # sobre un hogar exige al menos un campo a actualizar; el resto de
        # endpoints de la matriz ignoran el body.
        if "compartir" in ruta:
            cuerpo = {"email": "destino_matriz@example.com"}
        elif metodo == "PUT":
            cuerpo = {"nombre": "Hogar matriz renombrado"}
        else:
            cuerpo = {}
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

    def test_matriz_endpoints_ver_o_superior(self):
        for metodo, plantilla in ENDPOINTS_VER_O_SUPERIOR:
            ruta = plantilla.format(hogar_id=self.hogar_id)
            with self.subTest(endpoint=f"{metodo} {ruta}", rol="anonimo"):
                resp = self._peticion(metodo, ruta, usuario_id=None)
                self.assertEqual(resp.status_code, 401)

            with self.subTest(endpoint=f"{metodo} {ruta}", rol="ajeno"):
                resp = self._peticion(metodo, ruta, usuario_id=self.usuario_ajeno_id)
                self.assertEqual(resp.status_code, 403)

            for rol, uid in (("ver", self.usuario_ver_id), ("editar", self.usuario_editar_id), ("propietario", self.propietario_id)):
                with self.subTest(endpoint=f"{metodo} {ruta}", rol=rol):
                    resp = self._peticion(metodo, ruta, usuario_id=uid)
                    self.assertIn(resp.status_code, (200, 201))

    def test_eliminar_hogar_solo_propietario(self):
        """DELETE es destructivo: se prueba sobre un hogar propio para no
        afectar al self.hogar_id compartido por el resto de la matriz."""
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar a borrar', ?, 1, ?, ?)",
                (self.propietario_id, ahora(), ahora()),
            )
            hogar_a_borrar_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'editar', ?)",
                (hogar_a_borrar_id, self.usuario_editar_id, ahora()),
            )
            db.commit()

        ruta = f"/api/hogares/{hogar_a_borrar_id}"
        self.assertEqual(self._peticion("DELETE", ruta, usuario_id=None).status_code, 401)
        self.assertEqual(self._peticion("DELETE", ruta, usuario_id=self.usuario_ajeno_id).status_code, 403)
        self.assertEqual(self._peticion("DELETE", ruta, usuario_id=self.usuario_editar_id).status_code, 403)
        self.assertEqual(self._peticion("DELETE", ruta, usuario_id=self.propietario_id).status_code, 200)

    def test_hogar_inexistente_devuelve_404_no_403(self):
        """Los endpoints de hogares.py migrados distinguen 404 (hogar
        inexistente) de 403 (existe pero sin permiso), a diferencia de
        permisos.py, que no necesitaba esa distincion antes de migrar."""
        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT MAX(id) AS m FROM hogares").fetchone()
            id_inexistente = (fila["m"] or 0) + 9999

        resp = self._peticion("GET", f"/api/hogares/{id_inexistente}", usuario_id=self.propietario_id)
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
