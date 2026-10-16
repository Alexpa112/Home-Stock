"""Tests de regresion para el aislamiento de articulos_personalizados por hogar.

Cubre el bug donde el catalogo de articulos personalizados se deduplicaba por
nombre a nivel de TODA la instalacion, sin ninguna columna de propietario:
dos hogares no relacionados con un articulo del mismo nombre (p.ej. "Leche")
acababan compartiendo la misma fila, y cualquiera de ellos podia renombrarla,
cambiarle el icono/categoria o borrarla, afectando al otro hogar.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class AislamientoArticulosPersonalizadosTests(unittest.TestCase):
    NOMBRE_ARTICULO = "ZzzLecheMarcaAislamientoTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.usuarios_creados = []
        self.listas_creadas = []

        self.usuario_a_id, self.lista_a_id, self.client_a = self._crear_usuario_con_lista("a")
        self.usuario_b_id, self.lista_b_id, self.client_b = self._crear_usuario_con_lista("b")

    def _crear_usuario_con_lista(self, sufijo):
        nombre_usuario = f"test_{sufijo}_{uuid.uuid4().hex[:8]}"
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
                (f"Lista de {sufijo}", usuario_id, ahora(), ahora()),
            )
            hogar_id = cur.lastrowid
            db.commit()

        self.usuarios_creados.append(usuario_id)
        self.listas_creadas.append(hogar_id)

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = hogar_id

        return usuario_id, hogar_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            for hogar_id in self.listas_creadas:
                db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (hogar_id,))
                db.execute("DELETE FROM hogares WHERE id = ?", (hogar_id,))
            db.execute(
                "DELETE FROM traducciones_productos WHERE articulo_personalizado_id IN "
                "(SELECT id FROM articulos_personalizados WHERE nombre = ?)",
                (self.NOMBRE_ARTICULO,),
            )
            db.execute("DELETE FROM articulos_personalizados WHERE nombre = ?", (self.NOMBRE_ARTICULO,))
            for usuario_id in self.usuarios_creados:
                db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            db.commit()

    def _crear_articulo_personalizado(self, client):
        resp = client.post("/api/articulos", json={"nombre": self.NOMBRE_ARTICULO, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
        return resp.get_json()["articulo_personalizado_id"]

    def test_mismo_nombre_en_hogares_distintos_no_comparte_fila(self):
        id_a = self._crear_articulo_personalizado(self.client_a)
        id_b = self._crear_articulo_personalizado(self.client_b)

        self.assertIsNotNone(id_a)
        self.assertIsNotNone(id_b)
        self.assertNotEqual(
            id_a, id_b,
            "Dos hogares distintos con un articulo del mismo nombre no deben compartir la misma fila",
        )

    def test_usuario_b_no_puede_editar_articulo_personalizado_de_usuario_a(self):
        id_a = self._crear_articulo_personalizado(self.client_a)

        resp = self.client_b.patch(
            f"/api/articulos/personalizados/{id_a}",
            json={"nombre": "Nombre cambiado por B"},
        )
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_usuario_b_no_puede_borrar_articulo_personalizado_de_usuario_a(self):
        id_a = self._crear_articulo_personalizado(self.client_a)

        resp = self.client_b.delete(f"/api/articulos/personalizados/{id_a}")
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT id FROM articulos_personalizados WHERE id = ?", (id_a,)
            ).fetchone()
            self.assertIsNotNone(fila, "El artículo de A no debe borrarse por una petición de B")

    def test_mismo_usuario_reutiliza_articulo_en_segunda_lista_propia(self):
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Segunda lista de a", self.usuario_a_id, ahora(), ahora()),
            )
            segunda_lista_id = cur.lastrowid
            db.commit()
        self.listas_creadas.append(segunda_lista_id)

        id_primera = self._crear_articulo_personalizado(self.client_a)

        with self.client_a.session_transaction() as sess:
            sess["hogar_actual_id"] = segunda_lista_id
        id_segunda = self._crear_articulo_personalizado(self.client_a)

        self.assertEqual(
            id_primera, id_segunda,
            "El mismo hogar debe reutilizar el mismo artículo personalizado entre sus propias hogares",
        )


if __name__ == "__main__":
    unittest.main()
