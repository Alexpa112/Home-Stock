"""Tests de GET /api/consumo/resumen (P-11): agrega el consumo (bajadas de
stock) por dia y por producto en la lista activa, usado por el grafico de
evolucion en app/dashboard/historial/page.tsx."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ResumenConsumoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_consumo_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar consumo', ?, 1, ?, ?)",
                (self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES ('ZzzArrozConsumoTest', 'Otros', 5, 'ud', 1, ?, ?) RETURNING id",
                (ahora(), ahora()),
            )
            self.producto_id = cur.fetchone()["id"]
            db.execute(
                "INSERT INTO stock_hogar (hogar_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 5, 1, ?, ?)",
                (self.hogar_id, self.producto_id, ahora(), ahora()),
            )
            # Dos bajadas de stock (consumo) y una subida (reposicion, no cuenta).
            db.execute(
                "INSERT INTO movimientos_stock (producto_id, hogar_id, usuario_id, delta, cantidad_resultante, origen, fecha) "
                "VALUES (?, ?, ?, -2, 3, 'ajuste', ?)",
                (self.producto_id, self.hogar_id, self.usuario_id, ahora()),
            )
            db.execute(
                "INSERT INTO movimientos_stock (producto_id, hogar_id, usuario_id, delta, cantidad_resultante, origen, fecha) "
                "VALUES (?, ?, ?, -1, 2, 'ajuste', ?)",
                (self.producto_id, self.hogar_id, self.usuario_id, ahora()),
            )
            db.execute(
                "INSERT INTO movimientos_stock (producto_id, hogar_id, usuario_id, delta, cantidad_resultante, origen, fecha) "
                "VALUES (?, ?, ?, 10, 12, 'reposicion', ?)",
                (self.producto_id, self.hogar_id, self.usuario_id, ahora()),
            )
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM movimientos_stock WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_resumen_agrega_solo_bajadas_por_producto(self):
        resp = self.client.get("/api/consumo/resumen?dias=30")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(len(datos["por_producto"]), 1)
        self.assertEqual(datos["por_producto"][0]["nombre"], "ZzzArrozConsumoTest")
        self.assertEqual(datos["por_producto"][0]["consumo"], 3)

    def test_resumen_agrupa_por_dia(self):
        resp = self.client.get("/api/consumo/resumen?dias=30")
        datos = resp.get_json()
        self.assertEqual(len(datos["dias"]), 1)
        self.assertEqual(datos["dias"][0]["consumo"], 3)

    def test_sin_hogar_activo_devuelve_vacio(self):
        nombre_ajeno = f"test_consumo_ajeno_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_ajeno, generate_password_hash("password123"), ahora()),
            )
            usuario_ajeno_id = cur.lastrowid
            db.commit()
        try:
            client_sin_hogar = self.app.test_client()
            with client_sin_hogar.session_transaction() as sess:
                sess["usuario"] = nombre_ajeno
                sess["usuario_id"] = usuario_ajeno_id
            resp = client_sin_hogar.get("/api/consumo/resumen")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json(), {"dias": [], "por_producto": []})
        finally:
            with self.app.app_context():
                db = get_db()
                db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_ajeno_id,))
                db.commit()

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get("/api/consumo/resumen")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
