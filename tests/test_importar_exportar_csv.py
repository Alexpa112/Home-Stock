"""Tests de P-09 (importar/exportar inventario y lista de compra en CSV)."""
import io
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ImportarExportarCsvTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_csv_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar csv', ?, 1, ?, ?)",
                (self.usuario_id, ahora(), ahora()),
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
            db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute(
                "DELETE FROM productos WHERE nombre LIKE 'ZzzCsvTest%'"
            )
            db.execute("DELETE FROM historial_articulos WHERE nombre LIKE 'ZzzCsvTest%'")
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _subir_csv(self, ruta, contenido):
        data = {"fichero": (io.BytesIO(contenido.encode("utf-8")), "import.csv")}
        return self.client.post(ruta, data=data, content_type="multipart/form-data")

    def test_exportar_inventario_vacio(self):
        resp = self.client.get("/api/productos/exportar")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "text/csv; charset=utf-8")
        texto = resp.get_data(as_text=True)
        self.assertIn("nombre;categoria;unidad;cantidad;stock_minimo;dias_aviso", texto)

    def test_importar_inventario_crea_productos(self):
        csv_texto = (
            "nombre;categoria;unidad;cantidad;stock_minimo;dias_aviso\n"
            "ZzzCsvTestLeche;Lacteos;ud;3;1;30\n"
        )
        resp = self._subir_csv("/api/productos/importar", csv_texto)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["creados"], 1)

        resp_listar = self.client.get("/api/productos")
        nombres = [p["nombre"] for p in resp_listar.get_json()]
        self.assertIn("ZzzCsvTestLeche", nombres)

    def test_importar_inventario_actualiza_si_ya_existe(self):
        csv_texto = "nombre;categoria;unidad;cantidad;stock_minimo;dias_aviso\nZzzCsvTestPan;Otros;ud;2;1;30\n"
        self._subir_csv("/api/productos/importar", csv_texto)
        resp = self._subir_csv("/api/productos/importar", csv_texto.replace(";2;", ";7;"))
        self.assertEqual(resp.get_json()["actualizados"], 1)

        resp_listar = self.client.get("/api/productos")
        producto = next(p for p in resp_listar.get_json() if p["nombre"] == "ZzzCsvTestPan")
        self.assertEqual(producto["cantidad"], 7)

    def test_importar_inventario_sin_fichero_falla(self):
        resp = self.client.post("/api/productos/importar", data={}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)

    def test_exportar_lista_compra(self):
        self.client.post("/api/articulos", json={"nombre": "ZzzCsvTestArroz", "cantidad": 2})
        resp = self.client.get("/api/articulos/exportar")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ZzzCsvTestArroz", resp.get_data(as_text=True))

    def test_importar_lista_compra_anade_articulos(self):
        csv_texto = "nombre;categoria;unidad;cantidad;sub_descripcion\nZzzCsvTestPasta;Otros;ud;2;\n"
        resp = self._subir_csv("/api/articulos/importar", csv_texto)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["anadidos"], 1)

        resp_listar = self.client.get("/api/articulos")
        nombres = [a["nombre"] for a in resp_listar.get_json()["pendientes"]]
        self.assertIn("ZzzCsvTestPasta", nombres)

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get("/api/productos/exportar")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
