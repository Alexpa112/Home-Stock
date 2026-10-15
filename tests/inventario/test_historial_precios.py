"""Tests de P-04 (historial de precios): al confirmar un ticket con precio
detectado se registra en historial_precios, y GET /api/productos/<id>/precios
devuelve la evolucion para el producto en la lista activa."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class HistorialPreciosTests(unittest.TestCase):
    NOMBRE = "ZzzAceiteHistorialPreciosTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_precios_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Lista precios', ?, 1, ?, ?)",
                (self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM historial_precios WHERE producto_id IN (SELECT id FROM productos WHERE nombre = ?)",
                (self.NOMBRE,),
            )
            db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM productos WHERE nombre = ?", (self.NOMBRE,))
            db.execute("DELETE FROM historial_articulos WHERE nombre = ?", (self.NOMBRE,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _confirmar(self, precio_unitario=None, producto_id=None):
        item = {"nombre": self.NOMBRE, "cantidad": 1, "unidad": "ud"}
        if precio_unitario is not None:
            item["precio_unitario"] = precio_unitario
        if producto_id is not None:
            item["producto_id"] = producto_id
        resp = self.client.post("/api/tickets/confirmar", json={"items": [item]})
        self.assertIn(resp.status_code, (200,), resp.get_data(as_text=True))
        return resp

    def _producto_id(self):
        with self.app.app_context():
            db = get_db()
            fila = db.execute("SELECT id FROM productos WHERE nombre = ?", (self.NOMBRE,)).fetchone()
        return fila["id"]

    def test_confirmar_ticket_con_precio_lo_registra(self):
        self._confirmar(precio_unitario=1.99)
        producto_id = self._producto_id()

        resp = self.client.get(f"/api/productos/{producto_id}/precios")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        entradas = resp.get_json()
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]["precio"], 1.99)

    def test_confirmar_ticket_sin_precio_no_registra_nada(self):
        self._confirmar(precio_unitario=None)
        producto_id = self._producto_id()

        resp = self.client.get(f"/api/productos/{producto_id}/precios")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json(), [])

    def test_varias_confirmaciones_acumulan_historial(self):
        self._confirmar(precio_unitario=1.50)
        producto_id = self._producto_id()
        self._confirmar(precio_unitario=1.80, producto_id=producto_id)

        resp = self.client.get(f"/api/productos/{producto_id}/precios")
        precios = [e["precio"] for e in resp.get_json()]
        self.assertEqual(precios, [1.50, 1.80])

    def test_producto_de_otra_lista_devuelve_404(self):
        resp = self.client.get("/api/productos/999999/precios")
        self.assertEqual(resp.status_code, 404)

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get("/api/productos/1/precios")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
