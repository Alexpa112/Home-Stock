"""Confirmar un ticket registra el precio unitario en el historial de precios.

La pantalla de ticket no enviaba el precio al confirmar, asi que el historial de
precios (P-04) nunca se alimentaba desde tickets. Y el backend dejaba pasar
NaN/Infinity (el json de Python los acepta) hasta historial_precios.
"""
import json
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

NOMBRE = "ZzzPrecioTicketTest"


class ConfirmarTicketPrecioTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        nombre_usuario = f"test_precio_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            self.usuario_id = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            ).lastrowid
            self.hogar_id = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)", ("Hogar precio", self.usuario_id, ahora(), ahora()),
            ).lastrowid
            db.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            ids = [r["id"] for r in db.execute("SELECT id FROM productos WHERE nombre = ?", (NOMBRE,)).fetchall()]
            for pid in ids:
                db.execute("DELETE FROM historial_precios WHERE producto_id = ?", (pid,))
                db.execute("DELETE FROM stock_hogar WHERE producto_id = ?", (pid,))
            db.execute("DELETE FROM productos WHERE nombre = ?", (NOMBRE,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _precios(self):
        with self.app.app_context():
            db = get_db()
            return [r["precio"] for r in db.execute(
                "SELECT h.precio FROM historial_precios h, productos p "
                "WHERE h.producto_id = p.id AND p.nombre = ? AND h.hogar_id = ?",
                (NOMBRE, self.hogar_id)).fetchall()]

    def _confirmar(self, precio):
        # json= de Flask no codifica NaN con allow_nan por defecto en todas las
        # versiones: se manda el cuerpo a mano, como lo haria un cliente hostil.
        cuerpo = '{"items": [{"nombre": "%s", "cantidad": 1, "unidad": "ud", "precio_unitario": %s}]}' % (NOMBRE, precio)
        return self.client.post("/api/tickets/confirmar", data=cuerpo, content_type="application/json")

    def test_el_precio_unitario_llega_al_historial(self):
        resp = self._confirmar("1.89")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(self._precios(), [1.89])

    def test_sin_precio_no_se_registra_nada(self):
        resp = self.client.post(
            "/api/tickets/confirmar", json={"items": [{"nombre": NOMBRE, "cantidad": 1, "unidad": "ud"}]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._precios(), [])

    def test_precios_imposibles_se_ignoran_sin_romper_la_importacion(self):
        for malo in ("NaN", "Infinity", "-Infinity", "-3.5", "0", "1e12", '"abc"'):
            with self.subTest(precio=malo):
                resp = self._confirmar(malo)
                self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(self._precios(), [], "ningun precio imposible debe llegar al historial")


if __name__ == "__main__":
    unittest.main()
