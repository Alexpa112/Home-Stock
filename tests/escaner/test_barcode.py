"""Tests de P-03 (escaneo de codigo de barras/EAN): busqueda en el
catalogo por codigo (GET /api/historial/codigo/<codigo>) y aprendizaje del
codigo al anadir un articulo a la lista con codigo_barras."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class BarcodeTests(unittest.TestCase):
    NOMBRE_ESTANDAR = "ZzzYogurBarcodeTest"
    CODIGO_ESTANDAR = "8410000000019"
    NOMBRE_NUEVO = "ZzzGalletasBarcodeTest"
    CODIGO_NUEVO = "8420000000026"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_barcode_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Lista barcode', ?, 1, ?, ?)",
                (self.usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.execute(
                "INSERT INTO historial_articulos (nombre, icono, categoria, unidad, codigo_barras, fecha_actualizacion) "
                "VALUES (?, 'apple', 'Lacteos', 'ud', ?, ?)",
                (self.NOMBRE_ESTANDAR, self.CODIGO_ESTANDAR, ahora()),
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
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.execute("DELETE FROM historial_articulos WHERE nombre IN (?, ?)", (self.NOMBRE_ESTANDAR, self.NOMBRE_NUEVO))
            db.commit()

    def test_busca_por_codigo_conocido(self):
        resp = self.client.get(f"/api/historial/codigo/{self.CODIGO_ESTANDAR}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(datos["nombre"], self.NOMBRE_ESTANDAR)
        self.assertEqual(datos["categoria"], "Lacteos")

    def test_codigo_desconocido_devuelve_404(self):
        resp = self.client.get("/api/historial/codigo/0000000000000")
        self.assertEqual(resp.status_code, 404)

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get(f"/api/historial/codigo/{self.CODIGO_ESTANDAR}")
        self.assertEqual(resp.status_code, 401)

    def test_anadir_articulo_con_codigo_lo_aprende_en_historial(self):
        resp = self.client.post(
            "/api/articulos",
            json={"nombre": self.NOMBRE_NUEVO, "icono": "cookie", "categoria": "Otros", "codigo_barras": self.CODIGO_NUEVO},
        )
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))

        resp = self.client.get(f"/api/historial/codigo/{self.CODIGO_NUEVO}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["nombre"], self.NOMBRE_NUEVO)


if __name__ == "__main__":
    unittest.main()
