"""Toda pantalla del dashboard debe poder abrirse desde el movil.

Antes del rediseno movil, Recetas no aparecia en la barra inferior y el
Historial solo se alcanzaba entrando en Ajustes: dos funciones sin acceso
directo. Este test lee `app/dashboard/layout.tsx` y falla si aparece una
pagina nueva (o una existente queda huerfana) que no este ni en las pestanas
de movil ni en la lista explicita de destinos secundarios de abajo.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LAYOUT = RAIZ / "app" / "dashboard" / "layout.tsx"
DASHBOARD = RAIZ / "app" / "dashboard"

# Destinos que NO estan en la barra inferior pero si son alcanzables en movil
# por un camino declarado. Cada alta aqui debe justificarse. Recetas e Historial
# llegan por el grupo "Ir a" del menu de acciones (ver MenuAccionesIrATests).
DESTINOS_SECUNDARIOS = {
    "/dashboard/recetas": "grupo \"Ir a\" del menu de acciones",
    "/dashboard/historial": "grupo \"Ir a\" del menu de acciones",
    "/dashboard/gastos/categorias": "enlace en Ajustes y en el formulario de gasto",
}


def _hrefs_de(bloque):
    return re.findall(r"href:\s*'([^']+)'", bloque)


def _bloque(fuente, nombre):
    """Texto del array `const <nombre> = [ ... ]` del layout."""
    m = re.search(rf"const {nombre}\s*=\s*\[(.*?)\n\s*\]", fuente, re.S)
    assert m, f"No se encontro `{nombre}` en {LAYOUT}"
    return m.group(1)


def _rutas_de_paginas():
    rutas = set()
    for p in DASHBOARD.rglob("page.tsx"):
        rel = p.parent.relative_to(RAIZ / "app").as_posix()
        rutas.add("/" + rel)
    return rutas


class NavegacionMovilTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fuente = LAYOUT.read_text(encoding="utf-8")
        cls.tabs = set(_hrefs_de(_bloque(fuente, "tabItems")))
        cls.paginas = _rutas_de_paginas()

    def test_se_leen_las_pestanas_y_las_paginas(self):
        self.assertGreaterEqual(len(self.tabs), 5)
        self.assertIn("/dashboard", self.paginas)

    def test_toda_pagina_es_alcanzable_desde_movil(self):
        inalcanzables = sorted(
            r for r in self.paginas
            if r not in self.tabs and r not in DESTINOS_SECUNDARIOS
        )
        self.assertEqual(
            inalcanzables, [],
            "Paginas sin acceso en movil (ni pestana ni destino secundario "
            f"declarado): {inalcanzables}",
        )

    def test_los_destinos_secundarios_existen(self):
        # Evita que la lista de excepciones acumule rutas ya borradas.
        fantasma = sorted(set(DESTINOS_SECUNDARIOS) - self.paginas)
        self.assertEqual(fantasma, [], f"Destinos declarados que ya no existen: {fantasma}")

    def test_las_pestanas_apuntan_a_paginas_reales(self):
        rotas = sorted(self.tabs - self.paginas)
        self.assertEqual(rotas, [], f"Pestanas hacia rutas inexistentes: {rotas}")


PANTALLAS = ["page.tsx", "shopping/page.tsx", "gastos/page.tsx", "ticket/page.tsx",
             "historial/page.tsx", "recetas/page.tsx"]


class MenuAccionesIrATests(unittest.TestCase):
    """Fase 1: Recetas e Historial se alcanzan desde el menu de las 6 pantallas."""

    def test_las_seis_pantallas_usan_el_grupo_ir_a(self):
        for rel in PANTALLAS:
            with self.subTest(pantalla=rel):
                src = (DASHBOARD / rel).read_text(encoding="utf-8")
                self.assertIn("accionesIrA(t", src)
                self.assertIn("<MenuAcciones", src)

    def test_el_grupo_ir_a_enlaza_a_recetas_e_historial(self):
        src = (RAIZ / "components" / "dashboard" / "accionesIrA.tsx").read_text(encoding="utf-8")
        self.assertIn("href: '/dashboard/recetas'", src)
        self.assertIn("href: '/dashboard/historial'", src)

    def test_una_accion_con_href_es_un_enlace_y_no_un_boton(self):
        src = (RAIZ / "components" / "dashboard" / "MenuAcciones.tsx").read_text(encoding="utf-8")
        self.assertIn("accion.href ?", src)
        self.assertIn("<Link href={accion.href}", src)

    def test_el_panel_del_menu_no_se_sale_por_la_izquierda(self):
        # En Stock y Compra el boton esta junto a "Anadir" (a media pantalla):
        # anclar el panel de 224 px por la derecha lo recortaba.
        src = (RAIZ / "components" / "dashboard" / "MenuAcciones.tsx").read_text(encoding="utf-8")
        self.assertIn("alinearIzquierda", src)
        self.assertIn("getBoundingClientRect().right", src)

    def test_gastos_no_recibe_boton_flotante_duplicado(self):
        src = (DASHBOARD / "layout.tsx").read_text(encoding="utf-8")
        self.assertIn("pathname === '/dashboard' || pathname === '/dashboard/shopping'", src)
        self.assertNotIn("'/dashboard/gastos'", src.split("dispararAnadir}")[0].split("Botón flotante")[-1])

    def test_el_boton_flotante_tiene_a_quien_avisar(self):
        for rel in ("page.tsx", "shopping/page.tsx"):
            with self.subTest(pantalla=rel):
                src = (DASHBOARD / rel).read_text(encoding="utf-8")
                self.assertIn("useAccionAnadir(", src)


if __name__ == "__main__":
    unittest.main()
