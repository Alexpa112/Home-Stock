"""Tests para GET /api/articulos/personalizados y para el borrado de un
articulo personalizado que ya no esta referenciado por ningun articulo de
la lista de la compra (activo o completado).

Cubre un bug de _usuario_puede_acceder_articulo_personalizado: comprobaba el
permiso mirando articulos_compra.hogar_id, asi que un articulo del catalogo
personal que ya no tuviera ninguna fila en articulos_compra (p.ej. tras
borrarlo de la lista) no podia ser eliminado ni por su propio dueno.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class ListadoYBorradoArticulosPersonalizadosTests(unittest.TestCase):
    NOMBRE_ARTICULO = "ZzzGalletasMarcaCatalogoTest"

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        nombre_usuario = f"test_cat_{uuid.uuid4().hex[:8]}"
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
                ("Lista de catalogo test", self.usuario_id, ahora(), ahora()),
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
                "DELETE FROM traducciones_productos WHERE articulo_personalizado_id IN "
                "(SELECT id FROM articulos_personalizados WHERE nombre = ?)",
                (self.NOMBRE_ARTICULO,),
            )
            db.execute("DELETE FROM articulos_personalizados WHERE nombre = ?", (self.NOMBRE_ARTICULO,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _crear_articulo_personalizado(self):
        resp = self.client.post("/api/articulos", json={"nombre": self.NOMBRE_ARTICULO, "cantidad": 1})
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
        return resp.get_json()["articulo_personalizado_id"]

    def test_listar_incluye_articulo_recien_creado(self):
        articulo_id = self._crear_articulo_personalizado()

        resp = self.client.get("/api/articulos/personalizados")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        nombres = [a["nombre"] for a in resp.get_json()]
        ids = [a["id"] for a in resp.get_json()]
        self.assertIn(self.NOMBRE_ARTICULO, nombres)
        self.assertIn(articulo_id, ids)

    def test_puede_borrar_articulo_ya_no_referenciado_en_articulos_compra(self):
        articulo_id = self._crear_articulo_personalizado()

        # Al quitarlo de la lista de la compra desaparece su unica fila en
        # articulos_compra: antes del fix esto dejaba el articulo huerfano
        # e imposible de borrar por su propio dueno.
        item = self.client.get("/api/articulos").get_json()["pendientes"][0]
        resp = self.client.delete(f"/api/articulos/{item['id']}")
        self.assertEqual(resp.status_code, 204, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            en_compra = db.execute(
                "SELECT COUNT(*) AS n FROM articulos_compra WHERE articulo_personalizado_id = ?",
                (articulo_id,),
            ).fetchone()["n"]
            self.assertEqual(en_compra, 0)

        resp = self.client.delete(f"/api/articulos/personalizados/{articulo_id}")
        self.assertEqual(resp.status_code, 204, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT id FROM articulos_personalizados WHERE id = ?", (articulo_id,)
            ).fetchone()
            self.assertIsNone(fila)


if __name__ == "__main__":
    unittest.main()
