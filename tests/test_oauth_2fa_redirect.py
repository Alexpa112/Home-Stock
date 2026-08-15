"""Regresion: el callback OAuth de un usuario con 2FA debe llevar a una
pantalla que el frontend sirva de verdad.

Bug real: al forzar el 2FA en OAuth (M-5) los callbacks redirigian a
"/verificar-codigo-2fa", una ruta que NO existe en el App Router. El usuario
con 2FA que entraba por Google/Apple se comia un 404 y no podia terminar de
iniciar sesion; si ademas su cuenta se habia creado por OAuth (password_hash
NULL) tampoco tenia el login por contrasena como alternativa, asi que quedaba
fuera hasta editar la base de datos a mano.

El fallo nacio de que backend y frontend se desincronizaron sin que nada lo
detectara, asi que estos tests comprueban las dos mitades del contrato:
  1) el destino de la redireccion es una ruta que el App Router sirve, y
  2) el nombre del parametro que emite el backend es el que lee app/page.tsx.
Renombrarlo en un solo lado rompe la suite a proposito.
"""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

from stockhogar import create_app
from stockhogar.db import ahora, get_db
from stockhogar.rutas.oauth import PARAM_CODIGO_2FA

RAIZ = Path(__file__).resolve().parent.parent
EMAIL = "oauth.2fa@example.com"


def rutas_del_app_router():
    """Rutas estaticas que sirve el App Router, deducidas de los page.tsx.

    Se descartan los segmentos dinamicos ([token], [codigo]...) porque aqui
    solo se comprueban destinos fijos.
    """
    rutas = set()
    for page in (RAIZ / "app").rglob("page.tsx"):
        partes = page.relative_to(RAIZ / "app").parent.parts
        if any(p.startswith("[") for p in partes):
            continue
        rutas.add("/" + "/".join(partes) if partes else "/")
    return rutas


class OAuth2FARedirectTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM usuarios WHERE email = ?", (EMAIL,))
            cur = db.execute(
                "INSERT INTO usuarios (nombre_usuario, email, email_verificado, "
                "doble_factor_activo, fecha_creacion) VALUES (?, ?, 1, 1, ?)",
                (f"oauth2fa_{ahora()}", EMAIL, ahora()),
            )
            self.usuario_id = cur.lastrowid
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM oauth_accounts WHERE usuario_id = ?", (self.usuario_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (self.usuario_id,))
            db.commit()

    def _callback_google(self):
        """Ejecuta el callback de Google para el usuario con 2FA y devuelve la respuesta."""
        respuesta_token = MagicMock()
        respuesta_token.raise_for_status.return_value = None
        respuesta_token.json.return_value = {"access_token": "token-falso"}

        respuesta_usuario = MagicMock()
        respuesta_usuario.raise_for_status.return_value = None
        respuesta_usuario.json.return_value = {
            "email": EMAIL,
            "verified_email": True,
            "name": "Usuario OAuth",
            "id": "google-id-2fa",
            "picture": None,
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "estado-de-prueba"

        # El envio del codigo se mockea: aqui interesa a donde redirige, no el correo.
        with patch("stockhogar.rutas.oauth.requests.post", return_value=respuesta_token), \
             patch("stockhogar.rutas.oauth.requests.get", return_value=respuesta_usuario), \
             patch("stockhogar.servicios.email_service.EmailService.enviar_codigo_verificacion",
                   return_value=True):
            return self.client.get(
                "/auth/google/callback?code=codigo-falso&state=estado-de-prueba"
            )

    def test_redirige_a_una_ruta_que_el_frontend_sirve(self):
        respuesta = self._callback_google()

        self.assertEqual(respuesta.status_code, 302)
        destino = urlparse(respuesta.headers["Location"]).path.rstrip("/") or "/"
        self.assertIn(
            destino, rutas_del_app_router(),
            f"el callback redirige a {destino!r}, que no es ninguna pagina del App Router: "
            "el usuario con 2FA se comeria un 404 y no podria iniciar sesion",
        )

    def test_no_crea_sesion_todavia_sino_que_deja_el_2fa_pendiente(self):
        self._callback_google()

        with self.client.session_transaction() as sess:
            self.assertIsNone(
                sess.get("usuario"),
                "la sesion no debe quedar creada antes de verificar el codigo",
            )
            self.assertEqual(sess.get("pendiente_2fa_usuario_id"), self.usuario_id)

    def test_el_parametro_emitido_es_el_que_lee_el_frontend(self):
        respuesta = self._callback_google()
        query = parse_qs(urlparse(respuesta.headers["Location"]).query)

        self.assertIn(
            PARAM_CODIGO_2FA, query,
            "el backend debe marcar en la URL que toca pedir el codigo",
        )

        pagina_login = (RAIZ / "app" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn(
            f"'{PARAM_CODIGO_2FA}'", pagina_login,
            f"app/page.tsx no lee el parametro {PARAM_CODIGO_2FA!r} que emite el backend: "
            "si se renombra en un lado hay que renombrarlo en el otro",
        )


if __name__ == "__main__":
    unittest.main()
