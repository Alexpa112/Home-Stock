"""Tests de P-05 (presupuesto mensual): guardar presupuesto_mensual en el
hogar, GET /api/gastos/resumen-mes, y aviso push (una sola vez por mes) al
superarlo al crear un gasto."""
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class PresupuestoMensualTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_presupuesto_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar presupuesto', ?, 1, ?, ?)",
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
                "DELETE FROM gastos_participantes WHERE gasto_id IN (SELECT id FROM gastos WHERE hogar_id = ?)",
                (self.hogar_id,),
            )
            db.execute("DELETE FROM gastos WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear_gasto(self, importe):
        return self.client.post(
            "/api/gastos",
            json={
                "descripcion": "Gasto test",
                "importe_total": importe,
                "usuario_pagador_id": self.usuario_id,
                "participantes": [{"usuario_id": self.usuario_id, "importe": importe}],
            },
        )

    def test_guardar_presupuesto_mensual(self):
        resp = self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": 200})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["presupuesto_mensual"], 200)

    def test_presupuesto_negativo_rechazado(self):
        resp = self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": -5})
        self.assertEqual(resp.status_code, 400)

    def test_presupuesto_null_lo_borra(self):
        self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": 100})
        resp = self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": None})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertIsNone(resp.get_json()["presupuesto_mensual"])

    def test_resumen_mes_sin_presupuesto(self):
        self._crear_gasto(40)
        resp = self.client.get("/api/gastos/resumen-mes")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(datos["gasto_mes"], 40)
        self.assertIsNone(datos["presupuesto_mensual"])
        self.assertIsNone(datos["porcentaje"])

    def test_resumen_mes_con_presupuesto_calcula_porcentaje(self):
        self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": 100})
        self._crear_gasto(40)
        resp = self.client.get("/api/gastos/resumen-mes")
        datos = resp.get_json()
        self.assertEqual(datos["gasto_mes"], 40)
        self.assertEqual(datos["porcentaje"], 40.0)

    @patch("stockhogar.rutas.gastos.enviar_push_a_usuario")
    def test_avisa_push_al_superar_presupuesto(self, mock_push):
        self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": 50})
        self._crear_gasto(60)
        self.assertTrue(mock_push.called)

    @patch("stockhogar.rutas.gastos.enviar_push_a_usuario")
    def test_no_avisa_dos_veces_el_mismo_mes(self, mock_push):
        self.client.patch(f"/api/hogares/{self.hogar_id}", json={"presupuesto_mensual": 50})
        self._crear_gasto(60)
        mock_push.reset_mock()
        self._crear_gasto(10)
        self.assertFalse(mock_push.called)


if __name__ == "__main__":
    unittest.main()
