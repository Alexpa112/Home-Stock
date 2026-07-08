import unittest

from stockhogar import create_app
from stockhogar.db import get_db


class ProductosValidationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "test"

    def test_cantidad_igual_al_minimo_no_crea_entrada_auto_en_lista(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Leche",
                "categoria": "Lácteos",
                "cantidad": 2,
                "unidad": "ud",
                "stock_minimo": 2,
            },
        )

        self.assertEqual(resp.status_code, 201)
        producto = resp.get_json()
        db = get_db()
        pendiente = db.execute(
            "SELECT id FROM lista_compra WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
            (producto["id"],),
        ).fetchone()
        self.assertIsNone(pendiente)

    def test_cantidad_menor_al_minimo_crea_entrada_auto_en_lista(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Pan",
                "categoria": "Panadería y Bollería",
                "cantidad": 1,
                "unidad": "ud",
                "stock_minimo": 3,
            },
        )

        self.assertEqual(resp.status_code, 201)
        producto = resp.get_json()
        db = get_db()
        pendiente = db.execute(
            "SELECT id FROM lista_compra WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
            (producto["id"],),
        ).fetchone()
        self.assertIsNotNone(pendiente)

    def test_cantidad_negativa_es_rechazada(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Azúcar",
                "categoria": "Despensa",
                "cantidad": -1,
                "unidad": "kg",
                "stock_minimo": 1,
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("cantidad", resp.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()
