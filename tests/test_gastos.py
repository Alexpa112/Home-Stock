"""Tests de la funcionalidad de gastos compartidos del hogar (tipo Tricount):
permisos de escritura, validacion del reparto, calculo de saldo neto y
registro de liquidaciones. Ver stockhogar/rutas/gastos.py."""
import io
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

    def test_listar_liquidaciones_devuelve_historial(self):
        self._crear_gasto_valido(self.client_propietario)
        self.client_editor.post(
            "/api/gastos/liquidaciones",
            json={"usuario_origen_id": self.editor_id, "usuario_destino_id": self.propietario_id, "importe": 15, "nota": "Bizum"},
        )

        resp = self.client_viewer.get("/api/gastos/liquidaciones")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["usuario_origen_id"], self.editor_id)
        self.assertEqual(data[0]["usuario_destino_id"], self.propietario_id)
        self.assertEqual(data[0]["nota"], "Bizum")

    def test_viewer_no_puede_eliminar_liquidacion(self):
        self._crear_gasto_valido(self.client_propietario)
        self.client_editor.post(
            "/api/gastos/liquidaciones",
            json={"usuario_origen_id": self.editor_id, "usuario_destino_id": self.propietario_id, "importe": 15},
        )
        liquidacion_id = self.client_propietario.get("/api/gastos/liquidaciones").get_json()[0]["id"]

        resp = self.client_viewer.delete(f"/api/gastos/liquidaciones/{liquidacion_id}")
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_eliminar_liquidacion_inexistente_da_404(self):
        resp = self.client_propietario.delete("/api/gastos/liquidaciones/999999")
        self.assertEqual(resp.status_code, 404, resp.get_data(as_text=True))

    def test_eliminar_liquidacion_revierte_el_saldo(self):
        self._crear_gasto_valido(self.client_propietario)
        self.client_editor.post(
            "/api/gastos/liquidaciones",
            json={"usuario_origen_id": self.editor_id, "usuario_destino_id": self.propietario_id, "importe": 15},
        )
        liquidacion_id = self.client_propietario.get("/api/gastos/liquidaciones").get_json()[0]["id"]

        resp = self.client_propietario.delete(f"/api/gastos/liquidaciones/{liquidacion_id}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

        saldo = {
            f["usuario_id"]: f["saldo"]
            for f in self.client_propietario.get("/api/gastos/saldo").get_json()
        }
        self.assertAlmostEqual(saldo[self.propietario_id], 15.0)
        self.assertAlmostEqual(saldo[self.editor_id], -15.0)
        self.assertEqual(self.client_propietario.get("/api/gastos/liquidaciones").get_json(), [])

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

    def test_miembros_basico_usa_nombre_a_mostrar_si_existe(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", ("Nombre Bonito", self.propietario_id))
            db.commit()

        resp = self.client_viewer.get(f"/api/hogares/{self.hogar_id}/miembros-basico")
        miembro = next(m for m in resp.get_json() if m["id"] == self.propietario_id)
        self.assertEqual(miembro["nombre_usuario"], "Nombre Bonito")

        otro = next(m for m in resp.get_json() if m["id"] == self.editor_id)
        self.assertNotEqual(otro["nombre_usuario"], "")  # sigue devolviendo el username sin nombre configurado

    def test_gasto_usa_nombre_a_mostrar_si_existe(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", ("Nombre Bonito", self.propietario_id))
            db.commit()

        resp = self._crear_gasto_valido(self.client_propietario)
        self.assertEqual(resp.get_json()["pagador_nombre"], "Nombre Bonito")

        saldo = {f["nombre_usuario"] for f in self.client_propietario.get("/api/gastos/saldo").get_json()}
        self.assertIn("Nombre Bonito", saldo)

    def test_simplificar_sin_gastos_no_sugiere_nada(self):
        resp = self.client_propietario.get("/api/gastos/simplificar")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json(), [])

    def test_simplificar_sugiere_pago_directo(self):
        self._crear_gasto_valido(self.client_propietario)

        resp = self.client_propietario.get("/api/gastos/simplificar")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        sugerencias = resp.get_json()
        self.assertEqual(len(sugerencias), 1)
        self.assertEqual(sugerencias[0]["usuario_origen_id"], self.editor_id)
        self.assertEqual(sugerencias[0]["usuario_destino_id"], self.propietario_id)
        self.assertAlmostEqual(sugerencias[0]["importe"], 15.0)

    def test_simplificar_elimina_intermediario(self):
        # viewer paga 30 (viewer+editor a 15 cada uno) -> viewer +15, editor -15
        self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Cena",
                "importe_total": 30,
                "usuario_pagador_id": self.viewer_id,
                "participantes": [
                    {"usuario_id": self.viewer_id, "importe": 15},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )
        # editor paga 30 (editor+propietario a 15 cada uno) -> editor +15 (neto 0), propietario -15
        self.client_propietario.post(
            "/api/gastos",
            json={
                "descripcion": "Almuerzo",
                "importe_total": 30,
                "usuario_pagador_id": self.editor_id,
                "participantes": [
                    {"usuario_id": self.editor_id, "importe": 15},
                    {"usuario_id": self.propietario_id, "importe": 15},
                ],
            },
        )

        saldo = {
            f["usuario_id"]: f["saldo"]
            for f in self.client_propietario.get("/api/gastos/saldo").get_json()
        }
        self.assertAlmostEqual(saldo[self.editor_id], 0.0)

        resp = self.client_propietario.get("/api/gastos/simplificar")
        sugerencias = resp.get_json()
        # El editor queda neutro (paga y recibe lo mismo) -> se elimina como intermediario:
        # el propietario paga directamente al viewer en una única transacción.
        self.assertEqual(len(sugerencias), 1)
        self.assertEqual(sugerencias[0]["usuario_origen_id"], self.propietario_id)
        self.assertEqual(sugerencias[0]["usuario_destino_id"], self.viewer_id)
        self.assertAlmostEqual(sugerencias[0]["importe"], 15.0)

    def test_gasto_sin_recibo_indica_tiene_recibo_false(self):
        resp = self._crear_gasto_valido(self.client_propietario)
        self.assertFalse(resp.get_json()["tiene_recibo"])

    def test_viewer_no_puede_subir_recibo(self):
        resp_gasto = self._crear_gasto_valido(self.client_propietario)
        gasto_id = resp_gasto.get_json()["id"]

        resp = self.client_viewer.post(
            f"/api/gastos/{gasto_id}/recibo",
            data={"foto": (io.BytesIO(b"contenido-fake"), "recibo.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_subir_recibo_formato_no_permitido(self):
        resp_gasto = self._crear_gasto_valido(self.client_propietario)
        gasto_id = resp_gasto.get_json()["id"]

        resp = self.client_propietario.post(
            f"/api/gastos/{gasto_id}/recibo",
            data={"foto": (io.BytesIO(b"no es una imagen"), "recibo.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_subir_y_obtener_recibo(self):
        resp_gasto = self._crear_gasto_valido(self.client_propietario)
        gasto_id = resp_gasto.get_json()["id"]
        contenido = b"contenido-fake-de-imagen"

        resp_subida = self.client_propietario.post(
            f"/api/gastos/{gasto_id}/recibo",
            data={"foto": (io.BytesIO(contenido), "recibo.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp_subida.status_code, 200, resp_subida.get_data(as_text=True))
        self.assertTrue(resp_subida.get_json()["tiene_recibo"])

        resp_get = self.client_viewer.get(f"/api/gastos/{gasto_id}/recibo")
        self.assertEqual(resp_get.status_code, 200, resp_get.get_data(as_text=True))
        self.assertEqual(resp_get.data, contenido)
        self.assertEqual(resp_get.content_type, "image/jpeg")

        resp_lista = self.client_propietario.get("/api/gastos")
        gasto = next(g for g in resp_lista.get_json() if g["id"] == gasto_id)
        self.assertTrue(gasto["tiene_recibo"])

    def test_recibo_de_gasto_sin_adjuntar_da_404(self):
        resp_gasto = self._crear_gasto_valido(self.client_propietario)
        gasto_id = resp_gasto.get_json()["id"]

        resp = self.client_propietario.get(f"/api/gastos/{gasto_id}/recibo")
        self.assertEqual(resp.status_code, 404, resp.get_data(as_text=True))

    def test_eliminar_recibo(self):
        resp_gasto = self._crear_gasto_valido(self.client_propietario)
        gasto_id = resp_gasto.get_json()["id"]
        self.client_propietario.post(
            f"/api/gastos/{gasto_id}/recibo",
            data={"foto": (io.BytesIO(b"contenido-fake"), "recibo.jpg")},
            content_type="multipart/form-data",
        )

        resp_delete = self.client_propietario.delete(f"/api/gastos/{gasto_id}/recibo")
        self.assertEqual(resp_delete.status_code, 200, resp_delete.get_data(as_text=True))

        resp_get = self.client_propietario.get(f"/api/gastos/{gasto_id}/recibo")
        self.assertEqual(resp_get.status_code, 404)


if __name__ == "__main__":
    unittest.main()
