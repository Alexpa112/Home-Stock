"""Tests de rotacion de la clave de firma de sesiones (S-18).

IMPORTANTE: seguridad.py cachea la clave activa en variables de MODULO,
leidas del fichero real data/secret.json al importarse. Estos tests
redirigen CLAVES_PATH a un fichero temporal antes de cada prueba y
restauran el estado real del modulo al terminar, para no tocar nunca el
secret.json real de la instalacion ni dejar corrompido el estado en
memoria para el resto de la suite (otros tests que hacen create_app()
leen seguridad.FLASK_SECRET_KEY).
"""
import json
import unittest

from itsdangerous import URLSafeTimedSerializer

from stockhogar import seguridad


class RotacionSecretTests(unittest.TestCase):
    def setUp(self):
        self._claves_originales = seguridad._claves
        self._flask_secret_key_original = seguridad.FLASK_SECRET_KEY
        self._previas_originales = seguridad.CLAVES_VERIFICACION_PREVIAS
        self._claves_path_original = seguridad.CLAVES_PATH

    def tearDown(self):
        seguridad._claves = self._claves_originales
        seguridad.FLASK_SECRET_KEY = self._flask_secret_key_original
        seguridad.CLAVES_VERIFICACION_PREVIAS = self._previas_originales
        seguridad.CLAVES_PATH = self._claves_path_original

    def test_formato_antiguo_se_migra_sin_cambiar_la_clave_activa(self, ):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "secret.json"
            ruta.write_text(json.dumps({"flask_secret_key": "clave-vieja-formato"}), encoding="utf-8")
            seguridad.CLAVES_PATH = ruta

            claves = seguridad._cargar_claves()

            self.assertEqual(claves["flask_secret_key"], "clave-vieja-formato")
            self.assertEqual(claves["claves_verificacion_previas"], [])

    def test_rotar_clave_conserva_la_anterior_como_verificacion(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "secret.json"
            seguridad.CLAVES_PATH = ruta
            seguridad._claves = {"flask_secret_key": "clave-1", "claves_verificacion_previas": []}
            seguridad.FLASK_SECRET_KEY = "clave-1"
            seguridad.CLAVES_VERIFICACION_PREVIAS = []

            nueva = seguridad.rotar_clave()

            self.assertNotEqual(nueva, "clave-1")
            self.assertEqual(seguridad.FLASK_SECRET_KEY, nueva)
            self.assertIn("clave-1", seguridad.CLAVES_VERIFICACION_PREVIAS)

            persistido = json.loads(ruta.read_text(encoding="utf-8"))
            self.assertEqual(persistido["flask_secret_key"], nueva)
            self.assertIn("clave-1", persistido["claves_verificacion_previas"])

    def test_rotar_clave_no_acumula_mas_de_max_claves_verificacion(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "secret.json"
            seguridad.CLAVES_PATH = ruta
            seguridad._claves = {"flask_secret_key": "clave-0", "claves_verificacion_previas": []}
            seguridad.FLASK_SECRET_KEY = "clave-0"
            seguridad.CLAVES_VERIFICACION_PREVIAS = []

            for _ in range(seguridad.MAX_CLAVES_VERIFICACION + 3):
                seguridad.rotar_clave()

            self.assertLessEqual(len(seguridad.CLAVES_VERIFICACION_PREVIAS), seguridad.MAX_CLAVES_VERIFICACION)

    def test_serializer_con_secret_keys_multiples_verifica_firma_de_clave_antigua(self):
        """Prueba de la propiedad de itsdangerous que sostiene el mecanismo
        de rotacion aplicado en stockhogar/__init__.py::get_signing_serializer:
        una firma hecha con una clave sigue verificandose si esa clave se
        incluye (aunque no sea la primera) en secret_keys."""
        firmado_con_vieja = URLSafeTimedSerializer("clave-vieja", salt="cookie-session")
        token = firmado_con_vieja.dumps({"usuario_id": 1})

        verificador = URLSafeTimedSerializer("clave-nueva", salt="cookie-session")
        verificador.secret_keys = ["clave-nueva", "clave-vieja"]

        self.assertEqual(verificador.loads(token), {"usuario_id": 1})


if __name__ == "__main__":
    unittest.main()
