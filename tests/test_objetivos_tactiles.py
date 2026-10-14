"""Fase 7 del rediseno movil: todo control tactil mide al menos 44 px.

Recorre los <button>, <Link> y <a> de la interfaz y falla si alguno declara una
clase de Tailwind por debajo de 44 px (w/h-6..10, min-h/min-w 3x-40) sin otra
que lo compense. Es una comprobacion de fuente; el tamano real se mide en
Chromium aparte.

EXCEPCIONES DECLARADAS (cada una con su motivo y su comprobacion de que sigue
existiendo, para que la lista no se pudra):
  * Recuadros de la vista Grid de Stock: tres columnas de ~110 px no admiten
    tres botones de 44 px. Solucion pendiente de decision (columnas o fila).
  * Menu lateral de escritorio (lg): puntero preciso, no tactil.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PEQUENO = re.compile(r"(?<![\w-])(?:w-(?:6|7|8|9|10)|h-(?:6|7|8|9|10)|min-h-\[(?:3\d|40)px\]|min-w-\[(?:3\d|40)px\])(?![\w\[-])")
COMPENSA = re.compile(r"min-h-\[44px\]|(?<![\w-])h-1[1-9](?![\w-])|(?<![\w-])w-1[1-9](?![\w-])")
ETIQUETA = re.compile(r"<(button|Link|a)\b((?:=>|[^>])*?)>", re.S)
CLASES = re.compile(r'className=(?:"([^"]*)"|\{`([^`]*)`\})')


def _clases(cuerpo):
    return " ".join((a or b) for a, b in CLASES.findall(cuerpo))


def _region(texto, inicio, fin):
    i = texto.index(inicio)
    return i, texto.index(fin, i)


def _ofensores():
    salida = []
    for carpeta in ("app", "components"):
        for ruta in sorted((RAIZ / carpeta).rglob("*.tsx")):
            texto = ruta.read_text(encoding="utf-8")
            rel = ruta.relative_to(RAIZ).as_posix()
            grid = None
            if rel == "app/dashboard/page.tsx":
                grid = _region(texto, "const renderProductoGrid", "const renderProductoLista")
            for m in ETIQUETA.finditer(texto):
                cls = _clases(m.group(2))
                if not PEQUENO.search(cls) or COMPENSA.search(cls):
                    continue
                if grid and grid[0] <= m.start() <= grid[1]:
                    continue  # excepcion: recuadros Grid de Stock
                if rel == "app/dashboard/layout.tsx" and "group flex items-center gap-3 px-3" in cls:
                    continue  # excepcion: menu lateral de escritorio
                salida.append(f"{rel}:{texto[:m.start()].count(chr(10)) + 1}: {cls[:60]}")
    return salida


class ObjetivosTactilesTests(unittest.TestCase):
    def test_ningun_control_tactil_declara_menos_de_44px(self):
        self.assertEqual(_ofensores(), [])

    def test_el_segmentedcontrol_de_gastos_mide_44px(self):
        src = (RAIZ / "components" / "dashboard" / "SegmentedControl.tsx").read_text(encoding="utf-8")
        self.assertIn("min-h-[44px]", src)
        self.assertNotIn("min-h-[40px]", src)

    def test_las_excepciones_siguen_existiendo(self):
        pagina = (RAIZ / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        i, j = _region(pagina, "const renderProductoGrid", "const renderProductoLista")
        self.assertIn("w-7 h-7", pagina[i:j])  # si ya no hay, se retira la excepcion
        layout = (RAIZ / "app" / "dashboard" / "layout.tsx").read_text(encoding="utf-8")
        self.assertIn("group flex items-center gap-3 px-3", layout)

    def test_los_cierres_de_modales_y_filas_conocidas_miden_44px(self):
        for ruta, clase in (("components/dashboard/IconPicker.tsx", "w-11 h-11"),
                            ("components/dashboard/HojaCompleta.tsx", "w-11 h-11"),
                            ("components/shared/SelectorHogarPantallaCompleta.tsx", "w-11 h-11"),
                            ("components/shared/InvitacionesPendientes.tsx", "w-11 h-11")):
            with self.subTest(ruta=ruta):
                self.assertIn(clase, (RAIZ / ruta).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
