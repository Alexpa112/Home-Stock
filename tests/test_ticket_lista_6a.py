"""Fase 5 del rediseno movil: revision de ticket en formato 6A + aviso de dudosa.

Lee el fuente (patron del proyecto). Fija lo que NO se puede perder al pasar de
tres inputs por linea a chips con editor desplegable, y la regla del aviso de
cantidad dudosa (el caso real del 0,85 de "TOMATE PERA").
"""
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = (RAIZ / "app" / "dashboard" / "ticket" / "page.tsx").read_text(encoding="utf-8")
REGLA = (RAIZ / "lib" / "ticket.ts").read_text(encoding="utf-8")


class RevisionConservaFuncionesTests(unittest.TestCase):
    def test_siguen_la_casilla_y_seleccionar_todos(self):
        self.assertIn("aria_excluir_producto", PAGINA)
        self.assertIn("aria_incluir_producto", PAGINA)
        self.assertIn("deseleccionar_todos", PAGINA)
        self.assertIn("seleccionar_todos", PAGINA)

    def test_siguen_las_marcas_conocido_y_nuevo(self):
        self.assertIn("t('conocido')", PAGINA)
        self.assertIn("t('nuevo_badge')", PAGINA)

    def test_se_pueden_editar_nombre_cantidad_y_categoria(self):
        for campo in ("nombre: e.target.value", "categoria: e.target.value"):
            self.assertIn(campo, PAGINA)
        self.assertIn("parseFloat(e.target.value)", PAGINA)  # no parseInt: no truncar pesos
        self.assertNotIn("parseInt(", PAGINA)
        self.assertIn('step="any"', PAGINA)

    def test_el_lapiz_despliega_el_editor_y_tiene_etiqueta(self):
        self.assertIn("setEditando(editandoEsta ? null : idx)", PAGINA)
        self.assertIn("aria-expanded={editandoEsta}", PAGINA)
        self.assertIn("aria-label={`${t('editar')} ${item.nombre}`}", PAGINA)

    def test_confirmar_envia_los_mismos_campos(self):
        i = PAGINA.index("tickets.confirmar(")
        cuerpo = PAGINA[i:i + 400]
        for campo in ("nombre: it.nombre", "cantidad: it.cantidad === '' ? 1 : it.cantidad",
                      "unidad: it.unidad", "categoria: it.categoria", "producto_id: it.producto_id"):
            self.assertIn(campo, cuerpo)

    def test_los_controles_tactiles_miden_44px(self):
        self.assertIn("w-11 h-11", PAGINA)
        self.assertIn("min-h-[44px]", PAGINA)
        self.assertNotIn("w-9 h-9", PAGINA)

    def test_la_barra_de_accion_queda_sobre_la_barra_de_pestanas(self):
        # `sticky` NO vale: en movil scrollea el documento y <main> tiene
        # overflow, asi que flotaba sobre las tarjetas (regresion real).
        self.assertNotIn("sticky bottom", PAGINA)  # la clase, no el comentario que la explica
        self.assertIn("fixed inset-x-0 bottom-[var(--mobile-toolbar-h)]", PAGINA)
        self.assertIn("lg:static", PAGINA)
        self.assertIn('className="h-24 lg:hidden"', PAGINA)  # hueco para no tapar la ultima linea

    def test_el_boton_de_importar_muestra_cuantas_lineas(self):
        self.assertIn("importar_n_al_stock", PAGINA)
        self.assertIn("i.incluir && i.nombre.trim()).length", PAGINA)


class AvisoCantidadDudosaTests(unittest.TestCase):
    def test_la_regla_es_decimal_con_unidad_ud(self):
        self.assertIn("unidad.trim().toLowerCase() === 'ud' && !Number.isInteger(cantidad)", REGLA)

    def test_la_pagina_usa_la_regla_y_muestra_el_aviso(self):
        self.assertIn("cantidadDudosa(item.cantidad, item.unidad)", PAGINA)
        self.assertIn("aviso_cantidad_dudosa", PAGINA)
        self.assertIn('role="note"', PAGINA)

    def test_el_aviso_no_bloquea_la_importacion(self):
        i = PAGINA.index("disabled={confirmando")
        self.assertNotIn("dudosa", PAGINA[i:i + 120])

    def test_la_clave_existe_en_los_7_idiomas_con_su_marcador(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d), 7)
        for idioma, textos in d.items():
            with self.subTest(idioma=idioma):
                self.assertIn("{cantidad}", textos["aviso_cantidad_dudosa"])


if __name__ == "__main__":
    unittest.main()
