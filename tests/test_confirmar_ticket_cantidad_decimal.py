"""Regresion: confirmar un ticket no debe perder los articulos a peso.

Bug real: POST /api/tickets/confirmar validaba la cantidad con
Validator.entero_no_negativo, que hace int(valor) y por tanto TRUNCA. Los dos
motores de OCR producen cantidades fraccionarias legitimas para el granel
(el endpoint acepta unidades kg/g/l/ml), asi que "TOMATE PERA 0,850 kg" se
guardaba con cantidad 0 mientras la respuesta contestaba {"creados": 1}: el
usuario creia que se habia importado. Ademas, con stock_minimo=1 el articulo
reaparecia acto seguido en la lista de la compra como "falta".
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db

NOMBRE = "ZzzTomatePesoTest"


class ConfirmarTicketCantidadDecimalTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_peso_{uuid.uuid4().hex[:8]}"
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
                ("Hogar peso", self.usuario_id, ahora(), ahora()),
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
                "DELETE FROM stock_hogar WHERE producto_id IN (SELECT id FROM productos WHERE nombre = ?)",
                (NOMBRE,),
            )
            db.execute("DELETE FROM productos WHERE nombre = ?", (NOMBRE,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _stock_guardado(self):
        with self.app.app_context():
            db = get_db()
            return db.execute(
                "SELECT sh.cantidad FROM stock_hogar sh, productos p "
                "WHERE sh.producto_id = p.id AND p.nombre = ? AND sh.hogar_id = ?",
                (NOMBRE, self.hogar_id),
            ).fetchone()

    def test_articulo_a_peso_conserva_su_cantidad(self):
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": NOMBRE, "cantidad": 0.85, "unidad": "kg"}]},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json().get("creados"), 1)

        fila = self._stock_guardado()
        self.assertIsNotNone(fila, "el producto deberia existir tras confirmarlo")
        self.assertAlmostEqual(
            fila["cantidad"], 0.85, places=3,
            msg="la cantidad a peso se ha truncado: el articulo entra al stock vacio "
                "aunque la respuesta diga que se importo",
        )

    def test_cantidad_entera_sigue_guardandose_como_entero(self):
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": NOMBRE, "cantidad": 3, "unidad": "ud"}]},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        fila = self._stock_guardado()
        self.assertEqual(fila["cantidad"], 3)
        self.assertNotIsInstance(
            fila["cantidad"], float,
            "una cantidad entera no debe guardarse como decimal",
        )

    def test_cantidad_no_numerica_da_400_no_500(self):
        resp = self.client.post(
            "/api/tickets/confirmar",
            json={"items": [{"nombre": NOMBRE, "cantidad": "muchos", "unidad": "ud"}]},
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
