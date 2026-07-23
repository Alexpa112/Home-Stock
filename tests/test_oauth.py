"""Tests de regresion para el flujo OAuth (login con Google/Apple).

Cubre el bug donde el callback solo guardaba session["usuario_id"] pero el
guardian global (exigir_sesion en stockhogar/__init__.py) tambien exige
session["usuario"], dejando a cualquier usuario que entrase por OAuth
atrapado en un bucle de redireccion a /login pese a tener una sesion
"valida" en la cookie.
"""
import unittest
from unittest.mock import patch, MagicMock

from stockhogar import create_app
from stockhogar.db import get_db


class OAuthGoogleCallbackTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM oauth_accounts WHERE email = ?", ("nuevo.oauth@example.com",))
            db.execute("DELETE FROM usuarios WHERE email = ?", ("nuevo.oauth@example.com",))
            db.commit()

    def _iniciar_state(self):
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "estado-de-prueba"

    def _mock_respuestas_google(self, email):
        respuesta_token = MagicMock()
        respuesta_token.raise_for_status.return_value = None
        respuesta_token.json.return_value = {"access_token": "token-falso"}

        respuesta_usuario = MagicMock()
        respuesta_usuario.raise_for_status.return_value = None
        respuesta_usuario.json.return_value = {
            "email": email,
            "verified_email": True,
            "name": "Usuario OAuth",
            "id": "google-id-123",
            "picture": None,
        }
        return respuesta_token, respuesta_usuario

    @patch("stockhogar.rutas.oauth.requests.get")
    @patch("stockhogar.rutas.oauth.requests.post")
    def test_login_google_deja_sesion_autenticada(self, mock_post, mock_get):
        """Tras el callback de Google, una peticion API posterior no debe dar 401."""
        email = "nuevo.oauth@example.com"
        mock_post.return_value, mock_get.return_value = self._mock_respuestas_google(email)

        self._iniciar_state()
        respuesta = self.client.get(
            "/auth/google/callback?code=codigo-falso&state=estado-de-prueba"
        )
        self.assertEqual(respuesta.status_code, 302)

        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("usuario"), "session['usuario'] debe quedar rellena tras el login OAuth")
            self.assertIsNotNone(sess.get("usuario_id"))

        respuesta_api = self.client.get("/api/listas")
        self.assertNotEqual(
            respuesta_api.status_code, 401,
            "una sesion creada por OAuth debe superar el guardian exigir_sesion",
        )


if __name__ == "__main__":
    unittest.main()
