import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ProductosValidationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        # Estos tests corren contra la BD real persistente (config.py fija
        # DB_PATH a un fichero, no hay modo in-memory para tests). Se usa un
        # nombre de usuario único por ejecución para no chocar con datos de
        # una ejecución anterior, y se limpia todo en tearDown.
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
        self.otras_listas_creadas = []
        self.otros_usuarios_creados = []

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
            for lista_id in self.otras_listas_creadas:
                db.execute("DELETE FROM stock_lista WHERE lista_id = ?", (lista_id,))
                db.execute("DELETE FROM articulos_lista WHERE lista_id = ?", (lista_id,))
                db.execute("DELETE FROM listas WHERE id = ?", (lista_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            for otro_id in self.otros_usuarios_creados:
                db.execute("DELETE FROM usuarios WHERE id = ?", (otro_id,))
            db.commit()

    def test_cantidad_igual_al_minimo_crea_entrada_auto_en_lista(self):
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
        with self.app.app_context():
            db = get_db()
            pendiente = db.execute(
                "SELECT id FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
                (producto["id"],),
            ).fetchone()
        # cantidad <= stock_minimo dispara el aviso automático (igual O menor).
        self.assertIsNotNone(pendiente)

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
        with self.app.app_context():
            db = get_db()
            pendiente = db.execute(
                "SELECT id FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
                (producto["id"],),
            ).fetchone()
        self.assertIsNotNone(pendiente)

    def test_cantidad_por_encima_del_minimo_no_crea_entrada_auto(self):
        resp = self.client.post(
            "/api/productos",
            json={
                "nombre": "Arroz",
                "categoria": "Despensa",
                "cantidad": 5,
                "unidad": "kg",
                "stock_minimo": 1,
            },
        )

        self.assertEqual(resp.status_code, 201)
        producto = resp.get_json()
        with self.app.app_context():
            db = get_db()
            pendiente = db.execute(
                "SELECT id FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
                (producto["id"],),
            ).fetchone()
        self.assertIsNone(pendiente)

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

    def test_producto_solo_visible_en_su_propia_lista(self):
        """El stock creado en una lista no debe filtrarse a otra lista/usuario."""
        self.client.post(
            "/api/productos",
            json={"nombre": "Café", "categoria": "Bebidas", "cantidad": 3, "unidad": "ud", "stock_minimo": 1},
        )

        with self.app.app_context():
            db = get_db()
            otro_usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"otro_{uuid.uuid4().hex[:8]}", generate_password_hash("password123"), ahora()),
            ).lastrowid
            otra_lista_id = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Otra lista", otro_usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        self.otras_listas_creadas.append(otra_lista_id)
        self.otros_usuarios_creados = [otro_usuario_id]

        with self.client.session_transaction() as sess:
            sess["lista_actual_id"] = otra_lista_id

        resp = self.client.get("/api/productos")
        # Sin permiso sobre "otra_lista_id" (propietario distinto): no debe ver el stock.
        self.assertEqual(resp.get_json(), [])


if __name__ == "__main__":
    unittest.main()
