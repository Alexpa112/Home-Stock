"""Interruptores unificados y menos sondeo en segundo plano (cuarta ronda, 2026-10-22).

Se leen los fuentes (no hay entorno de React); la logica pura tiene tests de jest.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent


def _leer(*ruta):
    return RAIZ.joinpath(*ruta).read_text(encoding="utf-8")


class InterruptoresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.componente = _leer("components", "shared", "Interruptor.tsx")
        cls.css = _leer("app", "globals.css")
        cls.ajustes = _leer("app", "dashboard", "settings", "page.tsx")

    def test_es_un_switch_accesible(self):
        self.assertIn('role="switch"', self.componente)
        self.assertIn("aria-checked={activo}", self.componente)
        self.assertIn("aria-label={etiqueta}", self.componente)
        self.assertIn("aria-busy", self.componente)
        self.assertIn("disabled={deshabilitado || cargando}", self.componente)

    def test_el_estado_no_depende_solo_del_color(self):
        """Encendido lleva una marca de verificacion; cargando, un indicador giratorio."""
        self.assertIn("<Check", self.componente)
        self.assertIn("<Loader2", self.componente)

    def test_el_pulgar_queda_centrado_con_margen_igual_en_los_cuatro_lados(self):
        """La pista mide 3,5x2 rem con 0,25 de relleno y el pulgar 1,5: 0,25 arriba, abajo y a los lados.
        El dibujo antiguo ponia el pulgar 6 px arriba y 2 px abajo (top-1.5 sobre un contenedor con borde)."""
        pista = re.search(r"\.interruptor \{(.*?)\n  \}", self.css, re.S).group(1)
        pulgar = re.search(r"\.interruptor-pulgar \{(.*?)\n  \}", self.css, re.S).group(1)
        self.assertIn("width: 3.5rem", pista)
        self.assertIn("height: 2rem", pista)
        self.assertIn("padding: 0.25rem", pista)
        self.assertIn("align-items: center", pista)
        self.assertIn("width: 1.5rem", pulgar)
        self.assertIn("height: 1.5rem", pulgar)
        # recorrido = ancho interior (3.5 - 2*0.25 = 3.0) - pulgar (1.5) = 1.5rem
        self.assertIn("translateX(1.5rem)", self.css)

    def test_apagado_se_ve_sobre_la_tarjeta_en_claro_y_oscuro(self):
        pista = re.search(r"\.interruptor \{(.*?)\n  \}", self.css, re.S).group(1)
        self.assertIn("var(--color-muted-foreground)", pista)
        self.assertIn("var(--color-card)", pista)
        self.assertIn("inset 0 0 0 1px", pista, "contorno para que el borde de la pista se vea")

    def test_la_zona_tactil_llega_a_44px_y_hay_foco_de_teclado(self):
        self.assertIn(".interruptor::before", self.css)
        self.assertIn("inset: -0.5rem", self.css)
        self.assertIn(".interruptor:focus-visible", self.css)
        self.assertIn("border-radius: 9999px", self.css.split(".interruptor:focus-visible")[1][:120])

    def test_respeta_reducir_movimiento(self):
        self.assertIn("prefers-reduced-motion: reduce", self.css)

    def test_todos_los_interruptores_de_ajustes_usan_el_componente(self):
        bloques = re.findall(r"<Interruptor[\s\S]*?\n\s*/>", self.ajustes)
        self.assertEqual(len(bloques), 5)
        for clave in ("doble_factor_titulo", "notificaciones_push_titulo", "ocr_local_titulo", "modo_oscuro", "agrupar_por_categoria"):
            self.assertEqual(sum(f"etiqueta={{t('{clave}')}}" in b for b in bloques), 1, clave)

    def test_no_quedan_interruptores_hechos_a_mano(self):
        self.assertNotIn("relative w-14 h-8", self.ajustes)
        self.assertNotIn("relative inline-flex items-center h-8 w-14", self.ajustes)
        self.assertNotIn('role="switch"', self.ajustes)
        for f in list((RAIZ / "app").rglob("*.tsx")) + list((RAIZ / "components").rglob("*.tsx")):
            if f.name == "Interruptor.tsx":
                continue
            self.assertNotIn('role="switch"', f.read_text(encoding="utf-8"), f.relative_to(RAIZ).as_posix())


class SondeoEnSegundoPlanoTests(unittest.TestCase):
    def test_la_version_no_se_pregunta_con_la_pestana_oculta(self):
        src = _leer("lib", "useCacheBuster.ts")
        self.assertIn("const CHECK_INTERVAL = 30000", src)
        self.assertIn("if (document.visibilityState !== 'visible') return;", src)
        self.assertIn("addEventListener('visibilitychange'", src)
        self.assertIn("removeEventListener('visibilitychange'", src)

    def test_mantenimiento_tampoco_y_comprueba_al_volver(self):
        src = _leer("lib", "useMantenimientoStream.ts")
        self.assertIn("const INTERVALO_MS = 30000", src)
        self.assertIn("addEventListener('visibilitychange'", src)
        self.assertIn("removeEventListener('visibilitychange'", src)


class TraduccionesSinViajesInutilesTests(unittest.TestCase):
    def test_el_espanol_no_se_pide_al_servidor(self):
        src = _leer("contexts", "TranslationContext.tsx")
        self.assertIn("idiomaActual === 'es'", src)
        self.assertIn("setTraducciones(TRADUCCIONES_BASE)", src)

    def test_el_diccionario_del_idioma_conocido_se_pide_en_paralelo(self):
        src = _leer("contexts", "TranslationContext.tsx")
        i = src.index("const adelantado")
        self.assertLess(i, src.index("fetch('/api/idiomas/obtener'"))
        self.assertIn("await adelantado", src)


if __name__ == "__main__":
    unittest.main()
