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

_PROMPT = """TAREA CRÍTICA: Extraer TODOS los artículos de este documento (ticket/factura/nota)

Soy un sistema de compras. Necesito TODOS los artículos comprados para registrar stock.
NO puedo perder ni UN artículo. Tu precisión es CRÍTICA.

═══════════════════════════════════════════════════════════════════════════════
FORMATOS SOPORTADOS - Reconoce cualquier layout:

1. TICKET TRADICIONAL (supermercado)
   Leche 1L                     3.99
   Pan integral x2              4.50

2. FACTURA COMPLEJA (columnas)
   Código | Producto          | Cant | Unidad | Precio
   1234   | Tomates frescos   | 2    | kg     | 8.99

3. FACTURAS CON RESUMEN (con cabecera/pie)
   --- ARTICULOS ---
   Arroz 1kg ... 5.50
   --- TOTAL: 25.00 ---

4. LISTA SIMPLE (sin precios visibles)
   - Leche
   - Pan x2
   - Tomates 3kg

5. TABLA/MATRIZ (datos distribuidos)
   Item 1: Producto | 2x | 7.99
   Item 2: Producto | 1kg | 12.50

═══════════════════════════════════════════════════════════════════════════════
ESTRATEGIA DE LECTURA - Flexible según formato:

LEE INTELIGENTEMENTE:
  • Columnas (si existen): producto, cantidad, unidad, precio
  • Líneas (si no hay columnas): busca nombre + número + unidad/precio
  • Tablas: cada fila puede ser un artículo
  • Listas: cada punto/línea puede ser un artículo
  • Cualquier combinación: adapta y sigue extrayendo

PATRONES DE CANTIDAD:
  • "2x Leche" → cantidad: 2
  • "Leche x2" → cantidad: 2
  • "2 botellas Leche" → cantidad: 2
  • "500g Tomates" → cantidad: 0.5, unidad: kg
  • "Leche 1000ml" → cantidad: 1, unidad: l
  • "6 huevos" → cantidad: 6
  • "docena huevos" → cantidad: 12
  • "media docena" → cantidad: 6
  • "2 litros" → cantidad: 2, unidad: l
  • "250g queso" → cantidad: 0.25, unidad: kg
  • Solo nombre (sin cantidad) → cantidad: 1

PATRONES DE UNIDAD (detecta automáticamente):
  "kg", "kilos", "kilo" → kg
  "g", "gr", "gramo", "gramos" → g
  "l", "litro", "litros" → l
  "ml", "mililitro", "mililitros" → ml
  "botella", "bote", "unidad", "pieza", "pan", "lata", "caja" → ud
  "docena", "media docena" → 12 o 6 unidades
  "paquete", "bolsa", "pack", "bundle" → ud
  Si no hay unidad clara → ud (unidades)

═══════════════════════════════════════════════════════════════════════════════
QUÉ INCLUIR (TODO LO QUE SEA PRODUCTO):

  ✓ ALIMENTOS FRESCOS: frutas, verduras, carnes, pescado, aves, huevos
  ✓ LÁCTEOS: leche, queso, yogur, mantequilla, nata
  ✓ PANADERÍA: pan, bollo, galletas, pasteles
  ✓ BEBIDAS: agua, refrescos, zumos, vino, cerveza, licores, café, té
  ✓ CONSERVAS: latas, botes, frascos, productos enlatados
  ✓ SECOS: arroz, pasta, legumbres, cereales, harina, azúcar
  ✓ CONGELADOS: pizzas, verduras congeladas, helado
  ✓ HIGIENE: champú, jabón, dentífrico, desodorante, papel higiénico
  ✓ LIMPIEZA: detergente, limpiavidrios, lejía, bayeta, esponja
  ✓ DROGUERÍA: bolsas, film, papel aluminio, velas, pilas
  ✓ MASCOTAS: comida perros, comida gatos, arena gatos
  ✓ OTROS CONSUMIBLES: cigarrillos, revistas, libros

QUÉ EXCLUIR (NO son artículos de compra):

  ✗ ENCABEZADOS: "Supermercado XXX", "Tienda", "Fecha:", "Hora:", "Caja:", número de tienda
  ✗ COLUMNAS DESCRIPTIVAS: "Artículo", "Cantidad", "Precio", "Descripción"
  ✗ TOTAL/RESUMEN: TOTAL, SUBTOTAL, SUB, SUMA, IVA, Impuesto, IMPORTE TOTAL
  ✗ MÉTODOS PAGO: Tarjeta, Efectivo, Transferencia, cheque, forma de pago
  ✗ VUELTAS/CAMBIO: "Vueltas", "Cambio recibido", "Resto"
  ✗ GASTOS ADICIONALES: Bolsas (si se cobran), embalaje, envío, recargo
  ✗ DESCUENTOS/OFERTAS: líneas que digan "DESCUENTO", "OFERTA", "PROMOCIÓN" (si no son productos)
  ✗ PIE: "Gracias", "Vuelva pronto", "Aviso legal", datos de contacto
  ✗ CÓDIGOS: códigos de barras, números de referencia sin producto
  ✗ LÍNEAS VACÍAS

═══════════════════════════════════════════════════════════════════════════════
EXTRACCIÓN FINAL - 4 DATOS POR ARTÍCULO:

1. nombre_ticket: Nombre EXACTO del producto (sin precio ni cantidad)
   • "Leche entera 1L" → nombre: "Leche entera 1L" (incluye tamaño si está en el nombre)
   • "Tomates" → nombre: "Tomates"
   • "Pan integral 500g" → nombre: "Pan integral 500g"
   • MANTÉN EL NOMBRE COMPLETO TAL CUAL APARECE

2. cantidad: NÚMERO (puede ser decimal para kilos/gramos/ml)
   • Conversión automática: 500g = 0.5 kg, 250ml = 0.25 l
   • Siempre positivo y > 0
   • Si no aparece → 1

3. unidad: Uno de estos EXACTAMENTE: ud, kg, g, l, ml
   • NUNCA otras unidades
   • "botella", "lata", "caja" → ud
   • "gramos", "gr" → g (y ajusta cantidad)
   • "litros", "l" → l
   • Si no hay unidad → ud

4. producto_id: Busca en catálogo
   • Si hay match exacto o muy similar → usa el id
   • Si no hay match → null

CATÁLOGO:
{catalogo}

═══════════════════════════════════════════════════════════════════════════════
EJEMPLOS VARIADOS (diferentes formatos):

TICKET FORMATO 1:
  Leche 1L                      3.99
  Resultado: nombre:"Leche 1L", cantidad:1, unidad:"ud"

TICKET FORMATO 2:
  Tomates frescos 2kg @ 4.50/kg
  Resultado: nombre:"Tomates frescos", cantidad:2, unidad:"kg"

FACTURA FORMATO 1:
  Producto | Cantidad | Precio
  Pan      | 2        | 3.50
  Resultado: nombre:"Pan", cantidad:2, unidad:"ud"

FACTURA FORMATO 2:
  Arroz 1kg........................5.50
  Resultado: nombre:"Arroz 1kg", cantidad:1, unidad:"ud"

LISTA SIMPLE:
  - Leche 3 litros
  Resultado: nombre:"Leche", cantidad:3, unidad:"l"

TABLA:
  [Producto] [Cant] [Precio]
  Queso      250g   12.00
  Resultado: nombre:"Queso", cantidad:0.25, unidad:"kg"

═══════════════════════════════════════════════════════════════════════════════
RESPUESTA FINAL - JSON PURO:

{{"productos": [
  {{"nombre_ticket": "Leche 1L", "cantidad": 1, "unidad": "ud", "producto_id": null}},
  {{"nombre_ticket": "Tomates", "cantidad": 2, "unidad": "kg", "producto_id": null}},
  {{"nombre_ticket": "Pan integral", "cantidad": 3, "unidad": "ud", "producto_id": null}}
]}}

INSTRUCCIONES FINALES:
  • SOLO DEVUELVE JSON - nada más
  • SIN markdown, SIN comillas extras, SIN explicaciones
  • SIN ```json, SIN ```
  • Si está vacío: {{"productos": []}}
  • Cantidad SIEMPRE número (puede ser decimal: 0.5, 1.25, etc)
  • Unidad SIEMPRE uno de: ud / kg / g / l / ml
  • Todos los 4 campos SIEMPRE presentes

ÚLTIMA INSTRUCCIÓN: Lee el documento línea por línea. Extrae TODOS los artículos
sin perder ni uno. Duda siempre a INCLUIR (es mejor pedir corrección que perder datos).
Devuelve JSON válido, parseable, en una sola respuesta."""


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
            productos_validos = []

            for i, prod in enumerate(productos):
                if not isinstance(prod, dict):
                    logger.warning("Producto %d no es dict, saltando: %s", i, prod)
                    continue

                # Validar nombre
                nombre = (prod.get("nombre_ticket") or prod.get("nombre") or "").strip()
                if not nombre:
                    logger.warning("Producto %d sin nombre, saltando", i)
                    continue

                # Validar y convertir cantidad
                try:
                    cantidad = float(prod.get("cantidad") or 1)
                    if cantidad <= 0:
                        cantidad = 1
                except (ValueError, TypeError):
                    logger.warning("Producto %d cantidad inválida: %s, usando 1", i, prod.get("cantidad"))
                    cantidad = 1

                # Validar unidad
                unidad = (prod.get("unidad") or "ud").strip().lower()
                if unidad not in ("ud", "kg", "g", "l", "ml"):
                    logger.debug("Producto %d unidad inválida '%s', normalizando a 'ud'", i, unidad)
                    unidad = "ud"

                # Producto ID (puede ser None)
                producto_id = prod.get("producto_id")
                if producto_id == "null" or producto_id == "":
                    producto_id = None
                else:
                    try:
                        producto_id = int(producto_id) if producto_id is not None else None
                    except (ValueError, TypeError):
                        producto_id = None

                producto_validado = {
                    "nombre_ticket": nombre,
                    "cantidad": cantidad,
                    "unidad": unidad,
                    "producto_id": producto_id
                }
                productos_validos.append(producto_validado)
                logger.debug("Producto válido: %s", producto_validado)

            resultado["productos"] = productos_validos
            logger.info("Claude OCR detectó %d productos válidos", len(productos_validos))
            return resultado

        except json.JSONDecodeError as e:
            logger.error("Error parseando JSON de Claude: %s. Respuesta: %s", e, json_limpio[:500] if 'json_limpio' in locals() else "sin respuesta")
            return None
        except Exception as e:
            logger.exception("Fallo llamando a Claude OCR: %s - %s", type(e).__name__, str(e))
            return None
