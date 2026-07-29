"""Tests de CRUD de listas: crear, obtener, actualizar, seleccionar, salir,
eliminar. Cubre stockhogar/rutas/listas.py, sin test previo."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class GestionListasTests(unittest.TestCase):
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
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista inicial", self.usuario_id, ahora(), ahora()),
            )
            self.lista_inicial_id = cur.lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["lista_actual_id"] = self.lista_inicial_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM articulos_lista WHERE lista_id IN "
                "(SELECT id FROM listas WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM permisos_lista WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM listas WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_crear_lista_la_marca_como_actual(self):
        resp = self.client.post("/api/listas", json={"nombre": "Nueva lista"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        nueva_id = resp.get_json()["id"]

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["lista_actual_id"], nueva_id)

    def test_obtener_lista_requiere_acceso(self):
        resp = self.client.get(f"/api/listas/{self.lista_inicial_id}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        otro_client = self.app.test_client()
        resp_otro = otro_client.get(f"/api/listas/{self.lista_inicial_id}")
        self.assertEqual(resp_otro.status_code, 401)

    def test_actualizar_lista_solo_propietario(self):
        resp = self.client.patch(f"/api/listas/{self.lista_inicial_id}", json={"nombre": "Renombrada"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["nombre"], "Renombrada")

    def test_seleccionar_lista_cambia_sesion(self):
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Segunda lista", self.usuario_id, ahora(), ahora()),
            )
            segunda_id = cur.lastrowid
            db.commit()

        resp = self.client.post(f"/api/listas/{segunda_id}/seleccionar")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["lista_actual_id"], segunda_id)

    def test_salir_de_lista_propia_esta_prohibido(self):
        resp = self.client.post(f"/api/listas/{self.lista_inicial_id}/salir")
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_eliminar_lista_solo_propietario(self):
        resp = self.client.delete(f"/api/listas/{self.lista_inicial_id}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT id FROM listas WHERE id = ?", (self.lista_inicial_id,)).fetchone()
        self.assertIsNone(fila)


if __name__ == "__main__":
    unittest.main()
