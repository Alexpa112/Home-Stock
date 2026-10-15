"""Tests de P-08 (nivel de permiso intermedio 'comprar'): puede marcar
articulos como comprados/pendientes y mover stock, pero no crear/editar
articulos ni cambiar campos del producto en si (eso sigue exigiendo
'editar')."""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class NivelComprarTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        sufijo = uuid.uuid4().hex[:8]

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"prop_{sufijo}", generate_password_hash("password123"), ahora()),
            )
            self.propietario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (f"comprador_{sufijo}", generate_password_hash("password123"), ahora()),
            )
            self.comprador_id = cur.lastrowid

            cur = db.execute(
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES ('Hogar comprar', ?, 1, ?, ?)",
                (self.propietario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.execute(
                "INSERT INTO permisos_hogar (hogar_id, usuario_id, nivel, fecha_otorgado) VALUES (?, ?, 'comprar', ?)",
                (self.hogar_id, self.comprador_id, ahora()),
            )

            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES ('ZzzLecheComprarTest', 'Otros', 2, 'ud', 1, ?, ?) RETURNING id",
                (ahora(), ahora()),
            )
            self.producto_id = cur.fetchone()["id"]
            db.execute(
                "INSERT INTO stock_hogar (hogar_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 2, 1, ?, ?)",
                (self.hogar_id, self.producto_id, ahora(), ahora()),
            )
            cur = db.execute(
                "INSERT INTO articulos_compra (hogar_id, nombre, unidad, categoria, cantidad, activo, origen, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, 'ZzzPanComprarTest', 'ud', 'Otros', 1, 1, 'manual', ?, ?) RETURNING id",
                (self.hogar_id, ahora(), ahora()),
            )
            self.articulo_id = cur.fetchone()["id"]
            db.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = f"comprador_{sufijo}"
            sess["usuario_id"] = self.comprador_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM articulos_compra WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM stock_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM permisos_hogar WHERE hogar_id = ?", (self.hogar_id,))
            db.execute("DELETE FROM hogares WHERE id = ?", (self.hogar_id,))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.propietario_id, self.comprador_id))
            db.commit()

    def test_comprador_puede_marcar_articulo_comprado(self):
        resp = self.client.patch(f"/api/articulos/{self.articulo_id}", json={"activo": False})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_comprador_no_puede_renombrar_articulo(self):
        resp = self.client.patch(f"/api/articulos/{self.articulo_id}", json={"nombre": "ZzzOtroNombreTest"})
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_comprador_puede_mover_stock(self):
        resp = self.client.patch(f"/api/productos/{self.producto_id}", json={"delta": 1})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_comprador_no_puede_editar_campos_producto(self):
        resp = self.client.patch(f"/api/productos/{self.producto_id}", json={"nombre": "ZzzOtroTest"})
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_comprador_no_puede_anadir_articulo_nuevo(self):
        resp = self.client.post("/api/articulos", json={"nombre": "ZzzNuevoArticuloComprarTest"})
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

    def test_nivel_comprar_valido_al_compartir(self):
        cliente_propietario = self.app.test_client()
        with cliente_propietario.session_transaction() as sess:
            sess["usuario"] = "prop"
            sess["usuario_id"] = self.propietario_id
        resp = cliente_propietario.post(
            f"/api/hogares/{self.hogar_id}/compartir",
            json={"email": "nuevo_comprador@example.com", "nivel": "comprar"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM invitaciones_hogar WHERE hogar_id = ? AND email_destino = ?",
                (self.hogar_id, "nuevo_comprador@example.com"),
            )
            db.commit()


if __name__ == "__main__":
    unittest.main()
