"""
Test E2E: aislamiento de stock por lista.

Verifica que dos usuarios con sus propias hogares no comparten stock entre
si: el stock de un producto vive en stock_hogar, por lista, no en una tabla
global compartida. Usa el test client de Flask (in-process), igual que
test_productos.py, sin depender de un servidor real levantado aparte.
"""
import unittest
import uuid

from stockhogar import create_app
from stockhogar.db import get_db


class AislamientoStockTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.usuarios_creados = []
        self.listas_creadas = []
        self.productos_creados = []

    def _cliente_con_usuario_y_lista(self, prefijo):
        """Registra un usuario nuevo, inicia sesión y crea su lista activa."""
        client = self.app.test_client()
        usuario = f"{prefijo}_{uuid.uuid4().hex[:8]}"

        resp = client.post(
            "/api/auth/registrar",
            json={"usuario": usuario, "password": "TestPass123"},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())

        resp = client.post(
            "/api/hogares",
            json={"nombre": f"Lista de {usuario}"},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        hogar_id = resp.get_json()["id"]

        with self.app.app_context():
            db = get_db()
            usuario_id = db.execute(
                "SELECT id FROM usuarios WHERE nombre_usuario = ?", (usuario,)
            ).fetchone()["id"]
        self.usuarios_creados.append(usuario_id)
        self.listas_creadas.append(hogar_id)

        return client, usuario, hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for hogar_id in self.listas_creadas:
                db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (hogar_id,))
                db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (hogar_id,))
                db.execute("DELETE FROM hogares WHERE id = ?", (hogar_id,))
            for producto_id in self.productos_creados:
                db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
            for usuario_id in self.usuarios_creados:
                db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            db.commit()

    def test_stock_no_se_comparte_entre_usuarios(self):
        cliente1, usuario1, lista1_id = self._cliente_con_usuario_y_lista("e2e_uno")
        cliente2, usuario2, lista2_id = self._cliente_con_usuario_y_lista("e2e_dos")

        resp = cliente1.post(
            "/api/productos",
            json={"nombre": "Leche", "categoria": "Otros", "cantidad": 5, "stock_minimo": 1},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())
        self.productos_creados.append(resp.get_json()["id"])

        # El producto vive en la lista del usuario 1...
        productos_u1 = cliente1.get("/api/productos").get_json()
        self.assertEqual(len(productos_u1), 1)
        self.assertEqual(productos_u1[0]["nombre"], "Leche")

        # ...y no aparece en el stock del usuario 2, aunque ambos usuarios
        # compartan el mismo catalogo global de productos.
        productos_u2 = cliente2.get("/api/productos").get_json()
        self.assertEqual(productos_u2, [])

        with self.app.app_context():
            db = get_db()
            stock_lista1 = db.execute(
                "SELECT COUNT(*) AS n FROM stock_hogar WHERE hogar_id = ?", (lista1_id,)
            ).fetchone()["n"]
            stock_lista2 = db.execute(
                "SELECT COUNT(*) AS n FROM stock_hogar WHERE hogar_id = ?", (lista2_id,)
            ).fetchone()["n"]

        self.assertEqual(stock_lista1, 1)
        self.assertEqual(stock_lista2, 0)


if __name__ == "__main__":
    unittest.main()
