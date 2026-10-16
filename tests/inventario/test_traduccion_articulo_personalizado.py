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
                "INSERT INTO hogares (nombre, usuario_propietario_id, privada, fecha_creacion, fecha_actualizacion) "
                "VALUES (?, ?, 1, ?, ?)",
                ("Lista de test", usuario_id, ahora(), ahora()),
            )
            self.hogar_id = cur.lastrowid
            db.commit()

        self.usuario_id = usuario_id
        with self.client.session_transaction() as sess:
            sess["usuario"] = nombre_usuario
            sess["usuario_id"] = usuario_id
            sess["hogar_actual_id"] = self.hogar_id

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "DELETE FROM articulos_compra WHERE hogar_id IN "
                "(SELECT id FROM hogares WHERE usuario_propietario_id = ?)",
                (self.usuario_id,),
            )
            db.execute("DELETE FROM hogares WHERE usuario_propietario_id = ?", (self.usuario_id,))
            articulo = db.execute(
                "SELECT id FROM articulos_personalizados WHERE nombre = ? AND usuario_propietario_id = ?",
                ("ZzzArticuloTestUnico", self.usuario_id),
            ).fetchone()
            if articulo:
                db.execute(
                    "DELETE FROM traducciones_productos WHERE articulo_personalizado_id = ?", (articulo["id"],)
                )
                db.execute("DELETE FROM articulos_personalizados WHERE id = ?", (articulo["id"],))
            # articulos_personalizados.usuario_propietario_id referencia
            # usuarios(id): hay que borrar la fila personalizada antes que el
            # usuario, o la FK lo impide.
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _esperar_traducciones(self, nombre, segundos=20):
        """La traduccion se hace en segundo plano (no bloquea la BD a los demas usuarios)."""
        import time
        limite = time.time() + segundos
        while time.time() < limite:
            with self.app.app_context():
                n = get_db().execute(
                    "SELECT COUNT(*) FROM traducciones_productos t, articulos_personalizados a "
                    "WHERE t.articulo_personalizado_id = a.id AND a.nombre = ? AND t.tipo = 'nombre'", (nombre,)
                ).fetchone()[0]
            if n >= 6:
                return
            time.sleep(0.1)

    def test_crear_articulo_personalizado_genera_traducciones(self):
        from unittest.mock import patch

        nombre = "ZzzArticuloTestUnico"
        # Traductor determinista y rapido: lo que se prueba es que el alta GUARDA las traducciones
        # (en segundo plano), no la calidad de Argos, que sin red tarda decenas de segundos.
        falsas = {i: f"{nombre} ({i})" for i in ("es", "gl", "en", "pt", "fr", "it", "de")}
        with patch("stockhogar.servicios.traduccion.traductor_auto.TraductorAutomatico.traducir_a_todos_idiomas",
                   return_value=falsas):
            resp = self.client.post(
                "/api/articulos",
                json={"nombre": nombre, "cantidad": 1},
            )
            self.assertIn(resp.status_code, (200, 201), resp.get_data(as_text=True))
            self._esperar_traducciones(nombre)

        with self.app.app_context():
            db = get_db()
            articulo = db.execute(
                "SELECT id FROM articulos_personalizados WHERE nombre = ? AND usuario_propietario_id = ?",
                (nombre, self.usuario_id),
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
