"""Tests de regresion: asignar icono al crear una categoria y cambiar el
icono de un articulo personalizado deben persistirse correctamente.

El bug original era de frontend (el formulario de nueva categoria no
ofrecia selector de icono, y el de edicion de articulos personalizados
tampoco), pero estos tests cubren el contrato del backend que el frontend
debe respetar: /api/categorias POST debe guardar icono, y
/api/articulos/personalizados/<id> PATCH debe poder cambiarlo."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class IconosCategoriasYPersonalizadosTests(unittest.TestCase):
    NOMBRE_CATEGORIA = "ZzzCategoriaIconoTest"
    NOMBRE_LIBRE = "ZzzArticuloIconoTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_iconos_{uuid.uuid4().hex[:8]}"
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
                ("Hogar icono test", self.usuario_id, ahora(), ahora()),
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
            db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM articulos_personalizados WHERE nombre = ?", (self.NOMBRE_LIBRE,)
            )
            db.execute("DELETE FROM categorias WHERE nombre = ?", (self.NOMBRE_CATEGORIA,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_crear_categoria_con_icono_lo_persiste(self):
        resp = self.client.post(
            "/api/categorias", json={"nombre": self.NOMBRE_CATEGORIA, "icono": "lightbulb"}
        )
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["icono"], "lightbulb")

        resp = self.client.get("/api/categorias")
        creada = next(c for c in resp.get_json() if c["nombre"] == self.NOMBRE_CATEGORIA)
        self.assertEqual(creada["icono"], "lightbulb")

    def test_cambiar_icono_de_articulo_personalizado_lo_persiste(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_LIBRE, "cantidad": 1})
        articulo_personalizado_id = resp.get_json()["articulo_personalizado_id"]
        self.assertIsNotNone(articulo_personalizado_id)

        resp = self.client.patch(
            f"/api/articulos/personalizados/{articulo_personalizado_id}", json={"icono": "apple"}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["icono"], "apple")

        resp = self.client.get("/api/articulos/personalizados")
        propio = next(a for a in resp.get_json() if a["id"] == articulo_personalizado_id)
        self.assertEqual(propio["icono"], "apple")


if __name__ == "__main__":
    unittest.main()
