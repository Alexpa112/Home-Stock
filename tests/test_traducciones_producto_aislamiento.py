"""Test de regresion: GET /api/productos/<id>/traducciones/<idioma> no debe
filtrar traducciones de productos de listas ajenas.

Antes, el endpoint solo comprobaba que el producto existiera (SELECT * FROM
productos WHERE id = ?), sin verificar que perteneciera a una lista
accesible por el usuario: cualquier usuario autenticado podia leer
traducciones de cualquier producto de la instalacion iterando IDs.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class TraduccionesProductoAislamientoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.usuario_a_id, self.lista_a_id, self.client_a = self._crear_usuario_con_lista("a")
        self.usuario_b_id, self.lista_b_id, self.client_b = self._crear_usuario_con_lista("b")

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, unidad, dias_aviso, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, 'Otros', 'ud', 30, ?, ?)",
                ("ZzzProductoAislamientoTest", ahora(), ahora()),
            )
            self.producto_id = cur.lastrowid
            db.execute(
                "INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, 1, ?, ?)",
                (self.lista_a_id, self.producto_id, ahora(), ahora()),
            )
            db.execute(
                """INSERT INTO traducciones_productos
                   (producto_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                   VALUES (?, 'nombre', 'en', 'ZzzProductoAislamientoTest', 'ZzzTestProductIsolation', ?)""",
                (self.producto_id, ahora()),
            )
            db.commit()

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
            db.execute("DELETE FROM traducciones_productos WHERE producto_id = ?", (self.producto_id,))
            db.execute("DELETE FROM stock_lista WHERE producto_id = ?", (self.producto_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM listas WHERE id IN (?, ?)", (self.lista_a_id, self.lista_b_id))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_a_id, self.usuario_b_id))
            db.commit()

    def test_dueno_de_la_lista_puede_leer_las_traducciones(self):
        resp = self.client_a.get(f"/api/productos/{self.producto_id}/traducciones/en")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json().get("nombre"), "ZzzTestProductIsolation")

    def test_usuario_sin_acceso_no_puede_leer_las_traducciones(self):
        resp = self.client_b.get(f"/api/productos/{self.producto_id}/traducciones/en")
        self.assertIn(resp.status_code, (403, 404), resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
