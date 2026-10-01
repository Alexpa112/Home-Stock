"""Fase 4 del rediseno movil: Compra con deslizar, progreso y barra rapida.

Fija lo que NO se puede perder al anadir el gesto: la casilla accesible, la
pulsacion larga (editar) y que la barra rapida use las mismas vias que el
formulario completo en vez de duplicar logica. Lee el fuente (patron del
proyecto); el gesto real se mide aparte en Chromium.
"""
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = (RAIZ / "app" / "dashboard" / "shopping" / "page.tsx").read_text(encoding="utf-8")
FILA = (RAIZ / "components" / "dashboard" / "FilaDeslizable.tsx").read_text(encoding="utf-8")
BARRA = (RAIZ / "components" / "dashboard" / "BarraRapida.tsx").read_text(encoding="utf-8")


def _fila_item():
    i = PAGINA.index("const renderItemRow")
    return PAGINA[i:PAGINA.index("const renderItemGridTile", i)]


class CasillaAccesibleTests(unittest.TestCase):
    def test_la_casilla_sigue_con_su_aria_label(self):
        f = _fila_item()
        self.assertIn("handleToggleBought(item.id, !isCompleted)", f)
        self.assertIn("aria_marcar_comprado_producto", f)
        self.assertIn("aria_restaurar_producto", f)
        self.assertIn("w-11 h-11", f)

    def test_el_gesto_envuelve_la_fila_sin_quitar_la_casilla(self):
        f = _fila_item()
        self.assertIn("<FilaDeslizable", f)
        self.assertIn("</FilaDeslizable>", f)
        self.assertIn("key={item.id}", f.split("<div")[0])  # la key va en el envoltorio

    def test_editar_y_eliminar_de_la_fila_siguen_existiendo(self):
        f = _fila_item()
        self.assertIn("abrirModalEdicion(item)", f)
        self.assertIn("handleDeleteItem(item.id)", f)


class CoordinacionConPulsacionLargaTests(unittest.TestCase):
    def test_deslizar_cancela_la_pulsacion_larga(self):
        self.assertIn("const cancelarLongPress", PAGINA)
        self.assertIn("onMovimiento={cancelarLongPress}", _fila_item())

    def test_si_la_pulsacion_larga_ya_salto_el_gesto_se_ignora(self):
        self.assertIn("bloqueado={() => longPressDisparado.current}", _fila_item())
        self.assertIn("bloqueado()", FILA)

    def test_el_navegador_deja_pasar_el_movimiento_horizontal(self):
        self.assertIn("touchAction: 'pan-y'", FILA)

    def test_la_capa_del_gesto_no_tapa_la_casilla(self):
        # Regresion real: la capa verde (absolute inset-0) se pintaba ENCIMA de
        # la fila e interceptaba los clics, asi que la casilla dejaba de
        # funcionar. La capa no recibe eventos y el contenido va por encima.
        capa = FILA[FILA.index('aria-hidden="true"'):]
        self.assertIn("pointer-events-none", capa.split(">")[0] + capa.split("className=")[1][:120])
        self.assertIn('className="relative"', FILA)

    def test_el_borde_izquierdo_se_reserva_al_gesto_atras(self):
        self.assertIn("empiezaEnElBorde", FILA)

    def test_la_pulsacion_larga_original_no_cambia(self):
        self.assertIn("}, 550)", PAGINA)
        self.assertIn("onTouchMove: cancelar", PAGINA)


class ProgresoTests(unittest.TestCase):
    def test_hay_barra_de_progreso_accesible(self):
        self.assertIn('role="progressbar"', PAGINA)
        self.assertIn("aria-valuenow={completados.length}", PAGINA)

    def test_la_clave_de_progreso_existe_con_sus_marcadores_en_los_7_idiomas(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d), 7)
        for idioma, textos in d.items():
            with self.subTest(idioma=idioma):
                self.assertIn("{comprados}", textos["progreso_compra"])
                self.assertIn("{total}", textos["progreso_compra"])


class BarraRapidaTests(unittest.TestCase):
    def test_el_boton_flotante_abre_la_barra_y_no_el_formulario(self):
        self.assertIn("useAccionAnadir(() => setBarraRapida(true))", PAGINA)

    def test_el_boton_de_escritorio_sigue_abriendo_el_formulario_completo(self):
        self.assertIn("onClick={() => setShowForm(!showForm)}", PAGINA)

    def test_la_barra_no_duplica_logica_usa_las_mismas_vias(self):
        i = PAGINA.index("const handleAnadirRapido")
        h = PAGINA[i:PAGINA.index("const seleccionarSugerencia", i)]
        self.assertIn("articulosLista.anadir(", h)
        self.assertIn("fusionarArticulo(creado)", h)
        self.assertIn("buscarCatalogo(", BARRA)
        self.assertNotIn("articulosLista", BARRA)  # la barra no habla con la API de la lista

    def test_mas_opciones_pasa_lo_escrito_al_formulario_completo(self):
        self.assertIn("setFormData((prev) => ({ ...prev, nombre }))", PAGINA)
        self.assertIn("setShowForm(true)", PAGINA)

    def test_el_escaner_sigue_siendo_barcodescanner(self):
        self.assertIn("setMostrarEscaner(true)", PAGINA)
        self.assertIn("<BarcodeScanner", PAGINA)

    def test_la_barra_tiene_etiquetas_y_objetivos_tactiles(self):
        self.assertIn("htmlFor=\"barra-rapida-nombre\"", BARRA)
        self.assertIn("aria-label={t('escanear_codigo_barras')}", BARRA)
        self.assertIn("aria-label={t('añadir')}", BARRA)
        self.assertNotIn("w-9 h-9", BARRA)
        self.assertIn("!text-base", BARRA)  # 16 px: iOS no hace zoom al enfocar

    def test_la_barra_oculta_el_boton_flotante_mientras_esta_abierta(self):
        lay = (RAIZ / "app" / "dashboard" / "layout.tsx").read_text(encoding="utf-8")
        self.assertIn("document.body.dataset.barraRapida", BARRA)
        self.assertIn("[body[data-barra-rapida]_&]:hidden", lay)

    def test_la_barra_ignora_el_margen_del_contenedor_y_el_hueco_va_al_final(self):
        # Regresion real: space-y-6 del contenedor le daba 24 px de margen
        # inferior a la barra (quedaba separada de la barra de pestanas) y el
        # separador, puesto a mitad de pagina, abria un hueco entre secciones.
        self.assertIn("!mb-0", BARRA)
        cola = PAGINA[PAGINA.rindex("barraRapida && <div"):]
        self.assertIn('className="h-48 lg:hidden"', cola)
        self.assertLess(len(cola), 400)  # esta al final, no a mitad de la pagina

    def test_la_barra_es_solo_movil(self):
        self.assertIn("lg:hidden", BARRA)


if __name__ == "__main__":
    unittest.main()
