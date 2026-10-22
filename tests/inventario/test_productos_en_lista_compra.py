"""GET /api/productos indica si cada producto ya esta en la lista de la compra.

La tarjeta de stock ofrecia "Añadir a la compra" aunque el stock minimo ya
hubiera anadido el producto solo; el frontend usa `en_lista_compra` para no
ofrecerlo (segunda ronda de pruebas, 2026-10-22).
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ProductosEnListaCompraTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
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
                ("Hogar de test", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for tabla in ("stock_hogar", "articulos_compra"):
                db.execute(f"DELETE FROM {tabla} WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear(self, nombre, cantidad, minimo):
        resp = self.client.post(
            "/api/productos",
            json={"nombre": nombre, "categoria": "Otros", "cantidad": cantidad, "unidad": "ud", "stock_minimo": minimo},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()["id"]

    def _listado(self):
        resp = self.client.get("/api/productos")
        self.assertEqual(resp.status_code, 200)
        return {p["nombre"]: p for p in resp.get_json()}

    def test_bajo_minimo_ya_esta_en_la_lista(self):
        self._crear("Leche", 1, 2)
        self.assertTrue(self._listado()["Leche"]["en_lista_compra"])

    def test_producto_con_stock_suficiente_no_esta_en_la_lista(self):
        self._crear("Arroz", 5, 1)
        self.assertFalse(self._listado()["Arroz"]["en_lista_compra"])

    def test_articulo_comprado_ya_no_cuenta_como_en_la_lista(self):
        self._crear("Pan", 1, 2)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE articulos_compra SET activo = 0 WHERE hogar_id = ? AND LOWER(nombre) = 'pan'",
                (self.hogar_id,),
            )
            db.commit()
        self.assertFalse(self._listado()["Pan"]["en_lista_compra"])

    def test_articulo_manual_con_el_mismo_nombre_cuenta(self):
        self._crear("Sal", 5, 1)
        resp = self.client.post("/api/articulos", json={"nombre": "sal", "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_json())
        self.assertTrue(self._listado()["Sal"]["en_lista_compra"])


if __name__ == "__main__":
    unittest.main()
