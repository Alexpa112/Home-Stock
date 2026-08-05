"""Test de exportacion completa de datos personales (S-22, RGPD art. 15/20):
GET /api/auth/exportar-mis-datos devuelve un ZIP con los datos del usuario
autenticado, sin datos de otros usuarios.
"""
import io
import json
import unittest
import uuid
import zipfile

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ExportarMisDatosTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        self.nombre_a = f"exp_a_{uuid.uuid4().hex[:8]}"
        self.nombre_b = f"exp_b_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, email) VALUES (?, ?, ?, ?)",
                (self.nombre_a, generate_password_hash("password123456"), ahora(), "a@example.com"),
            )
            self.usuario_a_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (self.nombre_b, generate_password_hash("password123456"), ahora()),
            )
            self.usuario_b_id = cur.lastrowid

            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar de A", self.usuario_a_id, ahora(), ahora()),
            )
            self.hogar_a_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Hogar de B", self.usuario_b_id, ahora(), ahora()),
            )
            self.hogar_b_id = cur.lastrowid

            db.execute(
                "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, fecha_creacion) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.hogar_a_id, "Gasto secreto de A", 42.0, ahora(), self.usuario_a_id, ahora()),
            )
            db.execute(
                "INSERT INTO gastos (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, fecha_creacion) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.hogar_b_id, "Gasto secreto de B", 99.0, ahora(), self.usuario_b_id, ahora()),
            )
            db.commit()

        with self.client.session_transaction() as sess:
            sess["usuario"] = self.nombre_a
            sess["usuario_id"] = self.usuario_a_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM gastos WHERE hogar_id IN (?, ?)", (self.hogar_a_id, self.hogar_b_id))
            db.execute("DELETE FROM hogares WHERE id IN (?, ?)", (self.hogar_a_id, self.hogar_b_id))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_a_id, self.usuario_b_id))
            db.commit()

    def test_zip_contiene_las_entradas_esperadas(self):
        resp = self.client.get("/api/auth/exportar-mis-datos")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/zip")

        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        nombres = zf.namelist()
        for esperado in ("perfil.json", "hogares.json", "inventario.json", "gastos.json", "movimientos_stock.json"):
            self.assertIn(esperado, nombres)

    def test_no_incluye_datos_de_otro_usuario(self):
        resp = self.client.get("/api/auth/exportar-mis-datos")
        zf = zipfile.ZipFile(io.BytesIO(resp.data))

        perfil = json.loads(zf.read("perfil.json"))
        self.assertEqual(perfil["nombre_usuario"], self.nombre_a)
        self.assertNotIn("password_hash", perfil)

        hogares = json.loads(zf.read("hogares.json"))
        nombres_hogares_propios = [h["nombre"] for h in hogares["propios"]]
        self.assertIn("Hogar de A", nombres_hogares_propios)
        self.assertNotIn("Hogar de B", nombres_hogares_propios)

        gastos = json.loads(zf.read("gastos.json"))
        descripciones = [g["descripcion"] for g in gastos["pagados_por_mi"]]
        self.assertIn("Gasto secreto de A", descripciones)
        self.assertNotIn("Gasto secreto de B", descripciones)


if __name__ == "__main__":
    unittest.main()
