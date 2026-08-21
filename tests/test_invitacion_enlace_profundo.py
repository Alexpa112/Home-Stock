"""El enlace de invitacion debe sobrevivir al login.

Quien recibe una invitacion por WhatsApp normalmente NO tiene la sesion abierta
en ese navegador. El contrato entre las dos mitades es:

  1. app/aceptar-invitacion/[codigo] llama al backend; si responde "no has
     iniciado sesion", manda a `/?next=/aceptar-invitacion/<codigo>`.
  2. app/page.tsx lee ese `next` y, tras entrar, va alli en vez de a /dashboard.

Ninguna de las dos mitades estaba cubierta, y es exactamente la clase de
contrato que ya se rompio una vez en este proyecto (el callback de OAuth con
2FA apuntaba a una ruta que el frontend no servia). Estos tests leen los dos
ficheros para que renombrar el parametro en un lado rompa la suite.

Se comprueba tambien la proteccion contra redirecciones abiertas: `next` debe
ser una ruta relativa, no una URL a otro dominio.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA_INVITACION = RAIZ / "app" / "aceptar-invitacion" / "[codigo]" / "page.tsx"
PAGINA_LOGIN = RAIZ / "app" / "page.tsx"


class EnlaceProfundoInvitacionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invitacion = PAGINA_INVITACION.read_text(encoding="utf-8")
        cls.login = PAGINA_LOGIN.read_text(encoding="utf-8")

    def test_la_invitacion_manda_al_login_conservando_el_destino(self):
        self.assertIn(
            "next=/aceptar-invitacion/", self.invitacion,
            "sin conservar el destino, quien abre la invitacion sin sesion "
            "entra y aterriza en el dashboard: la invitacion se pierde",
        )

    def test_el_login_lee_el_parametro_next(self):
        self.assertIn(
            "searchParams.get('next')", self.login,
            "app/page.tsx debe leer el mismo parametro que emite la pagina de "
            "invitacion; si se renombra en un lado hay que renombrarlo en el otro",
        )

    def test_el_login_redirige_al_destino_y_no_siempre_al_dashboard(self):
        self.assertIn(
            "const destino", self.login,
            "el login debe resolver un destino a partir de `next`",
        )
        self.assertRegex(
            self.login, r"window\.location\.href\s*=\s*destino",
            "tras iniciar sesion hay que ir al destino calculado",
        )

    def test_next_solo_admite_rutas_relativas(self):
        """Proteccion contra redirecciones abiertas (M-12)."""
        self.assertRegex(
            self.login, r"startsWith\('/'\)",
            "`next` debe empezar por / para no poder saltar a otro dominio",
        )
        self.assertIn(
            "://", self.login,
            "debe rechazarse un `next` que traiga esquema (https://malo.example)",
        )

    def test_el_destino_por_defecto_es_el_dashboard(self):
        self.assertRegex(
            self.login, r"searchParams\.get\('next'\)\s*\|\|\s*'/dashboard'",
            "sin `next`, el login debe seguir llevando al dashboard",
        )


if __name__ == "__main__":
    unittest.main()
