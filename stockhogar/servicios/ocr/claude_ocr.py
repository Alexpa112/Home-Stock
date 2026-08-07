"""OCR de tickets usando Claude API (gratuita, la mejor para leer documentos).

Claude tiene el mejor modelo de visión disponible gratuitamente: entiende
tickets, facturas, documentos con OCR + comprensión semántica en un paso.

Requiere ANTHROPIC_API_KEY en .env (gratuita sin tarjeta en https://console.anthropic.com).
Sin esta clave, cae al pipeline local (Tesseract) como respaldo.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_TIMEOUT_SEGUNDOS = 30

_PROMPT = """Eres un lector de tickets de supermercado. Analiza la imagen del ticket y para cada artículo comprado (ignora cabecera con nombre/dirección/CIF de la tienda, el total, la forma de pago, el cambio y cualquier publicidad) decide a qué producto del CATALOGO corresponde.

CATALOGO (id: nombre):
{catalogo}

Devuelve SOLO un JSON con esta forma exacta, sin texto adicional ni markdown:
{{"productos": [
  {{"nombre_ticket": "texto tal cual aparece en el ticket",
    "producto_id": <id del catálogo o null si ninguno encaja>,
    "cantidad": <número, 1 si no se indica>,
    "unidad": "ud|kg|g|l|ml"}}
]}}

Sé preciso: si hay 2kg de manzanas a 1.20/kg, pon cantidad: 2, unidad: "kg".
Usa un producto_id solo si estás seguro de que es el mismo artículo."""


class ClaudeOCR:
    """Motor de OCR basado en Claude API (gratuita)."""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package no instalado, usando Tesseract")

    def disponible(self) -> bool:
        return bool(self.client and self.api_key)

    def procesar(self, imagen_bytes: bytes, productos_catalogo: list) -> Optional[dict]:
        """Analiza el ticket con Claude Vision y devuelve productos emparejados.

        Args:
            imagen_bytes: foto del ticket (jpg/png/etc)
            productos_catalogo: lista de dicts con {"id", "nombre"}

        Returns:
            dict {"productos": [...]} o None si la llamada falla
        """
        if not self.disponible():
            return None

        catalogo_texto = "\n".join(
            f"{p['id']}: {p['nombre']}" for p in productos_catalogo
        ) or "(catálogo vacío)"
        prompt = _PROMPT.format(catalogo=catalogo_texto)

        try:
            import base64

            # Detectar MIME type desde primeros bytes
            if imagen_bytes[:3] == b'\xff\xd8\xff':
                mime_type = "image/jpeg"
            elif imagen_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                mime_type = "image/png"
            elif imagen_bytes[:6] in (b'GIF87a', b'GIF89a'):
                mime_type = "image/gif"
            elif imagen_bytes[:2] == b'BM':
                mime_type = "image/bmp"
            else:
                mime_type = "image/jpeg"  # Default

            data_url = base64.standard_b64encode(imagen_bytes).decode('ascii')

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": data_url,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            texto = message.content[0].text.strip()

            # Extraer JSON (puede tener markdown)
            if "```json" in texto:
                texto = texto.split("```json")[1].split("```")[0].strip()
            elif "```" in texto:
                texto = texto.split("```")[1].split("```")[0].strip()

            resultado = json.loads(texto)
            if not isinstance(resultado, dict) or "productos" not in resultado:
                return None
            return resultado

        except Exception:
            logger.exception("Fallo llamando a Claude OCR, se usará pipeline local")
            return None
