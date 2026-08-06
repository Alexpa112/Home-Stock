"""Tests de las categorías de gasto (independientes de las de producto):
CRUD basico, semilla inicial, y bloqueo de borrado si es la categoría por
defecto o si está en uso por algún gasto. Ver stockhogar/rutas/categorias_gasto.py."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class CategoriasGastoTests(unittest.TestCase):
    NOMBRE_CATEGORIA = "ZzzCategoriaGastoTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_catgasto_{uuid.uuid4().hex[:8]}"
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
                ("Hogar categoria gasto test", self.usuario_id, ahora(), ahora()),
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
            db.execute("DELETE FROM categorias_gasto WHERE nombre = ?", (self.NOMBRE_CATEGORIA,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear_gasto_con_categoria(self, categoria):
        return self.client.post(
            "/api/gastos",
            json={
                "descripcion": "Gasto de prueba",
                "importe_total": 10,
                "usuario_pagador_id": self.usuario_id,
                "categoria": categoria,
                "participantes": [{"usuario_id": self.usuario_id, "importe": 10}],
            },
        )

    def test_listar_incluye_las_categorias_seed(self):
        resp = self.client.get("/api/categorias-gasto")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        nombres = {c["nombre"] for c in resp.get_json()}
        for esperada in ("Alimentación", "Transporte", "Vivienda", "Ocio", "Salud", "Suministros", "Otros"):
            self.assertIn(esperada, nombres)

    def test_crear_categoria_con_icono_la_persiste(self):
        resp = self.client.post(
            "/api/categorias-gasto", json={"nombre": self.NOMBRE_CATEGORIA, "icono": "lightbulb"}
        )
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["icono"], "lightbulb")

    def test_crear_categoria_duplicada_da_400(self):
        self.client.post("/api/categorias-gasto", json={"nombre": self.NOMBRE_CATEGORIA})
        resp = self.client.post(
            "/api/categorias-gasto", json={"nombre": self.NOMBRE_CATEGORIA.upper()}
        )
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_no_se_puede_borrar_otros(self):
        categorias = self.client.get("/api/categorias-gasto").get_json()
        otros = next(c for c in categorias if c["nombre"] == "Otros")
        resp = self.client.delete(f"/api/categorias-gasto/{otros['id']}")
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))

    def test_no_se_puede_borrar_categoria_en_uso(self):
        resp_crear = self.client.post("/api/categorias-gasto", json={"nombre": self.NOMBRE_CATEGORIA})
        categoria_id = resp_crear.get_json()["id"]

        resp_gasto = self._crear_gasto_con_categoria(self.NOMBRE_CATEGORIA)
        self.assertEqual(resp_gasto.status_code, 201, resp_gasto.get_data(as_text=True))

        resp = self.client.delete(f"/api/categorias-gasto/{categoria_id}")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True))

    def test_borrar_categoria_no_usada_devuelve_200(self):
        resp_crear = self.client.post("/api/categorias-gasto", json={"nombre": self.NOMBRE_CATEGORIA})
        categoria_id = resp_crear.get_json()["id"]

        resp = self.client.delete(f"/api/categorias-gasto/{categoria_id}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_borrar_categoria_inexistente_da_404(self):
        resp = self.client.delete("/api/categorias-gasto/999999999")
        self.assertEqual(resp.status_code, 404, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
