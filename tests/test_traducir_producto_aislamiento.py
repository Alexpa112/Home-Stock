"""Test de regresion: POST /api/productos/traducir no debe permitir que un
usuario sin acceso a un producto/articulo sobrescriba sus traducciones.

Antes, el endpoint aceptaba producto_id/articulo_id del body y grababa
directamente en traducciones_productos sin comprobar que pertenecieran a una
lista accesible por el usuario: cualquier usuario autenticado podia pasar el
ID de un producto/articulo de OTRO hogar (autoincremental, facil de
enumerar) y sobrescribir sus traducciones via INSERT OR REPLACE.
"""
import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class TraducirProductoAislamientoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        self.usuario_a_id, self.lista_a_id, self.client_a = self._crear_usuario_con_lista("a")
        self.usuario_b_id, self.lista_b_id, self.client_b = self._crear_usuario_con_lista("b")

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO productos (nombre, categoria, unidad, dias_aviso, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, 'Otros', 'ud', 30, ?, ?)",
                ("ZzzProductoTraducirAislamientoTest", ahora(), ahora()),
            )
            self.producto_id = cur.lastrowid
            db.execute(
                "INSERT INTO stock_hogar (hogar_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, 1, ?, ?)",
                (self.lista_a_id, self.producto_id, ahora(), ahora()),
            )
            db.commit()

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

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = hogar_id

        return usuario_id, hogar_id, client

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM traducciones_productos WHERE producto_id = ?", (self.producto_id,))
            db.execute("DELETE FROM stock_hogar WHERE producto_id = ?", (self.producto_id,))
            db.execute("DELETE FROM productos WHERE id = ?", (self.producto_id,))
            db.execute("DELETE FROM hogares WHERE id IN (?, ?)", (self.lista_a_id, self.lista_b_id))
            db.execute("DELETE FROM usuarios WHERE id IN (?, ?)", (self.usuario_a_id, self.usuario_b_id))
            db.commit()

    def test_dueno_de_la_lista_puede_traducir_su_producto(self):
        resp = self.client_a.post(
            "/api/productos/traducir",
            json={"nombre": "Leche", "producto_id": self.producto_id},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))

    def test_usuario_sin_acceso_no_puede_escribir_traducciones_de_producto_ajeno(self):
        resp = self.client_b.post(
            "/api/productos/traducir",
            json={"nombre": "Leche", "producto_id": self.producto_id},
        )
        self.assertEqual(resp.status_code, 403, resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            fila = db.execute(
                "SELECT texto_traducido FROM traducciones_productos WHERE producto_id = ? AND idioma = 'en'",
                (self.producto_id,),
            ).fetchone()
        self.assertIsNone(fila, "El usuario sin acceso no debe poder grabar traducciones")


if __name__ == "__main__":
    unittest.main()
