"""Integracion de claude_ocr.py con el SDK REAL de anthropic.

Los demas tests del motor de vision usan un doble escrito a mano, que solo
comprueba lo que creemos que hace el SDK. Aqui se usa el paquete `anthropic` de
verdad apuntando a un servidor HTTP local: asi se ve el payload que sale por el
cable y se comprueba que el parseo aguanta objetos de respuesta reales.

Cubre el fallo que dejaba el escaner en 0 articulos aunque el modelo funcionase:
el prompt describe QUE extraer pero delega el formato de salida en el esquema
(output_config.format), asi que cuando la API rechaza ese parametro y hay que
reintentar sin esquema, no habia nada que le pidiera JSON al modelo. Contestaba
en prosa, no parseaba nada y el ticket se quedaba vacio.
"""
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from PIL import Image

try:
    import anthropic  # noqa: F401
    SDK_DISPONIBLE = True
except ImportError:  # pragma: no cover
    SDK_DISPONIBLE = False

from stockhogar.servicios.ocr.claude_ocr import ClaudeOCR

CATALOGO = [{"id": 7, "nombre": "Leche entera 1L"}]
RESPUESTA_JSON = json.dumps({"productos": [
    {"nombre_ticket": "LECHE ENTERA 1L", "cantidad": 2, "unidad": "ud", "producto_id": 7},
    {"nombre_ticket": "TOMATE PERA", "cantidad": 0.85, "unidad": "kg", "producto_id": None},
]})


def _foto(ancho=900, alto=1400):
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), (250, 250, 250)).save(buffer, format="JPEG")
    return buffer.getvalue()


class _Servidor:
    """Servidor local que imita POST /v1/messages y registra las peticiones."""

    def __init__(self, rechazar_esquema=False, envolver_en_markdown=False):
        self.peticiones = []
        rechazar, envolver = rechazar_esquema, envolver_en_markdown
        registro = self.peticiones

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                largo = int(self.headers.get("content-length", 0))
                cuerpo = json.loads(self.rfile.read(largo))
                registro.append(cuerpo)

                if rechazar and "output_config" in cuerpo:
                    payload = json.dumps({"type": "error", "error": {
                        "type": "invalid_request_error",
                        "message": "output_config: unsupported parameter",
                    }}).encode()
                    self.send_response(400)
                else:
                    texto = RESPUESTA_JSON
                    if envolver and "output_config" not in cuerpo:
                        texto = f"```json\n{RESPUESTA_JSON}\n```"
                    payload = json.dumps({
                        "id": "msg_01", "type": "message", "role": "assistant",
                        "model": "claude-opus-5",
                        # Bloque de razonamiento delante: es el caso que rompia
                        # la lectura de content[0].text.
                        "content": [
                            {"type": "thinking", "thinking": "", "signature": "s"},
                            {"type": "text", "text": texto},
                        ],
                        "stop_reason": "end_turn", "stop_sequence": None,
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    }).encode()
                    self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self._srv = HTTPServer(("127.0.0.1", 0), Handler)

    def __enter__(self):
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._srv.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self._srv.shutdown()
        self._srv.server_close()

    @property
    def ultimo_prompt(self):
        return self.peticiones[-1]["messages"][0]["content"][-1]["text"]


@unittest.skipUnless(SDK_DISPONIBLE, "el paquete anthropic no esta instalado")
class IntegracionSdkTests(unittest.TestCase):
    def setUp(self):
        # El flag es de clase y una degradacion se recuerda entre instancias.
        self._soporte = ClaudeOCR._soporta_esquema
        ClaudeOCR._soporta_esquema = True

    def tearDown(self):
        ClaudeOCR._soporta_esquema = self._soporte

    def _motor(self, servidor):
        entorno = {"ANTHROPIC_API_KEY": "sk-ant-falsa", "ANTHROPIC_BASE_URL": servidor.url}
        with patch.dict(os.environ, entorno):
            return ClaudeOCR()

    def test_el_sdk_real_acepta_el_payload_y_se_parsea_la_respuesta(self):
        with _Servidor() as servidor:
            motor = self._motor(servidor)
            with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": servidor.url}):
                resultado = motor.procesar(_foto(), CATALOGO)

            self.assertEqual(len(servidor.peticiones), 1)
            enviado = servidor.peticiones[0]
            self.assertEqual(enviado["model"], "claude-opus-5")
            self.assertGreaterEqual(enviado["max_tokens"], 8000)
            self.assertEqual(
                enviado["output_config"]["format"]["type"], "json_schema",
                "el SDK real debe transmitir el esquema tal cual",
            )
            self.assertEqual(
                [b["type"] for b in enviado["messages"][0]["content"]], ["image", "text"]
            )

        self.assertIsNotNone(resultado)
        self.assertEqual(len(resultado["productos"]), 2)
        self.assertEqual(resultado["productos"][0]["producto_id"], 7)
        self.assertEqual(resultado["productos"][1]["unidad"], "kg")

    def test_con_esquema_el_prompt_no_gasta_tokens_describiendo_el_formato(self):
        with _Servidor() as servidor:
            motor = self._motor(servidor)
            with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": servidor.url}):
                motor.procesar(_foto(), CATALOGO)
            self.assertNotIn("json", servidor.ultimo_prompt.lower())

    def test_si_la_api_rechaza_el_esquema_el_prompt_si_pide_json(self):
        """Sin esta peticion explicita el modelo contesta en prosa y el ticket
        se queda en 0 articulos."""
        with _Servidor(rechazar_esquema=True, envolver_en_markdown=True) as servidor:
            motor = self._motor(servidor)
            with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": servidor.url}):
                resultado = motor.procesar(_foto(), CATALOGO)

            # Un intento con esquema (rechazado) y otro sin el.
            self.assertEqual(len(servidor.peticiones), 2)
            self.assertIn("output_config", servidor.peticiones[0])
            self.assertNotIn("output_config", servidor.peticiones[1])
            self.assertIn("json", servidor.ultimo_prompt.lower())
            self.assertIn('"productos"', servidor.ultimo_prompt)

        # Y el JSON envuelto en markdown (lo que devuelve un modelo sin
        # esquema) se sigue parseando.
        self.assertIsNotNone(resultado, "el reintento sin esquema debe reconocer articulos")
        self.assertEqual(len(resultado["productos"]), 2)

    def test_ticket_alto_manda_un_bloque_de_imagen_por_fragmento(self):
        with _Servidor() as servidor:
            motor = self._motor(servidor)
            with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": servidor.url}):
                motor.procesar(_foto(1200, 5000), CATALOGO)

            bloques = servidor.peticiones[0]["messages"][0]["content"]
            imagenes = [b for b in bloques if b["type"] == "image"]
            self.assertGreater(len(imagenes), 1)
            for bloque in imagenes:
                self.assertEqual(bloque["source"]["type"], "base64")
                self.assertTrue(bloque["source"]["data"])


if __name__ == "__main__":
    unittest.main()
