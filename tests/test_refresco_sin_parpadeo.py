"""Regresion del tiron periodico de la aplicacion.

HogarContext refresca los hogares cada 60 s para detectar que otro miembro
haya cambiado el color/icono del hogar activo. Ese refresco compartia funcion
con la carga inicial, asi que ponia `loading = true`, y dashboard/layout.tsx
sustituye TODA la pantalla por un spinner mientras `loading` sea true.

Efecto medido en un navegador real: en 95 s de reposo aparecia un spinner de
pantalla completa, el arbol de `children` se desmontaba (perdiendo scroll,
filtros y modales abiertos) y al remontar cada pagina volvia a pedir sus datos
(/api/productos, /api/categorias, /api/articulos e invitaciones-pendientes).
Tras separar el refresco silencioso: 0 spinners en los mismos 95 s.

No hay entorno de pruebas de React en el proyecto (jest.config.lib.js solo
cubre funciones puras de lib/), asi que se ata leyendo el fuente, igual que
hacen tests/test_invitacion_enlace_profundo.py y tests/test_sin_login_apple.py
con las dos mitades del flujo de invitacion.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONTEXTO = RAIZ / "contexts" / "HogarContext.tsx"
LAYOUT = RAIZ / "app" / "dashboard" / "layout.tsx"
TRADUCCIONES = RAIZ / "contexts" / "TranslationContext.tsx"


class RefrescoSinParpadeoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contexto = CONTEXTO.read_text(encoding="utf-8")
        cls.layout = LAYOUT.read_text(encoding="utf-8")
        cls.traducciones = TRADUCCIONES.read_text(encoding="utf-8")

    def test_el_layout_sigue_tapando_la_pantalla_cuando_loading(self):
        """Premisa de todo lo demas: si esto cambiara, el resto de los tests
        de este fichero dejarian de proteger nada y habria que replantearlos."""
        self.assertRegex(
            self.layout, r"if\s*\(\s*loading\s*\)",
            "el layout ya no depende de `loading`: revisar si estos tests siguen teniendo sentido",
        )
        self.assertIn("animate-spin", self.layout)

    def test_el_refresco_periodico_es_silencioso(self):
        """El setInterval debe llamar a cargar(true), no a cargar()."""
        intervalo = re.search(
            r"setInterval\((.*?)\},\s*INTERVALO_REVISION_TEMA_MS\)",
            self.contexto, re.S,
        )
        self.assertIsNotNone(intervalo, "no se encontro el setInterval del refresco de tema")
        cuerpo = intervalo.group(1)
        self.assertIn(
            "cargar(true)", cuerpo,
            "el refresco de fondo vuelve a llamar a cargar() sin marcarlo como "
            "silencioso: pondra loading=true y la app parpadeara cada 60 s",
        )

    def test_cargar_solo_toca_loading_cuando_no_es_silencioso(self):
        """Cada setLoading/setError de `cargar` debe estar bajo `if (!silencioso)`."""
        cuerpo = self.contexto[self.contexto.index("const cargar ="):self.contexto.index("useEffect(() => {\n    cargar()")]
        self.assertIn("silencioso", cuerpo, "cargar() ya no distingue el refresco silencioso")
        for llamada in re.findall(r"set(?:Loading|Error)\([^)]*\)", cuerpo):
            # setError(null) y setLoading(true/false) deben ir precedidos en la
            # misma linea o en el bloque por la comprobacion de `silencioso`.
            posicion = cuerpo.index(llamada)
            contexto_previo = cuerpo[max(0, posicion - 120):posicion]
            with self.subTest(llamada=llamada):
                self.assertIn(
                    "silencioso", contexto_previo,
                    f"{llamada} se ejecuta tambien en el refresco de fondo",
                )

    def test_t_es_estable_entre_renders(self):
        """t() envuelto en useCallback y el value en useMemo.

        Cuando t() se recreaba en cada render, HogarContext.cargar (que lo
        llevaba en sus dependencias) cambiaba de identidad, su useEffect se
        reejecutaba y /api/hogares se pedia varias veces por montaje: 16
        peticiones en la carga del dashboard donde bastan 11.
        """
        self.assertRegex(
            self.traducciones, r"const t = useCallback\(",
            "t() vuelve a recrearse en cada render: los efectos que dependan de "
            "el se reejecutaran sin motivo",
        )
        self.assertRegex(
            self.traducciones, r"const valor = useMemo\(",
            "el value del TranslationProvider vuelve a ser un objeto literal: "
            "repinta a todos los consumidores en cada render",
        )

    def test_cargar_no_depende_de_t(self):
        """`cargar` debe leer t por referencia (tRef) y tener dependencias vacias."""
        self.assertIn("tRef", self.contexto, "cargar volvio a depender de t directamente")
        firma = re.search(r"const cargar = useCallback\(.*?\n  \}, \[(.*?)\]\)", self.contexto, re.S)
        self.assertIsNotNone(firma, "no se pudo leer las dependencias de cargar")
        self.assertEqual(
            firma.group(1).strip(), "",
            "cargar volvio a tener dependencias: cambiara de identidad y "
            "reejecutara la carga inicial",
        )

    def test_el_value_del_contexto_de_hogares_esta_memoizado(self):
        self.assertRegex(
            self.contexto, r"const valor = useMemo\(",
            "el value del HogarProvider vuelve a ser un objeto literal nuevo en "
            "cada render: repinta a todo consumidor de useHogar()",
        )


class ListasLargasTests(unittest.TestCase):
    """Las listas que pueden tener cientos de filas llevan content-visibility.

    Medido con 400 productos y CPU x10 (movil lento): sin esto, 3 de 89
    fotogramas pasaban de 32 ms al desplazar, con un pico de 165 ms; con
    esto, 0 fotogramas perdidos y un peor caso de 19 ms.
    """

    CSS = RAIZ / "app" / "globals.css"
    PAGINAS = {
        "stock": RAIZ / "app" / "dashboard" / "page.tsx",
        "lista de la compra": RAIZ / "app" / "dashboard" / "shopping" / "page.tsx",
        "gastos": RAIZ / "components" / "dashboard" / "gastos" / "ListaGastos.tsx",
    }

    def test_las_clases_existen_en_el_css(self):
        css = self.CSS.read_text(encoding="utf-8")
        for clase in (".lista-larga >", ".lista-larga-grid >"):
            with self.subTest(clase=clase):
                self.assertIn(clase, css)
        self.assertIn("content-visibility: auto", css)
        # Sin contain-intrinsic-size la barra de desplazamiento daria saltos.
        self.assertIn("contain-intrinsic-size", css)

    def test_las_listas_largas_usan_la_clase(self):
        for nombre, ruta in self.PAGINAS.items():
            with self.subTest(pantalla=nombre):
                self.assertIn(
                    "lista-larga", ruta.read_text(encoding="utf-8"),
                    f"la lista de {nombre} ya no marca sus filas como lista larga",
                )

    def test_la_cabecera_sticky_de_gastos_no_queda_dentro_de_la_contencion(self):
        """content-visibility crea un bloque contenedor: si se aplicara al
        contenedor del grupo del mes, su cabecera dejaria de ser sticky."""
        fuente = self.PAGINAS["gastos"].read_text(encoding="utf-8")
        for linea in fuente.splitlines():
            if "lista-larga" in linea:
                with self.subTest(linea=linea.strip()[:60]):
                    self.assertNotIn(
                        "sticky", linea,
                        "lista-larga y sticky en el mismo elemento: la cabecera "
                        "del mes dejaria de quedarse pegada arriba",
                    )


if __name__ == "__main__":
    unittest.main()
