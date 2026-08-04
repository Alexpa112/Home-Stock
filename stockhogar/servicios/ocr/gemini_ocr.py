"""Reconocimiento de tickets usando la API gratuita de Gemini (Google AI).

En vez de leer texto con Tesseract y luego adivinar a qué producto del
catálogo corresponde cada línea (frágil: abreviaturas, marcas, formatos de
ticket distintos por supermercado, ver commits de fixes en parser_mejorado.py),
se manda la foto del ticket + el catálogo de productos del usuario al modelo
y se le pide que haga OCR y emparejamiento semántico en un solo paso.

Requiere GEMINI_API_KEY en el .env. Si no está configurada, o la llamada
falla (sin conexión, cuota agotada, error de la API), `procesar` devuelve
None y gestor_ocr.py cae al pipeline local (Tesseract) como respaldo.
"""
import base64
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
_TIMEOUT_SEGUNDOS = 25

_PROMPT = """Eres un lector de tickets de supermercado. Analiza la imagen del ticket y para cada artículo comprado (ignora cabecera con nombre/dirección/CIF de la tienda, el total, la forma de pago, el cambio y cualquier publicidad o programa de fidelización) decide a qué producto del CATALOGO de abajo corresponde.

CATALOGO (id: nombre):
{catalogo}

Devuelve SOLO un JSON con esta forma exacta, sin texto adicional ni marcas de código:
{{"productos": [
  {{"nombre_ticket": "texto tal cual aparece en el ticket",
    "producto_id": <id del catálogo o null si ninguno encaja>,
    "cantidad": <número, 1 si no se indica>,
    "unidad": "ud|kg|g|l|ml"}}
]}}

Usa un producto_id solo si estás razonablemente seguro de que es el mismo artículo, aunque el nombre del ticket sea una marca, abreviatura o esté en mayúsculas recortadas distintas al nombre del catálogo (p.ej. "LECHE PASC 1L" corresponde a "Leche entera" si esa es la entrada del catálogo). Si ningún producto del catálogo corresponde, pon producto_id a null."""


class GeminiOCR:
    """Motor de reconocimiento de tickets basado en la API gratuita de Gemini."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    def disponible(self) -> bool:
        return bool(self.api_key)

    def procesar(self, imagen_bytes: bytes, productos_catalogo: list, mime_type: str = "image/jpeg") -> dict:
        """Analiza el ticket y devuelve productos emparejados con el catálogo.

        Args:
            imagen_bytes: foto del ticket (jpg/png/etc, tal cual la sube el usuario)
            productos_catalogo: lista de dicts con al menos {"id", "nombre"}
            mime_type: tipo MIME real de imagen_bytes (jpg por defecto si no se indica)

        Returns:
            dict {"productos": [...]} o None si la llamada falla (el llamador
            debe caer al pipeline local en ese caso).
        """
        if not self.disponible():
            return None

        catalogo_texto = "\n".join(
            f"{p['id']}: {p['nombre']}" for p in productos_catalogo
        ) or "(catálogo vacío)"
        prompt = _PROMPT.format(catalogo=catalogo_texto)

        cuerpo = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(imagen_bytes).decode("ascii"),
                        }
                    },
                ]
            }],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            respuesta = requests.post(
                _ENDPOINT,
                params={"key": self.api_key},
                json=cuerpo,
                timeout=_TIMEOUT_SEGUNDOS,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto = datos["candidates"][0]["content"]["parts"][0]["text"]
            resultado = json.loads(texto)
            if not isinstance(resultado, dict) or "productos" not in resultado:
                return None
            return resultado
        except Exception:
            logger.exception("Fallo llamando a Gemini OCR, se usará el pipeline local")
            return None
