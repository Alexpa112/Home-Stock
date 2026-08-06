"""Tests de gastos recurrentes: plantillas que se materializan como gastos
normales al listar (generacion perezosa, sin tarea programada aparte).
Ver stockhogar/rutas/gastos.py: _generar_gastos_recurrentes_pendientes."""
import unittest
import uuid
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class GastosRecurrentesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.propietario_id, self.hogar_id, self.client_propietario = self._crear_usuario_con_hogar("owner")
        self.editor_id, _, self.client_editor = self._crear_usuario_con_hogar("editor")
        self.viewer_id, _, self.client_viewer = self._crear_usuario_con_hogar("viewer")

        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.editor_id, ahora()),
            )
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'ver', ?)",
                (self.hogar_id, self.viewer_id, ahora()),
            )
            db.commit()

        for client in (self.client_editor, self.client_viewer):
            with client.session_transaction() as sess:
                sess["hogar_actual_id"] = self.hogar_id

    def _crear_usuario_con_hogar(self, sufijo):
        nombre_usuario = f"test_recurr_{sufijo}_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                (f"Hogar de {sufijo}", usuario_id, ahora(), ahora()),
            )
            hogar_id = cur.lastrowid
            db.commit()

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = hogar_id

        return usuario_id, hogar_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM gastos_recurrentes_participantes WHERE gasto_recurrente_id IN "
                "(SELECT id FROM gastos_recurrentes WHERE hogar_id = ?)",
                (self.hogar_id,),
            )
            db.execute("DELETE FROM gastos_recurrentes WHERE hogar_id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM gastos_participantes WHERE gasto_id IN (SELECT id FROM gastos WHERE hogar_id = ?)",
                (self.hogar_id,),
            )
            db.execute("DELETE FROM gastos WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM hogares WHERE usuario_propietario_id IN (?, ?, ?)",
                (self.propietario_id, self.editor_id, self.viewer_id),
            )
            db.execute(
                "DELETE FROM usuarios WHERE id IN (?, ?, ?)",
                (self.propietario_id, self.editor_id, self.viewer_id),
            )
            db.commit()

    def _crear_recurrente(self, client, fecha_inicio, frecuencia="mensual", fecha_fin=None):
        datos = {
            "descripcion": "Alquiler",
            "importe_total": 40,
            "usuario_pagador_id": self.propietario_id,
            "frecuencia": frecuencia,
            "fecha_inicio": fecha_inicio,
            "participantes": [
                {"usuario_id": self.propietario_id, "importe": 25},
                {"usuario_id": self.editor_id, "importe": 15},
            ],
        }
        if fecha_fin:
            datos["fecha_fin"] = fecha_fin
        return client.post("/api/gastos/recurrentes", json=datos)

    def test_viewer_no_puede_crear_recurrente(self):
        resp = self._crear_recurrente(self.client_viewer, "2026-01-01")
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_frecuencia_invalida_da_error(self):
        resp = self.client_propietario.post(
            "/api/gastos/recurrentes",
            json={
                "descripcion": "Alquiler", "importe_total": 40, "usuario_pagador_id": self.propietario_id,
                "frecuencia": "diaria", "fecha_inicio": "2026-01-01",
                "participantes": [{"usuario_id": self.propietario_id, "importe": 40}],
            },
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_crear_recurrente_con_inicio_hoy_genera_gasto_inmediato(self):
        hoy = ahora()[:10]
        resp = self._crear_recurrente(self.client_propietario, hoy)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))

        resp_gastos = self.client_propietario.get("/api/gastos")
        gastos = resp_gastos.get_json()
        self.assertEqual(len(gastos), 1)
        self.assertEqual(gastos[0]["descripcion"], "Alquiler")
        self.assertEqual(len(gastos[0]["participantes"]), 2)

        recurrente = resp.get_json()
        proxima_esperada = self._siguiente_mensual(hoy)
        self.assertEqual(recurrente["proxima_fecha"], proxima_esperada)

    def test_crear_recurrente_con_inicio_futuro_no_genera_gasto(self):
        futuro = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        resp = self._crear_recurrente(self.client_propietario, futuro)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["proxima_fecha"], futuro)

        resp_gastos = self.client_propietario.get("/api/gastos")
        self.assertEqual(resp_gastos.get_json(), [])

    def test_listar_recurrentes(self):
        self._crear_recurrente(self.client_propietario, "2026-01-01")
        resp = self.client_viewer.get("/api/gastos/recurrentes")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["activo"])

    def test_pausar_recurrente_detiene_la_generacion(self):
        hoy = ahora()[:10]
        resp_crear = self._crear_recurrente(self.client_propietario, hoy)
        recurrente_id = resp_crear.get_json()["id"]

        resp_pausar = self.client_propietario.patch(
            f"/api/gastos/recurrentes/{recurrente_id}", json={"activo": False}
        )
        self.assertEqual(resp_pausar.status_code, 200, resp_pausar.get_data(as_text=True))
        self.assertFalse(resp_pausar.get_json()["activo"])

        # Ya se genero 1 gasto al crear; tras pausar, listar de nuevo no debe generar mas.
        self.client_propietario.get("/api/gastos")
        resp_gastos = self.client_propietario.get("/api/gastos")
        self.assertEqual(len(resp_gastos.get_json()), 1)

    def test_eliminar_recurrente_no_borra_gastos_ya_generados(self):
        hoy = ahora()[:10]
        resp_crear = self._crear_recurrente(self.client_propietario, hoy)
        recurrente_id = resp_crear.get_json()["id"]

        resp_delete = self.client_propietario.delete(f"/api/gastos/recurrentes/{recurrente_id}")
        self.assertEqual(resp_delete.status_code, 200, resp_delete.get_data(as_text=True))

        self.assertEqual(self.client_propietario.get("/api/gastos/recurrentes").get_json(), [])
        self.assertEqual(len(self.client_propietario.get("/api/gastos").get_json()), 1)

    def test_periodos_atrasados_generan_varios_gastos_y_desactiva_tras_fecha_fin(self):
        hoy = ahora()[:10]
        inicio = (datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d")  # ~2 meses atras
        fecha_fin = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")  # ya paso
        resp = self._crear_recurrente(self.client_propietario, inicio, fecha_fin=fecha_fin)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))

        resp_recurrentes = self.client_propietario.get("/api/gastos/recurrentes")
        recurrente = resp_recurrentes.get_json()[0]
        self.assertFalse(recurrente["activo"])  # se desactivo al superar fecha_fin

        resp_gastos = self.client_propietario.get("/api/gastos")
        # Al menos 2 ocurrencias mensuales entre "hace 70 dias" y "hace 5 dias".
        self.assertGreaterEqual(len(resp_gastos.get_json()), 2)

    @staticmethod
    def _siguiente_mensual(fecha_iso):
        fecha = datetime.fromisoformat(fecha_iso)
        mes = fecha.month + 1
        anio = fecha.year + (1 if mes > 12 else 0)
        mes = 1 if mes > 12 else mes
        import calendar
        dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
        return fecha.replace(year=anio, month=mes, day=dia).strftime("%Y-%m-%d")


if __name__ == "__main__":
    unittest.main()
