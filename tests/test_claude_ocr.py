"""Tests del motor de OCR de tickets con Claude Vision (claude_ocr.py).

Sin red real: se inyecta un modulo `anthropic` falso en sys.modules para que
ClaudeOCR.__init__ construya un cliente de mentira y se pueda inspeccionar
exactamente que se manda a la API y que se hace con la respuesta.

Cubre las regresiones que dejaban al escaner sin reconocer articulos:
  * respuesta leida de content[0] (con razonamiento activado el primer bloque
    no es texto y se perdia la respuesta entera),
  * presupuesto de tokens tan corto que truncaba los tickets largos,
  * producto_id inventado por el modelo colandose como articulo del catalogo,
  * tiras muy altas enviadas de una pieza y reducidas hasta ser ilegibles,
  * PDF de varias paginas del que solo se leia la primera.
"""
import io
import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from PIL import Image

from stockhogar.servicios.ocr import claude_ocr
from stockhogar.servicios.ocr.claude_ocr import ClaudeOCR

CATALOGO = [
    {"id": 7, "nombre": "Leche entera 1L"},
    {"id": 9, "nombre": "Pan integral"},
]


class _Bloque:
    """Bloque de contenido de una respuesta de la API."""

    def __init__(self, tipo, texto=None):
        self.type = tipo
        if texto is not None:
            self.text = texto


class _Respuesta:
    def __init__(self, bloques, stop_reason="end_turn"):
        self.content = bloques
        self.stop_reason = stop_reason


class _Mensajes:
    def __init__(self, respuestas, errores=None):
        self._respuestas = list(respuestas)
        self._errores = list(errores or [])
        self.llamadas = []

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._errores:
            error = self._errores.pop(0)
            if error is not None:
                raise error
        return self._respuestas.pop(0)


class _ClienteFalso:
    def __init__(self, respuestas, errores=None, **_kwargs):
        self.messages = _Mensajes(respuestas, errores)


@contextmanager
def motor_falso(respuestas, errores=None):
    """Construye un ClaudeOCR con un SDK de anthropic simulado.

    `_soporta_esquema` es un flag de CLASE (el motor se instancia por peticion,
    asi que un flag de instancia no recordaria la degradacion), asi que hay que
    restaurarlo al salir para no contaminar los demas tests.
    """
    modulo = types.ModuleType("anthropic")
    creado = {}

    def _Anthropic(**kwargs):
        cliente = _ClienteFalso(respuestas, errores, **kwargs)
        creado["cliente"] = cliente
        creado["kwargs"] = kwargs
        return cliente

    modulo.Anthropic = _Anthropic
    soporte_original = ClaudeOCR._soporta_esquema
    try:
        with patch.dict(sys.modules, {"anthropic": modulo}):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "clave_falsa"}):
                motor = ClaudeOCR()
        yield motor, creado
    finally:
        ClaudeOCR._soporta_esquema = soporte_original


def _texto(json_texto, stop_reason="end_turn", con_razonamiento=False):
    bloques = []
    if con_razonamiento:
        bloques.append(_Bloque("thinking"))
    bloques.append(_Bloque("text", json_texto))
    return _Respuesta(bloques, stop_reason)


def _png(ancho, alto):
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), (250, 250, 250)).save(buffer, format="PNG")
    return buffer.getvalue()


class DisponibilidadTests(unittest.TestCase):
    def test_sin_api_key_no_esta_disponible(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            motor = ClaudeOCR()
        self.assertFalse(motor.disponible())
        self.assertIsNone(motor.procesar(b"loquesea", CATALOGO))

    def test_sin_paquete_anthropic_no_esta_disponible(self):
        """Con clave pero sin el paquete instalado el motor se declara no
        disponible en vez de reventar (el flujo cae a Tesseract)."""
        real = sys.modules.pop("anthropic", None)
        try:
            with patch.dict(sys.modules, {"anthropic": None}):
                with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "clave_falsa"}):
                    motor = ClaudeOCR()
            self.assertFalse(motor.disponible())
        finally:
            if real is not None:
                sys.modules["anthropic"] = real


