"""Fase 3 del rediseno movil: Stock con fila densa, chips en una fila y sin emoji.

Lee el fuente (patron del proyecto, sin navegador). El comportamiento visual se
mide aparte en Chromium; aqui se fijan las funciones que NO se pueden perder.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = (RAIZ / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿⌀-⏿⊞ℹ️]")


def _fila_lista():
    i = SRC.index("const renderProductoLista")
    return SRC[i:SRC.index("const renderProducto =", i)]


class FilaDensaTests(unittest.TestCase):
    def test_la_fila_conserva_pm1_optimista_y_abrir_edicion(self):
        f = _fila_lista()
        self.assertIn("handleAjustarCantidad(item.id, -1)", f)
        self.assertIn("handleAjustarCantidad(item.id, 1)", f)
        self.assertIn("abrirEdicion(item)", f)
        self.assertIn("aria-label={`${t('editar')} ${item.nombre}`}", f)

    def test_la_fila_conserva_las_marcas_y_anadir_a_la_compra(self):
        f = _fila_lista()
        self.assertIn("bajoMinimo", f)
        self.assertIn("revisar_caducidad", f)
        self.assertIn("bg-red-500 shrink-0", f)  # punto de bajo minimo
        self.assertIn("handleAñadirACompra(item)", f)

    def test_todos_los_controles_de_la_fila_miden_44px(self):
        f = _fila_lista()
        self.assertNotIn("w-9 h-9", f)
        self.assertGreaterEqual(f.count("w-11 h-11"), 3)  # menos, mas y carrito
        self.assertIn("min-h-[44px]", f)

    def test_eliminar_con_confirmacion_vive_en_el_detalle(self):
        # La fila ya no lleva papelera: se elimina desde el modal de edicion.
        self.assertNotIn("handleDeleteItem", _fila_lista())
        i = SRC.index("Add / Edit Form")
        modal = SRC[i:SRC.index("mostrarHistorialPreciosId !== null", i)]
        self.assertIn("handleDeleteItem(editandoId)", modal)
        self.assertIn("setConfirmandoId(null)", modal)  # el "No" cancela
        self.assertIn("aria_confirmar_eliminacion", modal)

    def test_abrir_edicion_reinicia_la_confirmacion(self):
        i = SRC.index("const abrirEdicion")
        self.assertIn("setConfirmandoId(null)", SRC[i:i + 120])

    def test_la_vista_grid_se_conserva(self):
        self.assertIn("const renderProductoGrid", SRC)
        self.assertIn("modoVista === 'lista' ? renderProductoLista(item) : renderProductoGrid(item)", SRC)

    def test_los_chips_van_en_una_fila_con_scroll(self):
        self.assertIn("flex-nowrap", SRC)
        self.assertIn("overflow-x-auto", SRC)
        self.assertEqual(SRC.count("px-2.5 min-h-[44px] shrink-0 whitespace-nowrap"), 3)

    def test_no_queda_emoji_en_el_fuente_de_stock(self):
        # Los comentarios se admiten; se excluyen lineas de comentario.
        for n, linea in enumerate(SRC.splitlines(), 1):
            if linea.strip().startswith(("//", "{/*", "*")):
                continue
            with self.subTest(linea=n):
                self.assertIsNone(EMOJI.search(linea), f"emoji en linea {n}: {linea.strip()[:70]}")


if __name__ == "__main__":
    unittest.main()
