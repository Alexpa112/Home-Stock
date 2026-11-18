"""Tope de categorias creadas por usuarios: el catalogo es compartido entre hogares y sin tope un
solo usuario con permiso de edicion podria llenarlo de basura (stockhogar/servicios/catalogo_categorias.py)."""
import unittest
import uuid
from unittest import mock

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class TopeCategoriasTests(unittest.TestCase):
    NOMBRE_CATEGORIA = "ZzzTopeCategoria"

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

    def _crear(self, ruta, nombre):
        return self.client.post(ruta, json={"nombre": nombre})

    def test_el_tope_corta_la_creacion_de_categorias_de_producto_y_de_gasto(self):
        for ruta in ("/api/categorias", "/api/categorias-gasto"):
            with self.app.app_context():
                tabla = "categorias" if ruta == "/api/categorias" else "categorias_gasto"
                total = get_db().execute(f"SELECT COUNT(*) AS n FROM {tabla}").fetchone()["n"]
            from stockhogar.rutas.inventario.categorias import CATALOGO as CAT_P
            from stockhogar.rutas.finanzas.categorias_gasto import CATALOGO as CAT_G
            de_serie = len(CAT_P.de_serie if tabla == "categorias" else CAT_G.de_serie)
            # el tope se alcanza justo con las que ya hay mas una: la siguiente es rechazada
            with mock.patch("stockhogar.servicios.catalogo_categorias.MAX_CATEGORIAS_PERSONALIZADAS", total - de_serie):
                r = self._crear(ruta, self.NOMBRE_CATEGORIA + uuid.uuid4().hex[:6])
            self.assertEqual(r.status_code, 400, (ruta, r.get_data(as_text=True)))
            with mock.patch("stockhogar.servicios.catalogo_categorias.MAX_CATEGORIAS_PERSONALIZADAS", total - de_serie + 1):
                nombre = self.NOMBRE_CATEGORIA + uuid.uuid4().hex[:6]
                r = self._crear(ruta, nombre)
            self.assertEqual(r.status_code, 201, (ruta, r.get_data(as_text=True)))
            with self.app.app_context():
                db = get_db()
                db.execute(f"DELETE FROM {tabla} WHERE nombre = ?", (nombre,))
                db.commit()

    def test_el_tope_por_defecto_es_razonable(self):
        from stockhogar.servicios.catalogo_categorias import MAX_CATEGORIAS_PERSONALIZADAS
        self.assertTrue(50 <= MAX_CATEGORIAS_PERSONALIZADAS <= 1000)


if __name__ == "__main__":
    unittest.main()
