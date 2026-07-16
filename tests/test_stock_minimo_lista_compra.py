import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ReproBajadaStockTest(unittest.TestCase):
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
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista de test", usuario_id, ahora(), ahora()),
            )
            self.lista_id = cur.lastrowid
            db.commit()

        self.usuario_id = usuario_id
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["lista_actual_id"] = self.lista_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM stock_lista WHERE lista_id IN "
                "(SELECT id FROM listas WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute(
                "DELETE FROM articulos_lista WHERE lista_id IN "
                "(SELECT id FROM listas WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM listas WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_bajar_stock_con_delta_hasta_minimo_anade_a_lista(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Huevos",
                "categoria": "Lácteos",
                "cantidad": 5,
                "unidad": "ud",
                "stock_minimo": 2,
            },
        )
        self.assertEqual(resp.status_code, 201)
        producto = resp.get_json()
        producto_id = producto["id"]

        # Bajar de 5 a 2 (llega justo al minimo) via PATCH delta, como hace el boton "-"
        for _ in range(3):
            resp = self.client.patch(f"/api/productos/{producto_id}", json={"delta": -1})
            self.assertEqual(resp.status_code, 200, resp.get_json())

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT cantidad, stock_minimo FROM stock_lista WHERE producto_id = ? AND lista_id = ?",
                (producto_id, self.lista_id),
            ).fetchone()
            print("STOCK ACTUAL:", dict(fila))
            pendiente = db.execute(
                "SELECT * FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1 AND lista_id = ?",
                (producto_id, self.lista_id),
            ).fetchone()
            print("PENDIENTE:", dict(pendiente) if pendiente else None)

        self.assertIsNotNone(pendiente, "No se añadió a la lista de la compra al bajar al minimo")


class ReproEdicionCompletaTest(ReproBajadaStockTest):
    def test_editar_cantidad_directa_hasta_minimo_anade_a_lista(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Yogures",
                "categoria": "Lacteos",
                "cantidad": 5,
                "unidad": "ud",
                "stock_minimo": 2,
            },
        )
        self.assertEqual(resp.status_code, 201)
        producto = resp.get_json()
        producto_id = producto["id"]

        resp = self.client.patch(
            f"/api/productos/{producto_id}",
            json={
                "nombre": "Yogures",
                "categoria": "Lacteos",
                "cantidad": 2,
                "stock_minimo": 2,
                "unidad": "ud",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.get_json())

        with self.app.app_context():
            db = get_db()
            pendiente = db.execute(
                "SELECT * FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1 AND lista_id = ?",
                (producto_id, self.lista_id),
            ).fetchone()
            print("PENDIENTE EDICION:", dict(pendiente) if pendiente else None)

        self.assertIsNotNone(pendiente, "No se anadio a la lista de la compra al editar cantidad al minimo")


if __name__ == "__main__":
    unittest.main()
