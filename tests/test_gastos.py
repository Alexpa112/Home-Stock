"""Tests de la funcionalidad de gastos compartidos del hogar (tipo Tricount):
permisos de escritura, validacion del reparto, calculo de saldo neto y
registro de liquidaciones. Ver stockhogar/rutas/gastos.py."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class GastosTests(unittest.TestCase):
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
        nombre_usuario = f"test_gastos_{sufijo}_{uuid.uuid4().hex[:8]}"
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
                "DELETE FROM gastos_participantes WHERE gasto_id IN (SELECT id FROM gastos WHERE hogar_id = ?)",
                (self.hogar_id,),
            )
            db.execute("DELETE FROM gastos WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM liquidaciones WHERE hogar_id = ?", (self.hogar_id,))
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

    def _crear_gasto_valido(self, client):
        return client.post(
            "/api/gastos",
            json={
                "descripcion": "Compra semanal",
                "importe_total": 40,
                "usuario_pagador_id": self.propietario_id,
                "participantes": [
                    {"usuario_id": self.propietario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )

    def test_viewer_no_puede_crear_gasto(self):
        resp = self._crear_gasto_valido(self.client_viewer)
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_editor_crea_gasto_con_reparto_flexible(self):
        resp = self._crear_gasto_valido(self.client_editor)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        data = resp.get_json()
        self.assertEqual(data["importe_total"], 40)
        self.assertEqual(len(data["participantes"]), 2)

    def test_reparto_que_no_cuadra_da_error(self):
        resp = self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Reparto mal calculado",
                "importe_total": 40,
                "usuario_pagador_id": self.propietario_id,
                "participantes": [
                    {"usuario_id": self.propietario_id, "importe": 10},
                    {"usuario_id": self.editor_id, "importe": 10},
                ],
            },
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_viewer_puede_listar_gastos_y_ver_saldo(self):
        self._crear_gasto_valido(self.client_propietario)

        resp_lista = self.client_viewer.get("/api/gastos")
        self.assertEqual(resp_lista.status_code, 200)
        self.assertEqual(len(resp_lista.get_json()), 1)

        resp_saldo = self.client_viewer.get("/api/gastos/saldo")
        self.assertEqual(resp_saldo.status_code, 200)

    def test_saldo_refleja_pagador_y_participantes(self):
        self._crear_gasto_valido(self.client_propietario)

        saldo = {
            f["usuario_id"]: f["saldo"]
            for f in self.client_propietario.get("/api/gastos/saldo").get_json()
        }
        # El propietario pagó 40 y le corresponden 25 -> le deben 15.
        self.assertAlmostEqual(saldo[self.propietario_id], 15.0)
        # El editor debe su parte (15) y no pagó nada -> debe 15.
        self.assertAlmostEqual(saldo[self.editor_id], -15.0)

    def test_liquidacion_salda_el_saldo(self):
        self._crear_gasto_valido(self.client_propietario)

        resp = self.client_editor.post(
            "/api/gastos/liquidaciones",
            json={"usuario_origen_id": self.editor_id, "usuario_destino_id": self.propietario_id, "importe": 15},
        )
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))

        saldo = {
            f["usuario_id"]: f["saldo"]
            for f in self.client_propietario.get("/api/gastos/saldo").get_json()
        }
        self.assertAlmostEqual(saldo[self.propietario_id], 0.0)
        self.assertAlmostEqual(saldo[self.editor_id], 0.0)

    def test_crear_gasto_con_categoria_valida_la_persiste(self):
        resp = self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Billetes de tren",
                "importe_total": 40,
                "usuario_pagador_id": self.propietario_id,
                "categoria": "Transporte",
                "participantes": [
                    {"usuario_id": self.propietario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["categoria"], "Transporte")

    def test_crear_gasto_sin_categoria_queda_none(self):
        resp = self._crear_gasto_valido(self.client_propietario)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertIsNone(resp.get_json()["categoria"])

    def test_crear_gasto_con_categoria_desconocida_cae_a_otros(self):
        resp = self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Gasto raro",
                "importe_total": 40,
                "usuario_pagador_id": self.propietario_id,
                "categoria": f"NoExiste_{uuid.uuid4().hex[:6]}",
                "participantes": [
                    {"usuario_id": self.propietario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["categoria"], "Otros")

    def test_actualizar_gasto_permite_quitar_categoria(self):
        resp = self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Compra con categoría",
                "importe_total": 40,
                "usuario_pagador_id": self.propietario_id,
                "categoria": "Ocio",
                "participantes": [
                    {"usuario_id": self.propietario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )
        gasto_id = resp.get_json()["id"]

        resp_patch = self.client_propietario.patch(f"/api/gastos/{gasto_id}", json={"categoria": None})
        self.assertEqual(resp_patch.status_code, 200, resp_patch.get_data(as_text=True))
        self.assertIsNone(resp_patch.get_json()["categoria"])

    def test_viewer_puede_ver_miembros_basico(self):
        resp = self.client_viewer.get(f"/api/hogares/{self.hogar_id}/miembros-basico")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        ids = {m["id"] for m in resp.get_json()}
        self.assertEqual(ids, {self.propietario_id, self.editor_id, self.viewer_id})


if __name__ == "__main__":
    unittest.main()
