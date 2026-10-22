"""Regresiones de la segunda ronda de pruebas en produccion (2026-10-22).

No hay entorno de pruebas de React (jest solo cubre lib/), asi que se atan
leyendo el fuente, como hacen los demas tests de tests/frontend.

1. Error de hidratacion #418: las pantallas leian lib/dataCache (localStorage)
   al inicializar el estado; el servidor no lo tiene y el HTML no coincidia.
2. La tarjeta de stock ofrecia "Añadir a la compra" aunque el producto ya
   estaba en la lista (el backend ahora envia `en_lista_compra`).
3. El grafico de columnas con un solo dato pintaba un bloque de ancho completo.
4. Los eventos de "Actividad de tu cuenta" salian como identificador crudo
   ("registro").
5. "1 Items" / "1 Artículos": faltaba el singular en el contador de stock.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
TRADUCCIONES = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))


def _fuentes(*carpetas):
    for carpeta in carpetas:
        for f in (RAIZ / carpeta).rglob("*.tsx"):
            if "node_modules" not in f.parts:
                yield f, f.read_text(encoding="utf-8")


class HidratacionTests(unittest.TestCase):
    def test_ninguna_pantalla_lee_la_cache_al_inicializar_el_estado(self):
        # Argumento de useState(...) (con un nivel de parentesis anidado) que contenga getCached
        patron = re.compile(r"useState(?:<[^()]*>)?\((?:[^()]|\([^()]*\))*?getCached[<(]")
        culpables = [f.relative_to(RAIZ).as_posix() for f, src in _fuentes("app", "components") if patron.search(src)]
        self.assertEqual(culpables, [], "getCached dentro de useState provoca el error de hidratacion #418")

    def test_las_pantallas_que_usan_la_cache_la_cargan_tras_montar(self):
        usan = [
            (f, src) for f, src in _fuentes("app", "components")
            if re.search(r"getCached[<(]", src) and "lib/dataCache" in src
        ]
        self.assertGreaterEqual(len(usan), 4)
        for f, src in usan:
            self.assertIn("useCacheTrasMontar", src, f.relative_to(RAIZ).as_posix())

    def test_el_hook_usa_layout_effect_en_el_navegador(self):
        hook = (RAIZ / "lib" / "useCacheTrasMontar.ts").read_text(encoding="utf-8")
        self.assertIn("useLayoutEffect", hook)
        self.assertIn("typeof window === 'undefined'", hook)


class BotonAnadirACompraTests(unittest.TestCase):
    def test_el_stock_no_ofrece_anadir_lo_que_ya_esta_en_la_lista(self):
        src = (RAIZ / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("en_lista_compra", src)
        self.assertIn("yaEnLista(item)", src)
        # Las dos vistas (recuadro y lista) deshabilitan el boton cuando ya esta
        self.assertGreaterEqual(src.count("disabled={añadiendoIds.has(item.id) || yaEnLista(item)}"), 2)
        self.assertIn("!i.en_lista_compra", src, "\"añadir todos\" no debe repetir los que ya estan")


class GraficoColumnasTests(unittest.TestCase):
    def test_usa_la_geometria_con_columnas_minimas(self):
        src = (RAIZ / "components" / "dashboard" / "GraficoColumnas.tsx").read_text(encoding="utf-8")
        self.assertIn("geometriaColumnas(datos.length)", src)
        self.assertNotIn("100 / datos.length", src)


class EventosDeCuentaTests(unittest.TestCase):
    def _eventos_backend(self):
        eventos = set()
        for f in (RAIZ / "stockhogar").rglob("*.py"):
            eventos.update(re.findall(r'registrar\([^,()]+,\s*"([a-z_0-9]+)"', f.read_text(encoding="utf-8")))
        return eventos

    def test_todo_evento_de_auditoria_tiene_traduccion_en_todos_los_idiomas(self):
        eventos = self._eventos_backend()
        self.assertGreaterEqual(len(eventos), 8)
        for idioma, textos in TRADUCCIONES.items():
            faltan = [e for e in eventos if f"evento_{e}" not in textos]
            self.assertEqual(faltan, [], f"{idioma}: eventos sin traducir")

    def test_ajustes_traduce_los_eventos_en_vez_de_mostrar_el_identificador(self):
        src = (RAIZ / "app" / "dashboard" / "settings" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("etiquetasEvento[ev.evento] ?? ev.evento", src)
        for evento in self._eventos_backend():
            self.assertIn(f"t('evento_{evento}')", src, evento)


class SingularDelContadorTests(unittest.TestCase):
    def test_existe_el_singular_en_todos_los_idiomas(self):
        for idioma, textos in TRADUCCIONES.items():
            self.assertTrue(textos.get("articulo_singular"), idioma)
            if idioma != "de":  # en aleman singular y plural coinciden ("Artikel")
                self.assertNotEqual(textos["articulo_singular"], textos["articulos"], f"{idioma}: singular == plural")

    def test_el_contador_usa_el_singular_con_un_solo_articulo(self):
        src = (RAIZ / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("stats.totalItems === 1 ? t('articulo_singular') : t('articulos')", src)


if __name__ == "__main__":
    unittest.main()
