"""Tests de P-06 (recetas): CRUD y anadir todos los ingredientes de una
receta a la lista de la compra activa de un golpe."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class RecetasTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_recetas_{uuid.uuid4().hex[:8]}"
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            self.usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar recetas', ?, 1, ?, ?)",
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
            db.execute(
                "DELETE FROM receta_ingredientes WHERE receta_id IN (SELECT id FROM recetas WHERE hogar_id = ?)",
                (self.hogar_id,),
            )
            db.execute("DELETE FROM recetas WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM articulos_personalizados WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear_receta(self):
        return self.client.post(
            "/api/recetas",
            json={
                "nombre": "ZzzTortillaTest",
                "ingredientes": [
                    {"nombre": "ZzzHuevosRecetaTest", "cantidad": 6, "unidad": "ud"},
                    {"nombre": "ZzzPatatasRecetaTest", "cantidad": 2, "unidad": "kg"},
                ],
            },
        )

    def test_crear_receta(self):
        resp = self._crear_receta()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(datos["nombre"], "ZzzTortillaTest")
        self.assertEqual(len(datos["ingredientes"]), 2)

    def test_crear_receta_sin_ingredientes_falla(self):
        resp = self.client.post("/api/recetas", json={"nombre": "Sin ingredientes", "ingredientes": []})
        self.assertEqual(resp.status_code, 400)

    def test_listar_recetas(self):
        self._crear_receta()
        resp = self.client.get("/api/recetas")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(len(resp.get_json()), 1)

    def test_actualizar_receta(self):
        receta_id = self._crear_receta().get_json()["id"]
        resp = self.client.patch(f"/api/recetas/{receta_id}", json={"nombre": "ZzzTortillaEditadaTest"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(resp.get_json()["nombre"], "ZzzTortillaEditadaTest")

    def test_eliminar_receta(self):
        receta_id = self._crear_receta().get_json()["id"]
        resp = self.client.delete(f"/api/recetas/{receta_id}")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/api/recetas")
        self.assertEqual(resp.get_json(), [])

    def test_anadir_receta_a_lista_crea_articulos(self):
        receta_id = self._crear_receta().get_json()["id"]
        resp = self.client.post(f"/api/recetas/{receta_id}/anadir-a-lista")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        datos = resp.get_json()
        self.assertEqual(datos["anadidos"], 2)

        resp_lista = self.client.get("/api/articulos")
        nombres = [a["nombre"] for a in resp_lista.get_json()["pendientes"]]
        self.assertIn("ZzzHuevosRecetaTest", nombres)
        self.assertIn("ZzzPatatasRecetaTest", nombres)

    def test_anadir_receta_a_lista_suma_si_ya_esta_en_la_lista(self):
        receta_id = self._crear_receta().get_json()["id"]
        self.client.post(f"/api/recetas/{receta_id}/anadir-a-lista")
        self.client.post(f"/api/recetas/{receta_id}/anadir-a-lista")

        resp_lista = self.client.get("/api/articulos")
        huevos = next(a for a in resp_lista.get_json()["pendientes"] if a["nombre"] == "ZzzHuevosRecetaTest")
        self.assertEqual(huevos["cantidad"], 12)

    def test_receta_inexistente_devuelve_404(self):
        resp = self.client.post("/api/recetas/999999/anadir-a-lista")
        self.assertEqual(resp.status_code, 404)

    def test_requiere_sesion(self):
        client_anonimo = self.app.test_client()
        resp = client_anonimo.get("/api/recetas")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
