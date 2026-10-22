"""Rendimiento en la Raspberry Pi: diccionario con ETag y ajustes de SQLite."""
import unittest

from stockhogar import create_app
from stockhogar.db import get_db


class DiccionarioConEtagTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_la_respuesta_lleva_etag_y_revalida(self):
        r = self.client.get("/api/idiomas/todos/en")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers.get("ETag"))
        self.assertEqual(r.headers.get("Cache-Control"), "private, no-cache")
        self.assertIn("traducciones", r.get_json())

    def test_con_if_none_match_responde_304_sin_cuerpo(self):
        primera = self.client.get("/api/idiomas/todos/es")
        segunda = self.client.get("/api/idiomas/todos/es", headers={"If-None-Match": primera.headers["ETag"]})
        self.assertEqual(segunda.status_code, 304)
        self.assertEqual(segunda.get_data(), b"")

    def test_un_idioma_distinto_tiene_otro_etag(self):
        es = self.client.get("/api/idiomas/todos/es").headers["ETag"]
        en = self.client.get("/api/idiomas/todos/en").headers["ETag"]
        self.assertNotEqual(es, en)

    def test_un_idioma_no_soportado_sigue_siendo_400(self):
        self.assertEqual(self.client.get("/api/idiomas/todos/xx").status_code, 400)


class AjustesDeSqliteTests(unittest.TestCase):
    def test_cada_conexion_lleva_los_pragmas_de_rendimiento(self):
        app = create_app()
        with app.app_context():
            db = get_db()
            self.assertEqual(db.execute("PRAGMA cache_size").fetchone()[0], -8000)
            self.assertEqual(db.execute("PRAGMA temp_store").fetchone()[0], 2)  # 2 = MEMORY
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
            self.assertEqual(db.execute("PRAGMA synchronous").fetchone()[0], 1)  # 1 = NORMAL


if __name__ == "__main__":
    unittest.main()
