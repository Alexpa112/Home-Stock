"""Test de regresion: POST /api/tickets/confirmar exige permiso de 'editar'
en la lista activa.

Antes, sumar_stock()/crear_producto_nuevo() resolvian la lista activa de la
sesion (_resolver_lista_id_por_defecto) sin comprobar ningun permiso, a
diferencia de todos los endpoints de productos.py. Un usuario con acceso de
solo lectura ('ver') a una lista compartida podia subir una foto de ticket
y confirmarlo para crear productos/modificar stock de esa lista pese a no
tener permiso de edicion.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ConfirmarTicketPermisoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.propietario_id, self.lista_id, self.client_propietario = self._crear_usuario_con_lista("owner")
        self.lector_id, _, self.client_lector = self._crear_usuario_con_lista("viewer")

        with self.app.app_context():
            db = get_db()
            # El lector tiene acceso de solo lectura ('ver') a la lista del
            # propietario, y la tiene seleccionada como lista activa.
            db.execute(
                "INSERT INTO permisos_lista (lista_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'ver', ?)",
                (self.lista_id, self.lector_id, ahora()),
            )
            db.commit()

        with self.client_lector.session_transaction() as sess:
            sess["lista_actual_id"] = self.lista_id

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
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                (f"Lista de {sufijo}", usuario_id, ahora(), ahora()),
            )
            lista_id = cur.lastrowid
            db.commit()

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["lista_actual_id"] = lista_id

        return usuario_id, lista_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM productos WHERE nombre = 'ZzzTicketPermisoTest'"
            )
            db.execute("DELETE FROM permisos_lista WHERE lista_id = ?", (self.lista_id,))
            db.execute(
                "DELETE FROM listas WHERE usuario_propietario_id IN (?, ?)",
                (self.propietario_id, self.lector_id),
            )
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.propietario_id, self.lector_id))
            db.commit()

    def test_lector_de_solo_ver_no_puede_confirmar_ticket(self):
        resp = self.client_lector.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": "ZzzTicketPermisoTest", "cantidad": 2, "unidad": "ud"}]},
        )
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT id FROM productos WHERE nombre = 'ZzzTicketPermisoTest'"
            ).fetchone()
        self.assertIsNone(fila, "No debe haberse creado ningun producto")

    def test_propietario_si_puede_confirmar_ticket(self):
        resp = self.client_propietario.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": "ZzzTicketPermisoTest", "cantidad": 2, "unidad": "ud"}]},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json().get("creados"), 1)


if __name__ == "__main__":
    unittest.main()
