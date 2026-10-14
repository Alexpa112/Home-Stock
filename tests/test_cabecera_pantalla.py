"""Fase 2 del rediseno movil: una unica cabecera para todas las pantallas.

La barra superior fija de 48 px del layout (logo + selector de hogar) se repetia
en cada pantalla y, con el titulo y el subtitulo de cada pagina, se comia 474 px
antes del primer producto. Ahora el titulo, el chip de hogar y el menu van en
`CabeceraPantalla`, y el subtitulo y el boton "Anadir" solo en escritorio.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DASHBOARD = RAIZ / "app" / "dashboard"
PAGINAS = ["page.tsx", "shopping/page.tsx", "gastos/page.tsx", "ticket/page.tsx",
           "historial/page.tsx", "recetas/page.tsx", "settings/page.tsx"]


class CabeceraPantallaTests(unittest.TestCase):
    def test_las_siete_paginas_usan_la_cabecera_comun(self):
        for rel in PAGINAS:
            with self.subTest(pagina=rel):
                src = (DASHBOARD / rel).read_text(encoding="utf-8")
                self.assertIn("<CabeceraPantalla", src)

    def test_no_queda_ningun_h1_suelto_en_esas_paginas(self):
        for rel in PAGINAS:
            with self.subTest(pagina=rel):
                src = (DASHBOARD / rel).read_text(encoding="utf-8")
                self.assertNotIn("<h1", src, "el titulo debe salir de CabeceraPantalla")

    def test_el_layout_ya_no_pinta_la_barra_superior_movil(self):
        src = (DASHBOARD / "layout.tsx").read_text(encoding="utf-8")
        self.assertNotIn("<header", src)
        self.assertIn("useAbrirSelectorHogar", src)  # el chip sigue abriendo el selector

    def test_el_chip_de_hogar_solo_es_movil_y_tiene_etiqueta(self):
        src = (RAIZ / "components" / "dashboard" / "CabeceraPantalla.tsx").read_text(encoding="utf-8")
        self.assertIn("lg:hidden", src)
        self.assertIn("aria-label={t('cambiar_hogar')}", src)
        self.assertIn("min-h-[44px]", src)

    def test_el_subtitulo_solo_se_ve_en_escritorio(self):
        src = (RAIZ / "components" / "dashboard" / "CabeceraPantalla.tsx").read_text(encoding="utf-8")
        self.assertRegex(src, r'hidden lg:block[^"]*"[^>]*>\{subtitulo\}')

    def test_stock_y_compra_conservan_anadir_en_escritorio(self):
        # En movil lo hace el boton flotante; sin esto, escritorio perderia el alta.
        for rel in ("page.tsx", "shopping/page.tsx"):
            with self.subTest(pagina=rel):
                src = (DASHBOARD / rel).read_text(encoding="utf-8")
                self.assertRegex(src, r'className="hidden lg:flex btn-primary')

    def test_el_titulo_nunca_se_parte_letra_a_letra(self):
        # Regresion real: en Recetas, boton + chip + menu aplastaban el titulo
        # hasta partirlo en vertical. Nada de break-words/min-w-0 sobre el titulo
        # y el boton de Recetas es solo icono en movil.
        cab = (RAIZ / "components" / "dashboard" / "CabeceraPantalla.tsx").read_text(encoding="utf-8")
        self.assertNotIn("break-words", cab)
        rec = (DASHBOARD / "recetas" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn('<span className="hidden sm:inline">{t(\'nueva_receta\')}</span>', rec)
        self.assertIn("aria-label={t('nueva_receta')}", rec)

    def test_las_claves_de_subtitulo_siguen_existiendo(self):
        # Se siguen usando (en escritorio); la fase 7 decide si alguna sobra.
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        for idioma, textos in d.items():
            for k in ("subtitulo_stock", "subtitulo_ajustes", "subtitulo_historial",
                      "subtitulo_escanear_ticket", "cambiar_hogar"):
                with self.subTest(idioma=idioma, clave=k):
                    self.assertIn(k, textos)


if __name__ == "__main__":
    unittest.main()
