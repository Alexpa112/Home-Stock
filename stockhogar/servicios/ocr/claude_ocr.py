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

_PROMPT = """EXTRAE TODOS LOS ARTÍCULOS DEL TICKET - SIN EXCEPCIONES.

Tu ÚNICO objetivo: Leer el ticket de compra y devolver TODOS los artículos comprados.

═══════════════════════════════════════════════════════════════════════════════
IDENTIFICAR ARTÍCULOS - QUÉ ES UN ARTÍCULO:

Un ARTÍCULO es cualquier línea que tenga:
  ✓ Nombre del producto (pan, leche, tomates, etc.)
  ✓ Más un precio (junto o cerca)
  ✓ Opcionalmente cantidad (2x, 500g, 1L, etc.)

INCLUIR TODO:
  ✓ Frutas, verduras, alimentos frescos
  ✓ Lácteos, carnes, pescado, huevos
  ✓ Pan, cereales, pastas, arroz
  ✓ Bebidas, refrescos, zumos, vino
  ✓ Alimentos envasados, conservas
  ✓ Productos de higiene, limpieza, droguería
  ✓ Cualquier cosa con nombre + precio = ARTÍCULO

NO INCLUIR (ignorar completamente):
  ✗ ENCABEZADO: nombre tienda, fecha, hora, cajero, sucursal
  ✗ PIE: TOTAL, SUBTOTAL, SUB, IMPORTE, IVA, forma de pago, método pago
  ✗ VUELTAS, EFECTIVO, CAMBIO RECIBIDO
  ✗ LÍNEAS VACÍAS O SIN PRECIO
  ✗ "Gracias por su compra", mensajes de publicidad

═══════════════════════════════════════════════════════════════════════════════
EXTRAER 3 DATOS POR CADA ARTÍCULO:

1. nombre_ticket: El NOMBRE EXACTO que aparece en el ticket
   • Copia palabra por palabra lo que dice
   • Incluyendo tamaño si aparece (1L, 500g, 6 unidades, docena)
   • Ejemplo: si dice "Leche 1L 3.50", escribe "Leche 1L"
   • Si dice "Pan blanco", escribe "Pan blanco"

2. cantidad: El NÚMERO de cosas compradas
   • Si dice "2x" o "2 x" → cantidad = 2
   • Si dice "1 kg" → cantidad = 1 (el kg es la unidad, no cantidad)
   • Si dice "6 huevos" → cantidad = 6 (son 6 unidades)
   • Si NO dice cantidad → cantidad = 1 (asume 1 unidad)
   • Siempre un NÚMERO, nunca texto

3. unidad: Cómo se mide (ud, kg, g, l, ml)
   • "ud" = unidades simples (pan, latas, botellas individuales)
   • "kg" = kilogramos (para alimentos a granel)
   • "g" = gramos (para cantidades pequeñas)
   • "l" = litros (para líquidos)
   • "ml" = mililitros (para medicinas o cantidades muy pequeñas)
   • Si NO hay unidad especificada → "ud"

EJEMPLOS DE EXTRACCIÓN:
  Línea: "Leche entera 1L              3.99"
    → nombre_ticket: "Leche entera 1L", cantidad: 1, unidad: "ud"

  Línea: "Tomates                2 kg  8.99"
    → nombre_ticket: "Tomates", cantidad: 2, unidad: "kg"

  Línea: "2x Chocolate 100g            5.98"
    → nombre_ticket: "Chocolate 100g", cantidad: 2, unidad: "ud"

  Línea: "Manzanas rojas           6.99/kg"
    → nombre_ticket: "Manzanas rojas", cantidad: 1, unidad: "kg"

═══════════════════════════════════════════════════════════════════════════════
CATÁLOGO (usa producto_id si hay match):

{catalogo}

Para CADA artículo:
  • Busca si existe algo similar en el catálogo
  • Si SÍ → usa su "producto_id"
  • Si NO → producto_id = null

═══════════════════════════════════════════════════════════════════════════════
DEVOLVER SOLO JSON - EXACTAMENTE ASÍ:

{{"productos": [
  {{"nombre_ticket": "Leche 1L", "cantidad": 1, "unidad": "ud", "producto_id": 5}},
  {{"nombre_ticket": "Tomates", "cantidad": 2, "unidad": "kg", "producto_id": 12}},
  {{"nombre_ticket": "Pan integral", "cantidad": 1, "unidad": "ud", "producto_id": null}}
]}}

CRUCIAL:
  • SIN EXPLICACIONES
  • SIN COMILLAS ADICIONALES
  • SIN MARKDOWN (no escribas ```json)
  • SOLO EL JSON
  • Si está vacío: {{"productos": []}}
  • Validación: cantidad es NÚMERO, unidad es uno de: ud/kg/g/l/ml
  • Todos los campos DEBEN estar presentes

TAREA FINAL: Lee LÍNEA POR LÍNEA el ticket, extrae TODOS los artículos,
devuelve SOLO el JSON."""


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
                max_tokens=2048,
                timeout=_TIMEOUT_SEGUNDOS,
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
            logger.info("Claude OCR devolvió respuesta: %s caracteres", len(texto))

            # Extraer JSON (puede tener markdown o explicaciones)
            json_limpio = texto

            # Intenta limpiar markdown
            if "```json" in json_limpio:
                json_limpio = json_limpio.split("```json")[1].split("```")[0].strip()
            elif "```" in json_limpio:
                json_limpio = json_limpio.split("```")[1].split("```")[0].strip()

            # Busca el JSON dentro del texto (por si hay explicaciones)
            if not json_limpio.startswith("{"):
                inicio = json_limpio.find("{")
                if inicio != -1:
                    json_limpio = json_limpio[inicio:]

            if not json_limpio.endswith("}"):
                final = json_limpio.rfind("}")
                if final != -1:
                    json_limpio = json_limpio[:final+1]

            logger.debug("JSON extraído: %s", json_limpio[:200])

            resultado = json.loads(json_limpio)
            if not isinstance(resultado, dict) or "productos" not in resultado:
                logger.error("Claude devolvió formato inválido: %s", resultado)
                return None

            # Validar que todos los productos tienen los campos requeridos
            productos = resultado.get("productos", [])
            for i, prod in enumerate(productos):
                if not isinstance(prod, dict):
                    logger.warning("Producto %d no es dict: %s", i, prod)
                    continue
                if "nombre_ticket" not in prod:
                    prod["nombre_ticket"] = prod.get("nombre", "")
                if "cantidad" not in prod:
                    prod["cantidad"] = 1
                if "unidad" not in prod:
                    prod["unidad"] = "ud"
                if "producto_id" not in prod:
                    prod["producto_id"] = None

            logger.info("Claude OCR detectó %d productos", len(productos))
            return resultado

        except json.JSONDecodeError as e:
            logger.error("Error parseando JSON de Claude: %s. Respuesta: %s", e, json_limpio[:500] if 'json_limpio' in locals() else "sin respuesta")
            return None
        except Exception as e:
            logger.exception("Fallo llamando a Claude OCR: %s - %s", type(e).__name__, str(e))
            return None
