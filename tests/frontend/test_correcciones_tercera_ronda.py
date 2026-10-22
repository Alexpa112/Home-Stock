"""Regresiones de la tercera ronda (2026-10-22): push en iOS y errores menores.

No hay entorno de pruebas de React (jest solo cubre lib/), asi que se atan
leyendo el fuente, como el resto de tests/frontend. La logica pura tiene sus
propios tests de jest (errorPush, peticionesEnVuelo, categoriasGasto).
"""
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
TRADUCCIONES = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))


def _leer(*ruta):
    return RAIZ.joinpath(*ruta).read_text(encoding="utf-8")


class PushIosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = _leer("lib", "usePushNotifications.ts")

    def test_clave_y_registro_se_cargan_al_montar_no_al_pulsar(self):
        # iOS exige que subscribe() vaya dentro del gesto del usuario: sin viajes
        # de red entre el toque y subscribe().
        self.assertIn("clavePublicaRef", self.hook)
        self.assertIn("registroRef", self.hook)
        self.assertIn("clavePublicaRef.current = clave_publica", self.hook)

    def test_pide_el_permiso_antes_que_cualquier_otra_espera(self):
        activar = self.hook[self.hook.index("const activar"):self.hook.index("const desactivar")]
        self.assertLess(activar.index("requestPermission"), activar.index("serviceWorker.ready"))
        self.assertLess(activar.index("requestPermission"), activar.index("vapidClavePublica"))

    def test_reutiliza_la_suscripcion_existente_y_deshace_la_huerfana(self):
        activar = self.hook[self.hook.index("const activar"):self.hook.index("const desactivar")]
        self.assertIn("getSubscription()", activar)
        self.assertIn("suscripcionNueva.unsubscribe()", activar)

    def test_los_errores_del_navegador_ya_no_son_siempre_error_de_conexion(self):
        self.assertIn("claveErrorPush", self.hook)
        self.assertNotIn("mensajeDeError", self.hook)
        errores = _leer("lib", "errorPush.ts")
        self.assertIn("NotAllowedError", errores)
        self.assertIn("err_push_no_permitido", errores)

    def test_los_avisos_nuevos_existen_en_todos_los_idiomas(self):
        for idioma, textos in TRADUCCIONES.items():
            for clave in ("err_push_no_permitido", "err_push_fallo_suscripcion"):
                self.assertTrue(textos.get(clave), f"{idioma}:{clave}")
            self.assertIn("16.4", textos["err_push_no_permitido"], idioma)


class AjustesSinHogarTests(unittest.TestCase):
    def test_el_layout_deja_entrar_a_ajustes_sin_hogar(self):
        layout = _leer("app", "dashboard", "layout.tsx")
        self.assertIn("!hogarActivoId && pathname !== '/dashboard/settings'", layout)


class BalancesSinDuplicadoTests(unittest.TestCase):
    def test_el_panel_vacio_no_repite_el_mensaje_del_hero(self):
        panel = _leer("components", "dashboard", "gastos", "BalancesPanel.tsx")
        self.assertNotIn("t('estas_en_paz')", panel)
        self.assertIn("t('sin_pagos_pendientes')", panel)
        for idioma, textos in TRADUCCIONES.items():
            self.assertTrue(textos.get("sin_pagos_pendientes"), idioma)


class CategoriasGastoTraducidasTests(unittest.TestCase):
    def test_las_siete_por_defecto_tienen_traduccion_en_todos_los_idiomas(self):
        for idioma, textos in TRADUCCIONES.items():
            for slug in ("alimentacion", "transporte", "vivienda", "ocio", "salud", "suministros", "otros"):
                self.assertTrue(textos.get(f"catgasto_{slug}"), f"{idioma}:{slug}")

    def test_se_aplica_donde_se_muestran(self):
        self.assertIn("nombreCategoriaGasto(cat.nombre, t)", _leer("components", "dashboard", "gastos", "FormularioGasto.tsx"))
        pagina = _leer("app", "dashboard", "gastos", "page.tsx")
        self.assertIn("nombreCategoriaGasto(cat.nombre, t)", pagina)
        self.assertIn("nombreCategoriaGasto(d.etiqueta, t)", pagina)

    def test_los_nombres_por_defecto_del_backend_estan_cubiertos(self):
        config = _leer("stockhogar", "config.py")
        helper = _leer("lib", "categoriasGasto.ts")
        inicio = config.index("CATEGORIAS_GASTO_DEFECTO = [")
        bloque = config[inicio:config.index("]", inicio)]
        import re
        for nombre in re.findall(r'\("([^"]+)",', bloque):
            self.assertIn(f"case '{nombre}'", helper, nombre)


class TituloDePestanaTests(unittest.TestCase):
    def test_el_titulo_sigue_al_idioma_y_a_la_navegacion(self):
        raiz = _leer("app", "RootLayoutClient.tsx")
        self.assertIn("document.title = t('titulo_pestana')", raiz)
        self.assertIn("[t, ruta]", raiz)
        for idioma, textos in TRADUCCIONES.items():
            self.assertTrue(textos.get("titulo_pestana", "").startswith("Dreame!"), idioma)


class PeticionesDuplicadasTests(unittest.TestCase):
    def test_estado_y_hogares_comparten_la_peticion_en_vuelo(self):
        api = _leer("lib", "api.ts")
        self.assertIn("compartirEnVuelo('auth.estado'", api)
        self.assertIn("compartirEnVuelo('hogares.listar'", api)

    def test_una_escritura_invalida_las_lecturas_compartidas(self):
        api = _leer("lib", "api.ts")
        self.assertIn("olvidarEnVuelo()", api)


if __name__ == "__main__":
    unittest.main()
