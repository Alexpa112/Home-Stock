"""El login con Apple se retiro: no debe quedar rastro ni volver por descuido.

Decision del proyecto: no se ofrece "Continuar con Apple". El flujo nunca llego
a funcionar (el POST del callback moria en la comprobacion CSRF y la cookie
`SameSite=Lax` no viajaba en una peticion cross-site), y mantenerlo suponia
credenciales de Apple en el .env y a Apple Inc. declarada como encargada del
tratamiento en la politica de privacidad.

Estos tests fijan la retirada por las tres puntas que importan:
  * que no queden rutas /auth/apple servidas,
  * que la pantalla de login no ofrezca el boton, y
  * que la politica de privacidad no siga nombrando a Apple como tercero al
    que se envian datos (REGLA 11 del CLAUDE.md).
"""
import unittest
from pathlib import Path

from stockhogar import create_app

RAIZ = Path(__file__).resolve().parent.parent


class SinLoginAppleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    def test_no_hay_ninguna_ruta_de_apple(self):
        rutas = [str(r) for r in self.app.url_map.iter_rules()]
        de_apple = [r for r in rutas if "apple" in r.lower()]
        self.assertEqual(de_apple, [], f"siguen registradas rutas de Apple: {de_apple}")

    def test_las_urls_de_apple_no_llevan_a_apple(self):
        """No se comprueba un 404 exacto: el guardian global (exigir_sesion)
        redirige a / cualquier ruta no-API sin sesion, asi que una URL retirada
        responde 302. Lo que importa es que ya no exista la ruta (arriba) y que
        nada mande al usuario a appleid.apple.com."""
        cliente = self.app.test_client()
        for ruta, metodo in (("/auth/apple", "GET"), ("/auth/apple/callback", "POST")):
            with self.subTest(ruta=ruta):
                respuesta = cliente.open(ruta, method=metodo)
                self.assertNotIn(
                    "appleid.apple.com", respuesta.headers.get("Location", ""),
                    f"{ruta} sigue iniciando el flujo de Apple",
                )
                self.assertLess(respuesta.status_code, 500, respuesta.status)

    def test_el_backend_no_menciona_credenciales_de_apple(self):
        for modulo in ("stockhogar/config.py", "stockhogar/rutas/oauth.py",
                       "stockhogar/rutas/auth.py"):
            with self.subTest(modulo=modulo):
                texto = (RAIZ / modulo).read_text(encoding="utf-8").lower()
                self.assertNotIn("apple", texto, f"{modulo} sigue nombrando Apple")

    def test_el_env_de_ejemplo_no_pide_credenciales_de_apple(self):
        texto = (RAIZ / ".env.example").read_text(encoding="utf-8").lower()
        self.assertNotIn("apple", texto)

    def test_la_pantalla_de_login_no_ofrece_apple(self):
        texto = (RAIZ / "app" / "page.tsx").read_text(encoding="utf-8").lower()
        self.assertNotIn(
            "apple", texto,
            "el boton 'Continuar con Apple' debe desaparecer del login y del registro",
        )

    def test_no_quedan_traducciones_de_apple(self):
        import json
        traducciones = json.loads(
            (RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8")
        )
        for idioma, entradas in traducciones.items():
            with self.subTest(idioma=idioma):
                sobran = [c for c in entradas if "apple" in c.lower()]
                self.assertEqual(sobran, [], f"{idioma} conserva claves de Apple: {sobran}")

    def test_la_politica_de_privacidad_no_declara_a_apple(self):
        """REGLA 11: si ya no se envian datos a Apple, no puede seguir declarada."""
        texto = (RAIZ / "app" / "legal" / "privacidad" / "page.tsx").read_text(encoding="utf-8")
        self.assertNotIn(
            "Apple", texto,
            "la politica de privacidad no debe seguir nombrando a Apple como "
            "tercero al que se ceden datos",
        )


if __name__ == "__main__":
    unittest.main()
