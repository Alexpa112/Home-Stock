import unittest
import uuid

from werkzeug.security import generate_password_hash

from stockhogar import create_app
from stockhogar.db import ahora, get_db


class TraduccionArticuloPersonalizadoTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        nombre_usuario = f"test_{uuid.uuid4().hex[:8]}"

        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
                (nombre_usuario, generate_password_hash("password123"), ahora()),
            )
            usuario_id = cur.lastrowid
            cur = db.execute(
                "INSERT INTO listas (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista de test", usuario_id, ahora(), ahora()),
            )
            self.lista_id = cur.lastrowid
            db.commit()

        self.usuario_id = usuario_id
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["lista_actual_id"] = self.lista_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM articulos_lista WHERE lista_id IN "
                "(SELECT id FROM listas WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM listas WHERE usuario_propietario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            articulo = db.execute(
                "SELECT id FROM articulos_personalizados WHERE nombre = ?",
                ("ZzzArticuloTestUnico",),
            ).fetchone()
            if articulo:
                db.execute(
                    "DELETE FROM traducciones_productos WHERE articulo_personalizado_id = ?", (articulo["id"],)
                )
                db.execute("DELETE FROM articulos_personalizados WHERE id = ?", (articulo["id"],))
            db.commit()

    def test_crear_articulo_personalizado_genera_traducciones(self):
        nombre = "ZzzArticuloTestUnico"
        resp = self.client.post(
            "/api/articulos",
            json={"nombre": nombre, "cantidad": 1},
        )
        self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            articulo = db.execute(
                "SELECT id FROM articulos_personalizados WHERE nombre = ?", (nombre,)
            ).fetchone()
            self.assertIsNotNone(articulo, "El artículo personalizado no se creó")

            traducciones = db.execute(
                "SELECT idioma, texto_original, texto_traducido FROM traducciones_productos "
                "WHERE articulo_personalizado_id = ? AND tipo = 'nombre'",
                (articulo["id"],),
            ).fetchall()

            idiomas_esperados = {"gl", "en", "pt", "fr", "it", "de"}
            idiomas_obtenidos = {t["idioma"] for t in traducciones}
            self.assertTrue(
                idiomas_esperados.issubset(idiomas_obtenidos),
                f"Faltan traducciones. Obtenidas: {idiomas_obtenidos}",
            )
            for t in traducciones:
                self.assertTrue(t["texto_traducido"], f"Traducción vacía para {t['idioma']}")


if __name__ == "__main__":
    unittest.main()
