"""Toda clave de traduccion que usa el codigo existe en TODOS los idiomas.

Una clave que no esta en translations.json se pinta en crudo ("enviar_invitacion")
en la pantalla. Pasaba en el dialogo de compartir lista: dos claves usadas por
SelectorHogarPantallaCompleta.tsx no estaban definidas en ningun idioma.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRADUCCIONES = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
CARPETAS_FRONT = ("app", "components", "contexts", "hooks", "lib")
EXCLUIDAS = {"traduccionesBase.ts"}
RE_T = re.compile(r"""\bt\(\s*['"]([a-z0-9_à-ÿ]+)['"]""")
RE_TRADUCIR = re.compile(r"""\btraducir\(\s*['"]([a-z0-9_]+)['"]""")


def _usadas(rutas, regex, sufijos):
    claves = {}
    for carpeta in rutas:
        for f in (RAIZ / carpeta).rglob("*"):
            if f.suffix in sufijos and f.name not in EXCLUIDAS and "node_modules" not in f.parts and "__tests__" not in f.parts:
                for m in regex.finditer(f.read_text(encoding="utf-8")):
                    claves.setdefault(m.group(1), f.relative_to(RAIZ).as_posix())
    return claves


class ClavesUsadasTests(unittest.TestCase):
    def test_las_del_frontend_existen_en_todos_los_idiomas(self):
        usadas = _usadas(CARPETAS_FRONT, RE_T, {".ts", ".tsx"})
        self.assertGreater(len(usadas), 300)
        for idioma, textos in TRADUCCIONES.items():
            faltan = {k: f for k, f in usadas.items() if k not in textos}
            self.assertEqual(faltan, {}, f"{idioma}: claves usadas y sin traducir")

    def test_las_del_backend_existen_en_todos_los_idiomas(self):
        usadas = _usadas(("stockhogar",), RE_TRADUCIR, {".py"})
        for idioma, textos in TRADUCCIONES.items():
            faltan = {k: f for k, f in usadas.items() if k not in textos}
            self.assertEqual(faltan, {}, f"{idioma}: claves usadas y sin traducir")


if __name__ == "__main__":
    unittest.main()


class AvisosDelTicketTests(unittest.TestCase):
    """Los avisos de /api/tickets/analizar se traducen en el cliente por su "tipo"."""

    def test_cada_tipo_de_aviso_tiene_traduccion_con_sus_marcadores(self):
        pagina = (RAIZ / "app" / "dashboard" / "ticket" / "page.tsx").read_text(encoding="utf-8")
        esperado = {"muchos_sin_match": ("aviso_muchos_sin_match", "{n}"),
                    "confianza_baja": ("aviso_confianza_baja", None),
                    "descuadre": ("aviso_descuadre_ticket", "{suma}")}
        for tipo, (clave, marcador) in esperado.items():
            self.assertIn(f"{tipo}: '{clave}'", pagina)
            for idioma, textos in TRADUCCIONES.items():
                self.assertIn(clave, textos, f"{idioma}:{clave}")
                if marcador:
                    self.assertIn(marcador, textos[clave], f"{idioma}:{clave}")
        for idioma, textos in TRADUCCIONES.items():
            self.assertIn("{total}", textos["aviso_descuadre_ticket"], idioma)

    def test_el_descuadre_lleva_la_suma_y_el_total_para_el_texto(self):
        fuente = (RAIZ / "stockhogar" / "rutas" / "tickets.py").read_text(encoding="utf-8")
        self.assertIn('"suma": cuadre_ticket.get("suma_articulos")', fuente)
        self.assertIn('"total": cuadre_ticket.get("total_ticket")', fuente)