class PeticionTests(unittest.TestCase):
    def test_peticion_usa_modelo_actual_esquema_y_presupuesto_amplio(self):
        respuesta = _texto('{"productos": []}')
        with motor_falso([respuesta]) as (motor, creado):
            motor.procesar(_png(600, 800), CATALOGO)
            llamada = creado["cliente"].messages.llamadas[0]

        self.assertEqual(llamada["model"], "claude-opus-5")
        # Un ticket de compra grande no cabe en 2048 tokens, y el
        # razonamiento sale del mismo presupuesto que la respuesta.
        self.assertGreaterEqual(llamada["max_tokens"], 8000)
        formato = llamada["output_config"]["format"]
        self.assertEqual(formato["type"], "json_schema")
        self.assertIn("productos", formato["schema"]["properties"])
        self.assertEqual(creado["kwargs"]["max_retries"], claude_ocr._MAX_REINTENTOS)

    def test_el_catalogo_viaja_en_el_prompt_y_la_imagen_va_delante(self):
        with motor_falso([_texto('{"productos": []}')]) as (motor, creado):
            motor.procesar(_png(600, 800), CATALOGO)
            contenido = creado["cliente"].messages.llamadas[0]["messages"][0]["content"]

        self.assertEqual(contenido[0]["type"], "image")
        self.assertEqual(contenido[-1]["type"], "text")
        prompt = contenido[-1]["text"]
        self.assertIn("7: Leche entera 1L", prompt)
        self.assertIn("9: Pan integral", prompt)

    def test_catalogo_vacio_no_rompe_la_llamada(self):
        with motor_falso([_texto('{"productos": []}')]) as (motor, creado):
            resultado = motor.procesar(_png(400, 400), [])
            prompt = creado["cliente"].messages.llamadas[0]["messages"][0]["content"][-1]["text"]

        # La respuesta trae ademas "totales" y "cuadre" (pie del ticket y su
        # comprobacion aritmetica); aqui solo interesa que no haya articulos.
        self.assertEqual(resultado["productos"], [])
        self.assertIn("catálogo vacío", prompt)


class RespuestaTests(unittest.TestCase):
    def test_se_lee_el_texto_aunque_haya_bloques_de_razonamiento_delante(self):
        """Regresion: se leia message.content[0].text, y con el razonamiento
        activado el primer bloque no es texto, asi que no se reconocia ni un
        articulo."""
        cuerpo = ('{"productos": [{"nombre_ticket": "LECHE ENTERA 1L", '
                  '"cantidad": 2, "unidad": "ud", "producto_id": 7}]}')
        with motor_falso([_texto(cuerpo, con_razonamiento=True)]) as (motor, _):
            resultado = motor.procesar(_png(600, 800), CATALOGO)

        self.assertEqual(len(resultado["productos"]), 1)
        self.assertEqual(resultado["productos"][0]["producto_id"], 7)
        self.assertEqual(resultado["productos"][0]["cantidad"], 2)

    def test_rechazo_del_modelo_devuelve_none(self):
        with motor_falso([_Respuesta([], stop_reason="refusal")]) as (motor, _):
            self.assertIsNone(motor.procesar(_png(400, 400), CATALOGO))

    def test_respuesta_sin_texto_devuelve_none(self):
        with motor_falso([_Respuesta([_Bloque("thinking")])]) as (motor, _):
            self.assertIsNone(motor.procesar(_png(400, 400), CATALOGO))

    def test_json_troceado_por_max_tokens_devuelve_none(self):
        recortado = '{"productos": [{"nombre_ticket": "LECHE'
        with motor_falso([_texto(recortado, stop_reason="max_tokens")]) as (motor, _):
            self.assertIsNone(motor.procesar(_png(400, 400), CATALOGO))

    def test_formato_inesperado_devuelve_none(self):
        with motor_falso([_texto('{"otra_cosa": 1}')]) as (motor, _):
            self.assertIsNone(motor.procesar(_png(400, 400), CATALOGO))

    def test_error_de_red_devuelve_none(self):
        with motor_falso([_texto('{"productos": []}')],
                         errores=[RuntimeError("sin conexion")]) as (motor, _):
            self.assertIsNone(motor.procesar(_png(400, 400), CATALOGO))


