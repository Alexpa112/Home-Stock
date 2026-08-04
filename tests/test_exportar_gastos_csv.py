"""Tests de la exportación CSV de gastos compartidos (formato largo: una
fila por gasto+participante). Ver stockhogar/rutas/gastos.py:exportar_gastos_csv."""
import csv
import io
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ExportarGastosCsvTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_exportcsv_{uuid.uuid4().hex[:8]}"
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
                ("Hogar export csv test", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid

            editor_nombre = f"test_exportcsv_editor_{uuid.uuid4().hex[:8]}"
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (editor_nombre, generate_password_hash("password123"), ahora()),
            )
            self.editor_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'editar', ?)",
                (self.hogar_id, self.editor_id, ahora()),
            )

            viewer_nombre = f"test_exportcsv_viewer_{uuid.uuid4().hex[:8]}"
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (viewer_nombre, generate_password_hash("password123"), ahora()),
            )
            self.viewer_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'ver', ?)",
                (self.hogar_id, self.viewer_id, ahora()),
            )
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = self.usuario_id
            sess["hogar_actual_id"] = self.hogar_id

        self.client_viewer = self.app.test_client()
        with self.client_viewer.session_transaction() as sess:
            sess["usuario"] = viewer_nombre
            sess["usuario_id"] = self.viewer_id
            sess["hogar_actual_id"] = self.hogar_id

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
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM usuarios WHERE id IN (?, ?, ?)",
                (self.usuario_id, self.editor_id, self.viewer_id),
            )
            db.commit()

    def _filas_csv(self, resp):
        contenido = resp.data.decode("utf-8-sig")
        return list(csv.reader(io.StringIO(contenido), delimiter=";"))

    def test_exportar_csv_devuelve_content_type_y_disposition(self):
        resp = self.client.get("/api/gastos/exportar")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertTrue(resp.content_type.startswith("text/csv"))
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))
        self.assertIn(".csv", resp.headers.get("Content-Disposition", ""))

    def test_exportar_csv_contiene_bom_utf8(self):
        resp = self.client.get("/api/gastos/exportar")
        self.assertEqual(resp.data[:3], b"\xef\xbb\xbf")

    def test_exportar_csv_hogar_sin_gastos_devuelve_solo_cabecera(self):
        resp = self.client.get("/api/gastos/exportar")
        self.assertEqual(resp.status_code, 200)
        filas = self._filas_csv(resp)
        self.assertEqual(len(filas), 1)

    def test_exportar_csv_una_fila_por_participante(self):
        self.client.post(
            "/api/gastos",
            json={
                "descripcion": "Cañón de descuento; oferta",
                "importe_total": 40,
                "usuario_pagador_id": self.usuario_id,
                "categoria": "Ocio",
                "participantes": [
                    {"usuario_id": self.usuario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )

        resp = self.client.get("/api/gastos/exportar")
        filas = self._filas_csv(resp)
        self.assertEqual(len(filas), 3)  # cabecera + 2 participantes
        descripciones = {fila[1] for fila in filas[1:]}
        self.assertEqual(descripciones, {"Cañón de descuento; oferta"})
        importes = {fila[3] for fila in filas[1:]}
        self.assertEqual(importes, {"40,00"})

    def test_exportar_csv_incluye_liquidaciones(self):
        self.client.post(
            "/api/gastos",
            json={
                "descripcion": "Compra semanal",
                "importe_total": 40,
                "usuario_pagador_id": self.usuario_id,
                "participantes": [
                    {"usuario_id": self.usuario_id, "importe": 25},
                    {"usuario_id": self.editor_id, "importe": 15},
                ],
            },
        )
        self.client.post(
            "/api/gastos/liquidaciones",
            json={"usuario_origen_id": self.editor_id, "usuario_destino_id": self.usuario_id, "importe": 15, "nota": "Bizum"},
        )

        resp = self.client.get("/api/gastos/exportar")
        filas = self._filas_csv(resp)
        self.assertEqual(len(filas), 4)  # cabecera + 2 participantes del gasto + 1 liquidación
        cabecera = filas[0]
        self.assertEqual(cabecera[-1], "Tipo")

        fila_liquidacion = filas[-1]
        self.assertEqual(fila_liquidacion[1], "Bizum")
        self.assertEqual(fila_liquidacion[3], "15,00")
        self.assertEqual(fila_liquidacion[-1], "Liquidación")

    def test_viewer_puede_exportar(self):
        resp = self.client_viewer.get("/api/gastos/exportar")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_sin_sesion_no_puede_exportar(self):
        cliente_anonimo = self.app.test_client()
        resp = cliente_anonimo.get("/api/gastos/exportar")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
