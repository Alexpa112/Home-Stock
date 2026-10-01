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
# por un camino declarado. Cada alta aqui debe justificarse; la fase 1 del
# rediseno anade /recetas y /historial (menu de acciones de cada pantalla).
DESTINOS_SECUNDARIOS = {
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

    # FASE 0: rojo conocido (Recetas e Historial sin acceso). La fase 1 anade el
    # grupo "Ir a" al menu de acciones y DEBE quitar esta marca.
    @unittest.expectedFailure
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


if __name__ == "__main__":
    unittest.main()
