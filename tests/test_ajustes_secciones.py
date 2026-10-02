"""Fase 6 del rediseno movil: epigrafe visible encima de cada grupo de Ajustes.

Los 6 grupos (tarjeta con filas e icono) ya existian; solo faltaba el titulo.
Cada grupo es una <section> etiquetada por su <h2>, y el epigrafe esta
traducido en los 7 idiomas.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = (RAIZ / "app" / "dashboard" / "settings" / "page.tsx").read_text(encoding="utf-8")
CLAVES = ["ajustes_grupo_cuenta", "ajustes_grupo_apariencia", "ajustes_grupo_datos",
          "ajustes_grupo_seguridad", "ajustes_grupo_legal", "zona_riesgo"]


class AjustesSeccionesTests(unittest.TestCase):
    def test_hay_seis_secciones_etiquetadas_y_en_orden(self):
        encontrados = re.findall(r"<h2 id=\"ajustes-grupo-\w+\"[^>]*>\{t\('(\w+)'\)\}</h2>", PAGINA)
        self.assertEqual(encontrados, CLAVES)

    def test_cada_seccion_apunta_a_su_epigrafe_y_se_cierra(self):
        ids = re.findall(r'<section aria-labelledby="(ajustes-grupo-\w+)"', PAGINA)
        self.assertEqual(len(ids), 6)
        for id_ in ids:
            with self.subTest(id=id_):
                self.assertIn(f'<h2 id="{id_}"', PAGINA)
        self.assertEqual(PAGINA.count("<section"), PAGINA.count("</section>"))

    def test_cada_grupo_sigue_siendo_una_tarjeta_con_filas(self):
        self.assertEqual(PAGINA.count("rounded-2xl border"), 6)

    def test_la_zona_de_riesgo_se_distingue_en_rojo(self):
        i = PAGINA.index('id="ajustes-grupo-zona"')
        self.assertIn("text-red-600", PAGINA[i:i + 200])

    def test_los_epigrafes_estan_traducidos_en_los_7_idiomas(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d), 7)
        for idioma, textos in d.items():
            for k in CLAVES:
                with self.subTest(idioma=idioma, clave=k):
                    self.assertTrue(textos.get(k, "").strip())

    def test_las_funciones_de_ajustes_siguen_ahi(self):
        # Red de seguridad: el envoltorio no debe haber comido ninguna fila.
        for clave in ("btn_exportar_mis_datos", "btn_cerrar_otras_sesiones", "titulo_eventos_seguridad",
                      "historial_consumo", "categorias_gasto", "cerrar_sesion_titulo",
                      "eliminar_cuenta_titulo", "enlace_aviso_legal", "enlace_privacidad",
                      "enlace_terminos", "enlace_cookies", "subtitulo_ajustes"):
            with self.subTest(clave=clave):
                self.assertIn(f"t('{clave}')", PAGINA)


if __name__ == "__main__":
    unittest.main()
