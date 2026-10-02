"""Fase 7 del rediseno movil: ni un emoji en la interfaz.

Los iconos de la app son todos de trazo (lucide). Un emoji se pinta distinto en
cada sistema, no hereda el color del tema ni se adapta al modo oscuro. Se mira
el fuente de la interfaz y el texto de las traducciones que se muestran.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿⌀-⏿⊞ℹ️‍]")

# Textos con emoji que NO son interfaz de la app y se dejan a proposito:
#  - app_name: mensaje de la API al cambiar de idioma, no se pinta en pantalla.
#  - whatsapp_mensaje_compartir_hogar: texto que se envia FUERA de la app.
#  - log_*: salida de la pagina tecnica /diagnose.
PERMITIDAS = {"app_name", "whatsapp_mensaje_compartir_hogar"}


def _fuentes_de_interfaz():
    for carpeta in ("app", "components"):
        yield from sorted((RAIZ / carpeta).rglob("*.tsx"))


class SinEmojiEnInterfazTests(unittest.TestCase):
    def test_el_codigo_de_la_interfaz_no_contiene_emoji(self):
        for ruta in _fuentes_de_interfaz():
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                if linea.strip().startswith(("//", "{/*", "*")):
                    continue
                with self.subTest(archivo=str(ruta.relative_to(RAIZ)), linea=n):
                    self.assertIsNone(EMOJI.search(linea), linea.strip()[:80])

    def test_las_traducciones_visibles_no_contienen_emoji(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        for idioma, textos in d.items():
            for clave, texto in textos.items():
                if clave in PERMITIDAS or clave.startswith("log_"):
                    continue
                with self.subTest(idioma=idioma, clave=clave):
                    self.assertIsNone(EMOJI.search(texto), texto)

    def test_la_lista_de_permitidas_no_se_pudre(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))["es"]
        for clave in PERMITIDAS:
            self.assertIn(clave, d)


if __name__ == "__main__":
    unittest.main()