class NormalizacionTests(unittest.TestCase):
    def test_producto_id_inventado_se_descarta(self):
        """Un id que no esta en el catalogo pasaria a confirmar el ticket como
        si fuera un articulo ya existente."""
        cuerpo = ('{"productos": [{"nombre_ticket": "COSA RARA", "cantidad": 1, '
                  '"unidad": "ud", "producto_id": 4242}]}')
        with motor_falso([_texto(cuerpo)]) as (motor, _):
            resultado = motor.procesar(_png(400, 400), CATALOGO)

        self.assertIsNone(resultado["productos"][0]["producto_id"])
        self.assertEqual(resultado["productos"][0]["nombre_ticket"], "COSA RARA")

    def test_unidades_y_cantidades_se_normalizan(self):
        cuerpo = """{"productos": [
          {"nombre_ticket": "Queso", "cantidad": "250", "unidad": "Gramos", "producto_id": null},
          {"nombre_ticket": "Refresco", "cantidad": 33, "unidad": "cl", "producto_id": null},
          {"nombre_ticket": "Agua", "cantidad": 6, "unidad": "botella", "producto_id": null},
          {"nombre_ticket": "Raro", "cantidad": -2, "unidad": "chorrada", "producto_id": null}
        ]}"""
        with motor_falso([_texto(cuerpo)]) as (motor, _):
            productos = motor.procesar(_png(400, 400), CATALOGO)["productos"]

        self.assertEqual((productos[0]["cantidad"], productos[0]["unidad"]), (250.0, "g"))
        # 33 cl son 330 ml, no 33.
        self.assertEqual((productos[1]["cantidad"], productos[1]["unidad"]), (330.0, "ml"))
        self.assertEqual((productos[2]["cantidad"], productos[2]["unidad"]), (6.0, "ud"))
        # Cantidad imposible y unidad desconocida caen a los valores seguros.
        self.assertEqual((productos[3]["cantidad"], productos[3]["unidad"]), (1.0, "ud"))

    def test_articulos_sin_nombre_se_descartan(self):
        cuerpo = """{"productos": [
          {"nombre_ticket": "   ", "cantidad": 1, "unidad": "ud", "producto_id": null},
          {"nombre_ticket": "Pan integral", "cantidad": 1, "unidad": "ud", "producto_id": 9}
        ]}"""
        with motor_falso([_texto(cuerpo)]) as (motor, _):
            productos = motor.procesar(_png(400, 400), CATALOGO)["productos"]

        self.assertEqual([p["nombre_ticket"] for p in productos], ["Pan integral"])


class CompatibilidadSdkTests(unittest.TestCase):
    def test_sdk_antiguo_reintenta_sin_esquema_y_parsea_markdown(self):
        """Un SDK sin structured outputs lanza TypeError; hay que reintentar
        sin esquema y aceptar el JSON envuelto en markdown."""
        cuerpo = ('```json\n{"productos": [{"nombre_ticket": "PAN", "cantidad": 1, '
                  '"unidad": "ud", "producto_id": 9}]}\n```')
        with motor_falso(
            [_texto(cuerpo)],
            errores=[TypeError("unexpected keyword argument 'output_config'")],
        ) as (motor, creado):
            resultado = motor.procesar(_png(400, 400), CATALOGO)
            llamadas = creado["cliente"].messages.llamadas
            # La degradación se recuerda para no repetir la llamada fallida en
            # cada ticket, y por eso vive en la clase; motor_falso la restaura
            # al salir, asi que hay que comprobarla aqui dentro.
            self.assertFalse(ClaudeOCR._soporta_esquema)

        self.assertEqual(len(llamadas), 2)
        self.assertIn("output_config", llamadas[0])
        self.assertNotIn("output_config", llamadas[1])
        self.assertEqual(resultado["productos"][0]["producto_id"], 9)

    def test_api_que_rechaza_output_config_reintenta_sin_esquema(self):
        cuerpo = '{"productos": [{"nombre_ticket": "PAN", "cantidad": 1, "unidad": "ud", "producto_id": 9}]}'
        with motor_falso(
            [_texto(cuerpo)],
            errores=[ValueError("output_config: unsupported parameter")],
        ) as (motor, creado):
            resultado = motor.procesar(_png(400, 400), CATALOGO)

        self.assertEqual(len(creado["cliente"].messages.llamadas), 2)
        self.assertEqual(len(resultado["productos"]), 1)


