"""Escaner en el cliente: codigo de barras, subida de fotos y pantalla de ticket.

Lee el fuente (patron del proyecto: no hay jsdom). El comportamiento real se
comprobo ademas en Chromium con camara y BarcodeDetector simulados.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BARRAS = (RAIZ / "components" / "shared" / "BarcodeScanner.tsx").read_text(encoding="utf-8")
API = (RAIZ / "lib" / "api.ts").read_text(encoding="utf-8")
TICKET = (RAIZ / "app" / "dashboard" / "ticket" / "page.tsx").read_text(encoding="utf-8")


class BarcodeScannerTests(unittest.TestCase):
    def test_la_camara_se_abre_una_sola_vez_aunque_la_pantalla_se_renderice(self):
        # Antes el efecto dependia de [onDetectado] (funcion nueva en cada
        # render): cada re-render paraba y reabria la camara.
        self.assertIn("onDetectadoRef", BARRAS)
        self.assertNotIn("[onDetectado]", BARRAS)
        efecto = BARRAS[BARRAS.index("let activo = true"):]
        self.assertRegex(efecto, r"return detener\s*\n\s*\}, \[\]\)")

    def test_no_se_toca_mediadevices_ni_el_detector_sin_comprobar(self):
        self.assertIn("navigator.mediaDevices?.getUserMedia", BARRAS)
        self.assertIn("getSupportedFormats", BARRAS)
        # el constructor del detector va dentro de un try (lanza TypeError sin formatos)
        i = BARRAS.index("new Detector(")
        self.assertIn("try {", BARRAS[:i][-600:])

    def test_hay_entrada_manual_del_codigo_siempre_disponible(self):
        self.assertIn('id="codigo-manual"', BARRAS)
        self.assertIn("usarCodigoManual", BARRAS)
        self.assertIn("onDetectadoRef.current(codigo)", BARRAS)
        # el formulario manual esta fuera de las ramas condicionales de estado
        self.assertLess(BARRAS.index("estado === 'sin_soporte'"), BARRAS.index('id="codigo-manual"'))

    def test_distingue_sin_soporte_de_error_de_camara(self):
        self.assertIn("escaner_no_soportado", BARRAS)
        self.assertIn("err_camara_no_disponible", BARRAS)

    def test_apaga_la_camara_al_cerrar_y_al_detectar(self):
        self.assertIn("stream?.getTracks().forEach((track) => track.stop())", BARRAS)
        self.assertIn("detener()\n              onDetectadoRef.current(", BARRAS)

    def test_limita_la_frecuencia_de_deteccion(self):
        self.assertIn("INTERVALO_DETECCION_MS", BARRAS)

    def test_objetivos_tactiles_de_44px_y_texto_de_16px(self):
        self.assertGreaterEqual(BARRAS.count("min-h-[44px]"), 2)
        self.assertIn("!text-base", BARRAS)

    def test_las_claves_nuevas_existen_en_los_7_idiomas(self):
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d), 7)
        for idioma, textos in d.items():
            for k in ("codigo_manual_etiqueta", "codigo_manual_boton"):
                with self.subTest(idioma=idioma, clave=k):
                    self.assertTrue(textos.get(k, "").strip())


class SubidaDeFotosTests(unittest.TestCase):
    def _apiupload(self):
        i = API.index("async function apiUpload")
        return API[i:API.index("// Como apiCall pero para descargar", i)]

    def test_apiupload_reintenta_si_el_token_csrf_caduco(self):
        f = self._apiupload()
        self.assertIn("obtenerCsrfToken(true)", f)
        self.assertIn("includes('csrf')", f)

    def test_apiupload_trata_la_sesion_invalidada_como_apicall(self):
        # La interpretacion de la respuesta (401 -> limpiar cache y token) es UNA sola funcion
        # compartida por apiCall, apiUpload y apiDownload.
        self.assertIn("return leerRespuesta<T>(response)", self._apiupload())
        j = API.index("async function leerRespuesta")
        f = API[j:API.index("// Como apiCall pero para multipart", j)]
        self.assertIn("response.status === 401", f)
        self.assertIn("clearAllCache()", f)

    def test_cada_intento_tiene_su_propio_temporizador(self):
        f = self._apiupload()
        self.assertEqual(f.count("new AbortController()"), 1)  # dentro de `enviar`, que se llama por intento
        self.assertIn("const enviar = async", f)

    def test_la_pantalla_reduce_las_fotos_grandes_antes_de_subir(self):
        self.assertIn("tickets.analizar(await prepararFotoParaSubida(file))", TICKET)
        lib = (RAIZ / "lib" / "imagenSubida.ts").read_text(encoding="utf-8")
        self.assertIn("createImageBitmap(archivo, { imageOrientation: 'from-image' })", lib)  # respeta EXIF
        self.assertIn("blob.size >= archivo.size) return archivo", lib)  # nunca empeora
        self.assertIn("} catch {\n    return archivo", lib)  # nunca lanza

    def test_un_fallo_de_red_no_se_muestra_en_crudo(self):
        self.assertIn("esFalloDeRed(crudo)", TICKET)
        self.assertIn("t('error_procesar')", TICKET)


class PantallaDeTicketTests(unittest.TestCase):
    def test_la_suspension_por_edicion_esta_equilibrada(self):
        # suspender (1) y reanudar en el finally (1). Las dos llamadas extra que
        # habia al confirmar y al cancelar restaban de mas sobre un contador
        # global compartido con los modales.
        self.assertEqual(TICKET.count("suspenderPorEdicion()"), 1)
        self.assertEqual(TICKET.count("reanudarPorEdicion()"), 1)
        self.assertIn("finally {", TICKET[TICKET.index("suspenderPorEdicion()"):])

    def test_el_input_de_camara_y_el_de_archivo_siguen_ahi(self):
        self.assertIn('capture="environment"', TICKET)
        self.assertIn("application/pdf", TICKET)

    def test_el_limite_del_cliente_coincide_con_el_del_servidor(self):
        # tickets.py rechaza > TAMANO_MAXIMO_MB; el texto de ayuda debe decir lo mismo
        servidor = (RAIZ / "stockhogar" / "rutas" / "escaner" / "tickets.py").read_text(encoding="utf-8")
        mb = int(re.search(r"TAMANO_MAXIMO_MB = (\d+)", servidor).group(1))
        d = json.loads((RAIZ / "stockhogar" / "translations.json").read_text(encoding="utf-8"))["es"]
        self.assertIn(str(mb), d["jpg_png_hasta_10mb"])


if __name__ == "__main__":
    unittest.main()
