"""Tests de edicion del campo dias_aviso ("dias sin actualizar para avisar",
lo mas cercano a una caducidad que existe en el proyecto) en la lista de la
compra y en el catalogo de articulos personalizados.

Cubre la regla de negocio: si se edita un campo que describe el articulo en
si (dias_aviso incluido) de un item que todavia apunta al catalogo ESTANDAR
(articulo_personalizado_id es NULL), el item se bifurca a un articulo
personalizado propio del hogar en vez de sobrescribir historial_articulos,
que es compartido por todas las hogares."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class EdicionDiasAvisoArticuloTests(unittest.TestCase):
    NOMBRE_ESTANDAR = "ZzzYogurCaducidadTest"
    NOMBRE_LIBRE = "ZzzArticuloLibreCaducidadTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_caducidad_{uuid.uuid4().hex[:8]}"
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
                ("Lista caducidad test", self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.execute(
                "INSERT INTO historial_articulos (nombre, icono, categoria, unidad, dias_aviso, fecha_actualizacion) "
                "VALUES (?, 'yogur', 'Lacteos', 'ud', 30, ?)",
                (self.NOMBRE_ESTANDAR, ahora()),
            )
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
                "DELETE FROM articulos_personalizados WHERE nombre IN (?, ?)",
                (self.NOMBRE_ESTANDAR, self.NOMBRE_LIBRE),
            )
            db.execute("DELETE FROM historial_articulos WHERE nombre = ?", (self.NOMBRE_ESTANDAR,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def test_editar_dias_aviso_de_articulo_estandar_lo_bifurca_a_personalizado(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_ESTANDAR, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
        item = resp.get_json()
        self.assertIsNone(item["articulo_personalizado_id"])
        self.assertEqual(item["dias_aviso"], 30)

        resp = self.client.patch(f"/api/articulos/{item['id']}", json={"dias_aviso": 5})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        actualizado = resp.get_json()
        self.assertEqual(actualizado["dias_aviso"], 5)
        self.assertIsNotNone(actualizado["articulo_personalizado_id"])

        with self.app.app_context():
            db = get_db()
            # El catalogo estandar compartido NO debe haberse tocado.
            estandar = db.execute(
                "SELECT dias_aviso FROM historial_articulos WHERE nombre = ?", (self.NOMBRE_ESTANDAR,)
            ).fetchone()
            self.assertEqual(estandar["dias_aviso"], 30)

            personal = db.execute(
                "SELECT dias_aviso FROM articulos_personalizados WHERE id = ?",
                (actualizado["articulo_personalizado_id"],),
            ).fetchone()
            self.assertEqual(personal["dias_aviso"], 5)

    def test_editar_articulo_ya_personalizado_actualiza_su_propio_catalogo(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_LIBRE, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
        item = resp.get_json()
        articulo_personalizado_id = item["articulo_personalizado_id"]
        self.assertIsNotNone(articulo_personalizado_id)

        resp = self.client.patch(f"/api/articulos/{item['id']}", json={"dias_aviso": 10})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["dias_aviso"], 10)
        self.assertEqual(resp.get_json()["articulo_personalizado_id"], articulo_personalizado_id)

        resp = self.client.get("/api/articulos/personalizados")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        propio = next(a for a in resp.get_json() if a["id"] == articulo_personalizado_id)
        self.assertEqual(propio["dias_aviso"], 10)

    def test_actualizar_articulo_personalizado_directamente(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_LIBRE, "cantidad": 1})
        articulo_personalizado_id = resp.get_json()["articulo_personalizado_id"]

        resp = self.client.patch(
            f"/api/articulos/personalizados/{articulo_personalizado_id}", json={"dias_aviso": 15}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["dias_aviso"], 15)

    def test_dias_aviso_nulo_al_editar_articulo_de_lista_conserva_el_anterior(self):
        """Vaciar el input de dias_aviso (llega null) no debe romper la
        petición: se conserva el valor que ya tenía el artículo."""
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_LIBRE, "cantidad": 1})
        item = resp.get_json()
        self.assertEqual(item["dias_aviso"], 30)

        resp = self.client.patch(f"/api/articulos/{item['id']}", json={"dias_aviso": 10})
        self.assertEqual(resp.get_json()["dias_aviso"], 10)

        resp = self.client.patch(f"/api/articulos/{item['id']}", json={"dias_aviso": None, "cantidad": 2})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["dias_aviso"], 10)
        self.assertEqual(resp.get_json()["cantidad"], 2)

    def test_dias_aviso_nulo_al_editar_articulo_personalizado_conserva_el_anterior(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_LIBRE, "cantidad": 1})
        articulo_personalizado_id = resp.get_json()["articulo_personalizado_id"]

        resp = self.client.patch(
            f"/api/articulos/personalizados/{articulo_personalizado_id}", json={"dias_aviso": 20}
        )
        self.assertEqual(resp.get_json()["dias_aviso"], 20)

        resp = self.client.patch(
            f"/api/articulos/personalizados/{articulo_personalizado_id}", json={"dias_aviso": None}
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["dias_aviso"], 20)


if __name__ == "__main__":
    unittest.main()