class ImagenYPdfTests(unittest.TestCase):
    def test_tira_alta_se_trocea_conservando_el_ancho(self):
        trozos = claude_ocr._preparar_imagenes(_png(1200, 5000))
        self.assertGreater(len(trozos), 1)
        anchos = {Image.open(io.BytesIO(datos)).size[0] for _, datos in trozos}
        # Reducir la tira entera dejaria el texto ilegible: los fragmentos
        # tienen que salir a resolucion nativa.
        self.assertEqual(anchos, {1200})
        for _, datos in trozos:
            self.assertLessEqual(max(Image.open(io.BytesIO(datos)).size), claude_ocr._LADO_MAXIMO)

    def test_documento_con_forma_de_pagina_va_en_una_sola_imagen(self):
        trozos = claude_ocr._preparar_imagenes(_png(3000, 4200))
        self.assertEqual(len(trozos), 1)

    def test_imagen_ilegible_se_envia_tal_cual(self):
        trozos = claude_ocr._preparar_imagenes(b"esto-no-es-una-imagen")
        self.assertEqual(len(trozos), 1)
        self.assertEqual(trozos[0][1], b"esto-no-es-una-imagen")

    def test_ticket_troceado_manda_varias_imagenes_y_avisa_del_solape(self):
        with motor_falso([_texto('{"productos": []}')]) as (motor, creado):
            motor.procesar(_png(1200, 5000), CATALOGO)
            contenido = creado["cliente"].messages.llamadas[0]["messages"][0]["content"]

        imagenes = [b for b in contenido if b["type"] == "image"]
        self.assertGreater(len(imagenes), 1)
        self.assertIn("solape", contenido[-1]["text"])

    def test_articulo_repetido_en_el_solape_se_cuenta_una_vez(self):
        cuerpo = """{"productos": [
          {"nombre_ticket": "LECHE ENTERA 1L", "cantidad": 2, "unidad": "ud", "producto_id": 7},
          {"nombre_ticket": "leche entera 1l", "cantidad": 2, "unidad": "ud", "producto_id": 7},
          {"nombre_ticket": "PAN INTEGRAL", "cantidad": 1, "unidad": "ud", "producto_id": 9}
        ]}"""
        with motor_falso([_texto(cuerpo)]) as (motor, _):
            productos = motor.procesar(_png(1200, 5000), CATALOGO)["productos"]

        self.assertEqual(len(productos), 2)
        self.assertEqual(productos[0]["cantidad"], 2)

    def test_sin_trocear_no_se_deduplica(self):
        """En un ticket de una sola imagen el mismo articulo puede aparecer
        legitimamente en dos lineas seguidas."""
        cuerpo = """{"productos": [
          {"nombre_ticket": "AGUA 1,5L", "cantidad": 1, "unidad": "ud", "producto_id": null},
          {"nombre_ticket": "AGUA 1,5L", "cantidad": 1, "unidad": "ud", "producto_id": null}
        ]}"""
        with motor_falso([_texto(cuerpo)]) as (motor, _):
            productos = motor.procesar(_png(600, 800), CATALOGO)["productos"]

        self.assertEqual(len(productos), 2)

    def test_pdf_se_manda_como_documento_no_como_imagen(self):
        """Asi Claude lee todas las paginas de una factura; rasterizando solo
        se leia la primera."""
        pdf = b"%PDF-1.4\n" + b"0" * 200
        with motor_falso([_texto('{"productos": []}')]) as (motor, creado):
            motor.procesar(pdf, CATALOGO, mime="application/pdf")
            contenido = creado["cliente"].messages.llamadas[0]["messages"][0]["content"]

        self.assertEqual(contenido[0]["type"], "document")
        self.assertEqual(contenido[0]["source"]["media_type"], "application/pdf")
        self.assertFalse([b for b in contenido if b["type"] == "image"])

    def test_pdf_se_detecta_por_su_firma_sin_pista_de_mime(self):
        pdf = b"%PDF-1.7\n" + b"0" * 100
        with motor_falso([_texto('{"productos": []}')]) as (motor, creado):
            motor.procesar(pdf, CATALOGO)
            contenido = creado["cliente"].messages.llamadas[0]["messages"][0]["content"]

        self.assertEqual(contenido[0]["type"], "document")


if __name__ == "__main__":
    unittest.main()
