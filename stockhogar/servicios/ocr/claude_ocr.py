"""OCR de tickets con Claude Vision (motor principal del escáner).

Claude lee la foto (o el PDF) del ticket y devuelve directamente los
artículos comprados con su cantidad, ya emparejados contra el catálogo del
hogar: OCR + comprensión del documento en una sola llamada.

Requiere ANTHROPIC_API_KEY (ver .env.example). Sin esa clave, sin el paquete
`anthropic` instalado, o si la llamada falla (sin red, cuota agotada...), el
flujo cae al pipeline local con Tesseract (ver gestor_ocr.py / rutas/tickets.py).

Decisiones de diseño que afectan a la fiabilidad del reconocimiento:

* El formato de la respuesta se impone con `output_config.format` (structured
  outputs), no pidiéndolo en el prompt: la API garantiza un JSON que valida
  contra el esquema, así que no hay que reparar markdown ni comillas. Se
  mantiene el parseo tolerante como respaldo para SDKs antiguos que no
  aceptan ese parámetro.
* Los tickets de supermercado son tiras muy altas y estrechas. Reducirlas de
  golpe al lado máximo que acepta la API deja el texto ilegible, así que se
  parten en fragmentos verticales solapados que se envían en la misma
  llamada, cada uno a resolución nativa (ver `_preparar_imagenes`).
* `_MAX_TOKENS` tiene que dar de sí para un ticket largo *y* para el
  razonamiento del modelo (ambos salen del mismo presupuesto): con los 2048
  de la versión anterior, un ticket de compra grande se cortaba por la mitad
  y se perdían artículos.
"""
import base64
import io
import json
import logging
import math
import os
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_MODELO = "claude-opus-5"
# Escalera de timeouts del escaneo, de dentro afuera. Cada capa deja margen
# sobre la de dentro para que el usuario vea el error de quien realmente falló
# y no un corte a mitad:
#
#   llamada a la API   180 s  (aquí)
#   worker de gunicorn 240 s  (--timeout, Dockerfile y Dockerfile.raspbian)
#   abort del frontend 270 s  (apiUpload en lib/api.ts)
#
# Los 60 s entre la API y gunicorn cubren la subida de la foto, el troceado y
# el emparejado contra el catálogo. Si se cambia uno de los tres, hay que
# revisar los otros dos: con gunicorn por debajo de la llamada, el worker
# muere a mitad del análisis y el usuario recibe un error genérico.
_TIMEOUT_SEGUNDOS = 180
# Un ticket de compra grande no cabe en 2048 tokens (el presupuesto anterior),
# y el razonamiento del modelo sale del mismo saco que la respuesta.
_MAX_TOKENS = 16000
_MAX_REINTENTOS = 3
# "high" es el mínimo recomendado para tareas donde importa la precisión, y
# leer un ticket arrugado o con poca luz lo es. Cuesta más tiempo que "medium",
# que es justo lo que compra la escalera de timeouts de arriba.
_ESFUERZO = "high"

# Lado máximo (px) que aprovecha la banda de alta resolución del modelo.
# Por encima solo se gastan tokens de imagen sin ganar detalle.
_LADO_MAXIMO = 2576
# Un documento se trocea si es al menos esta proporción más alto que ancho.
# Por debajo (una factura A4 fotografiada) una sola imagen ya da resolución
# de sobra y trocear solo añade coste.
_RATIO_TROCEO = 1.6
_MAX_TROZOS = 10
_SOLAPE = 0.12
# Alto útil de cada fragmento *antes* de añadirle el solape, elegido para que
# el recorte final (fragmento + solape por arriba y por abajo) quepa ya dentro
# de `_LADO_MAXIMO`. Si no se reserva ese margen, el recorte se pasa del lado
# máximo y hay que reducirlo, y esa reducción encoge también el ancho: el
# texto acaba con menos píxeles de alto justo en el troceado que pretendía
# conservarlos.
_ALTO_TROZO = int(_LADO_MAXIMO / (1 + 2 * _SOLAPE))

_UNIDADES_VALIDAS = ("ud", "kg", "g", "l", "ml")

# Variantes que el modelo puede devolver pese al enum del esquema (y que sí
# devuelven los SDKs antiguos, que van por el camino sin esquema).
_ALIAS_UNIDADES = {
    "u": "ud", "uds": "ud", "unidad": "ud", "unidades": "ud",
    "pz": "ud", "pieza": "ud", "piezas": "ud", "bote": "ud",
    "botella": "ud", "lata": "ud", "caja": "ud", "paq": "ud",
    "paquete": "ud", "pack": "ud", "bolsa": "ud", "docena": "ud",
    "kilo": "kg", "kilos": "kg", "kgs": "kg",
    "gr": "g", "grs": "g", "gramo": "g", "gramos": "g",
    "lt": "l", "litro": "l", "litros": "l",
    "mililitro": "ml", "mililitros": "ml",
}
# Unidades que hay que convertir, no solo renombrar.
_CONVERSIONES_UNIDAD = {"cl": ("ml", 10.0)}

_FIRMAS_MIME = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"%PDF-", "application/pdf"),
)

_ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "productos": {
            "type": "array",
            "description": "Un elemento por línea de artículo del documento.",
            "items": {
                "type": "object",
                "properties": {
                    "nombre_ticket": {
                        "type": "string",
                        "description": "Nombre del artículo, sin precio ni cantidad.",
                    },
                    "cantidad": {
                        "type": "number",
                        "description": "Unidades, peso o volumen comprados. 1 si no consta.",
                    },
                    "unidad": {
                        "type": "string",
                        "enum": list(_UNIDADES_VALIDAS),
                    },
                    "producto_id": {
                        "description": "Id del catálogo, o null si no hay correspondencia clara.",
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                    },
                },
                "required": ["nombre_ticket", "cantidad", "unidad", "producto_id"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["productos"],
    "additionalProperties": False,
}

_PROMPT = """Extrae todos los artículos comprados de este ticket o factura de compra.

Devuelve un elemento por línea de artículo del documento, en el mismo orden en
que aparecen. No te dejes ninguno: los artículos que falten no llegan al stock.

Sobre cada campo:

- nombre_ticket: el nombre tal como está impreso, sin precio ni cantidad.
  Corrige los errores de lectura evidentes y desarrolla las abreviaturas
  cuando el producto sea inequívoco ("LCH ENT PASCUAL" -> "Leche entera
  Pascual"). Quita los códigos de artículo que lleve delante.
- cantidad y unidad: lo realmente comprado.
- producto_id: el id del catálogo de abajo cuando el artículo se corresponda
  claramente con uno de ellos; null en cualquier otro caso. No inventes ids.

Cantidad y unidad:

- La cantidad comprada suele ir al principio de la línea o en su propia
  columna: en "2 LECHE PASCUAL 1L" son 2 unidades, no 1 litro.
- El tamaño del envase forma parte del nombre. Úsalo como cantidad solo si la
  línea no indica ninguna otra.
- A granel el peso suele venir en la línea siguiente al nombre: "TOMATE PERA
  KG" y "0,850 kg 1,89 EUR/kg 1,61" son un único artículo de 0,85 kg.
- "2x1", "3x2" y similares marcan promoción, no cantidad.
- Docena son 12 unidades; media docena, 6.
- Conserva la unidad impresa: 500 g se queda en 500 g, no lo pases a kg.
- Si no consta cantidad, es 1 ud.

Incluye cualquier producto de compra: alimentación fresca y envasada,
congelados, bebidas, panadería, conservas, higiene, limpieza, droguería,
bazar, mascotas.

Deja fuera todo lo que no sea un artículo comprado: cabecera y pie del
documento (tienda, dirección, CIF, teléfono, fecha, caja, número de factura),
cabeceras de columna, totales y subtotales, IVA, formas de pago, cambio,
descuentos y cupones que no sean en sí un producto, puntos y saldo de
fidelización, cargos por bolsas, y cualquier texto legal o publicitario.

Si la imagen no es un ticket ni una factura de compra, devuelve la lista vacía.

Catálogo del hogar (id: nombre):
{catalogo}"""

_AVISO_TROZOS = """
Las {n} imágenes son fragmentos consecutivos del mismo documento, de arriba
abajo y solapados entre sí. Léelos como un único ticket: no repitas un
artículo que aparezca en la zona de solape de dos fragmentos.
"""


def _detectar_mime(imagen_bytes: bytes) -> str:
    """Detecta el tipo de contenido por su firma binaria."""
    for firma, mime in _FIRMAS_MIME:
        if imagen_bytes.startswith(firma):
            return mime
    return "image/jpeg"


def _preparar_imagenes(imagen_bytes: bytes) -> List[Tuple[str, bytes]]:
    """Normaliza la foto del ticket y, si hace falta, la parte en fragmentos.

    Devuelve una lista de `(mime, bytes)` en orden de lectura (de arriba
    abajo). Aplica la rotación del EXIF, ajusta el ancho al máximo que
    aprovecha el modelo y, en tiras muy altas (el ticket de supermercado
    típico), corta fragmentos verticales solapados en vez de reducir la tira
    entera: reducirla dejaría el texto por debajo del umbral de lectura.

    Si Pillow no está disponible o la imagen no se puede decodificar, se
    devuelve el original tal cual para que la llamada se intente igualmente.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:  # pragma: no cover - Pillow es dependencia del proyecto
        return [(_detectar_mime(imagen_bytes), imagen_bytes)]

    try:
        with Image.open(io.BytesIO(imagen_bytes)) as original:
            imagen = ImageOps.exif_transpose(original).convert("RGB")
    except Exception:
        logger.warning("No se pudo decodificar la imagen, se envía sin normalizar")
        return [(_detectar_mime(imagen_bytes), imagen_bytes)]

    ancho, alto = imagen.size
    if ancho > _LADO_MAXIMO:
        alto = max(1, round(alto * _LADO_MAXIMO / ancho))
        imagen = imagen.resize((_LADO_MAXIMO, alto), Image.LANCZOS)
        ancho = _LADO_MAXIMO

    if alto <= _LADO_MAXIMO:
        return [_a_jpeg(imagen)]

    if alto < ancho * _RATIO_TROCEO:
        # Documento con forma de página: una sola imagen reducida da detalle
        # de sobra y evita partir filas de una tabla.
        escala = _LADO_MAXIMO / alto
        return [_a_jpeg(imagen.resize((max(1, round(ancho * escala)), _LADO_MAXIMO), Image.LANCZOS))]

    trozos = min(_MAX_TROZOS, math.ceil(alto / _ALTO_TROZO))
    alto_trozo = math.ceil(alto / trozos)
    solape = int(alto_trozo * _SOLAPE)

    preparados = []
    for indice in range(trozos):
        arriba = max(0, indice * alto_trozo - solape)
        abajo = min(alto, (indice + 1) * alto_trozo + solape)
        if abajo - arriba < 2:
            continue
        preparados.append(_a_jpeg(imagen.crop((0, arriba, ancho, abajo))))

    logger.info(
        "Ticket de %dx%d px troceado en %d fragmentos para conservar resolución",
        ancho, alto, len(preparados),
    )
    return preparados or [_a_jpeg(imagen)]


def _a_jpeg(imagen) -> Tuple[str, bytes]:
    """Reduce la imagen al lado máximo útil y la codifica como JPEG."""
    from PIL import Image

    ancho, alto = imagen.size
    lado = max(ancho, alto)
    if lado > _LADO_MAXIMO:
        escala = _LADO_MAXIMO / lado
        imagen = imagen.resize(
            (max(1, round(ancho * escala)), max(1, round(alto * escala))), Image.LANCZOS
        )

    buffer = io.BytesIO()
    imagen.save(buffer, format="JPEG", quality=88, optimize=True)
    return "image/jpeg", buffer.getvalue()


def _normalizar_unidad(unidad, cantidad: float) -> Tuple[str, float]:
    """Lleva la unidad a una de `_UNIDADES_VALIDAS`, convirtiendo si procede."""
    texto = str(unidad or "").strip().lower().rstrip(".")
    texto = _ALIAS_UNIDADES.get(texto, texto)
    if texto in _CONVERSIONES_UNIDAD:
        texto, factor = _CONVERSIONES_UNIDAD[texto]
        cantidad *= factor
    if texto not in _UNIDADES_VALIDAS:
        texto = "ud"
    return texto, cantidad


def _normalizar_producto_id(valor, ids_catalogo) -> Optional[int]:
    """Valida el id devuelto por el modelo contra el catálogo real.

    Un id inventado (o de otro hogar) llegaría al confirmar el ticket como si
    fuera un artículo existente, así que aquí se descarta y el artículo pasa a
    tratarse como nuevo.
    """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto or texto.lower() in ("null", "none"):
            return None
        try:
            valor = int(texto)
        except ValueError:
            return None
    elif isinstance(valor, float):
        if not valor.is_integer():
            return None
        valor = int(valor)
    elif not isinstance(valor, int):
        return None

    if ids_catalogo and valor not in ids_catalogo:
        logger.warning("Claude devolvió un producto_id fuera del catálogo: %s", valor)
        return None
    return valor


def _normalizar_items(productos, ids_catalogo) -> List[dict]:
    """Limpia y valida la lista devuelta por el modelo."""
    normalizados = []
    for item in productos:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre_ticket") or item.get("nombre") or "").strip()
        if not nombre:
            continue

        try:
            cantidad = float(item.get("cantidad"))
        except (TypeError, ValueError):
            cantidad = 1.0
        if not math.isfinite(cantidad) or cantidad <= 0:
            cantidad = 1.0

        unidad, cantidad = _normalizar_unidad(item.get("unidad"), cantidad)

        normalizados.append({
            "nombre_ticket": nombre,
            "cantidad": round(cantidad, 3),
            "unidad": unidad,
            "producto_id": _normalizar_producto_id(item.get("producto_id"), ids_catalogo),
        })
    return normalizados


def _deduplicar_solape(items: List[dict]) -> List[dict]:
    """Quita el artículo repetido en la zona de solape de dos fragmentos.

    Solo se aplica cuando el ticket se ha troceado, y solo a repeticiones
    consecutivas idénticas: en un ticket sin trocear el mismo artículo puede
    aparecer legítimamente dos veces seguidas.
    """
    limpios: List[dict] = []
    for item in items:
        anterior = limpios[-1] if limpios else None
        if (
            anterior
            and anterior["nombre_ticket"].casefold() == item["nombre_ticket"].casefold()
            and anterior["cantidad"] == item["cantidad"]
            and anterior["unidad"] == item["unidad"]
        ):
            continue
        limpios.append(item)
    return limpios


def _extraer_json(texto: str) -> Optional[dict]:
    """Parsea la respuesta cuando no se pudo usar structured outputs.

    El modelo puede envolver el JSON en markdown o acompañarlo de texto, así
    que se limpia la valla de código y se recorta al primer objeto completo.
    """
    limpio = texto.strip()
    if "```" in limpio:
        trozos = limpio.split("```")
        if len(trozos) >= 2:
            limpio = trozos[1]
            if limpio.lower().startswith("json"):
                limpio = limpio[4:]
            limpio = limpio.strip()

    inicio = limpio.find("{")
    final = limpio.rfind("}")
    if inicio == -1 or final <= inicio:
        return None

    try:
        return json.loads(limpio[inicio:final + 1])
    except json.JSONDecodeError as error:
        logger.error("Respuesta de Claude no parseable: %s (%s)", error, limpio[:300])
        return None


class ClaudeOCR:
    """Motor de OCR de tickets basado en Claude Vision."""

    # De clase, no de instancia: rutas/tickets.py construye un ClaudeOCR por
    # peticion, asi que un flag de instancia volveria a intentar (y a fallar)
    # la llamada con esquema en cada ticket.
    _soporta_esquema = True

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if not self.api_key:
            return
        try:
            import anthropic
        except ImportError:
            logger.warning(
                "ANTHROPIC_API_KEY configurada pero el paquete 'anthropic' no está "
                "instalado: el escáner usará Tesseract. Instala con: pip install anthropic"
            )
            return
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=_MAX_REINTENTOS)
        except Exception:
            # Un fallo al construir el cliente (SDK incompatible, clave con un
            # formato que rechaza) no debe tumbar el analisis del ticket: se
            # deja el motor como no disponible y el flujo cae a Tesseract.
            logger.exception("No se pudo inicializar el cliente de Claude")
            self.client = None

    def disponible(self) -> bool:
        return bool(self.client and self.api_key)

    def procesar(self, imagen_bytes: bytes, productos_catalogo: list, mime: str = None) -> Optional[dict]:
        """Analiza el ticket y devuelve los artículos emparejados.

        Args:
            imagen_bytes: foto del ticket, o el PDF de una factura.
            productos_catalogo: lista de dicts con al menos {"id", "nombre"}.
            mime: tipo de contenido si se conoce. "application/pdf" envía el
                documento tal cual (así se leen todas las páginas de una
                factura, no solo la primera).

        Returns:
            dict {"productos": [...]} ya normalizado, o None si la llamada
            falla (el llamante debe caer entonces al pipeline local).
        """
        if not self.disponible() or not imagen_bytes:
            return None

        if not mime:
            mime = _detectar_mime(imagen_bytes)

        if mime == "application/pdf":
            bloques = [{
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(imagen_bytes).decode("ascii"),
                },
            }]
            troceado = False
        else:
            imagenes = _preparar_imagenes(imagen_bytes)
            bloques = [{
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_trozo,
                    "data": base64.standard_b64encode(datos).decode("ascii"),
                },
            } for mime_trozo, datos in imagenes]
            troceado = len(imagenes) > 1

        catalogo = "\n".join(
            f"{p['id']}: {p['nombre']}" for p in productos_catalogo
        ) or "(catálogo vacío)"
        prompt = _PROMPT.format(catalogo=catalogo)
        if troceado:
            prompt += _AVISO_TROZOS.format(n=len(bloques))

        respuesta = self._pedir_analisis(bloques, prompt)
        if respuesta is None:
            return None

        ids_catalogo = {p["id"] for p in productos_catalogo if p.get("id") is not None}
        items = _normalizar_items(respuesta.get("productos") or [], ids_catalogo)
        if troceado:
            items = _deduplicar_solape(items)

        logger.info("Claude OCR detectó %d artículos", len(items))
        return {"productos": items}

    def _pedir_analisis(self, bloques, prompt) -> Optional[dict]:
        """Hace la llamada y devuelve el dict de la respuesta, o None."""
        try:
            mensaje = self._crear_mensaje(bloques, prompt, self._soporta_esquema)
        except TypeError as error:
            # SDK antiguo: no conoce output_config. Se reintenta sin esquema y
            # se deja marcado para las siguientes llamadas.
            logger.warning(
                "El SDK de anthropic instalado no acepta structured outputs (%s); "
                "se usa el parseo tolerante. Actualiza con: pip install -U anthropic",
                error,
            )
            type(self)._soporta_esquema = False
            try:
                mensaje = self._crear_mensaje(bloques, prompt, False)
            except Exception:
                logger.exception("Fallo llamando a Claude OCR")
                return None
        except Exception as error:
            if self._soporta_esquema and _parece_parametro_no_soportado(error):
                logger.warning(
                    "La API rechazó structured outputs (%s); se usa el parseo tolerante",
                    error,
                )
                type(self)._soporta_esquema = False
                try:
                    mensaje = self._crear_mensaje(bloques, prompt, False)
                except Exception:
                    logger.exception("Fallo llamando a Claude OCR")
                    return None
            else:
                logger.exception("Fallo llamando a Claude OCR: %s", type(error).__name__)
                return None

        motivo = getattr(mensaje, "stop_reason", None)
        if motivo == "refusal":
            logger.error("Claude rechazó analizar la imagen del ticket")
            return None
        if motivo == "max_tokens":
            logger.error(
                "La respuesta de Claude se cortó por longitud; el ticket podría "
                "tener más artículos de los que caben en %d tokens", _MAX_TOKENS,
            )

        # Con el razonamiento activado la respuesta trae bloques que no son
        # texto: hay que filtrar por tipo en vez de leer content[0].
        texto = "".join(
            bloque.text for bloque in getattr(mensaje, "content", [])
            if getattr(bloque, "type", None) == "text" and getattr(bloque, "text", None)
        ).strip()
        if not texto:
            logger.error("Claude devolvió una respuesta sin texto (stop_reason=%s)", motivo)
            return None

        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            datos = _extraer_json(texto)

        if not isinstance(datos, dict) or not isinstance(datos.get("productos"), list):
            logger.error("Claude devolvió un formato inesperado: %s", texto[:300])
            return None
        return datos

    def _crear_mensaje(self, bloques, prompt, usar_esquema: bool):
        parametros = {
            "model": _MODELO,
            "max_tokens": _MAX_TOKENS,
            "timeout": _TIMEOUT_SEGUNDOS,
            "messages": [{
                "role": "user",
                "content": bloques + [{"type": "text", "text": prompt}],
            }],
        }
        if usar_esquema:
            parametros["output_config"] = {
                "effort": _ESFUERZO,
                "format": {"type": "json_schema", "schema": _ESQUEMA_RESPUESTA},
            }
        return self.client.messages.create(**parametros)


def _parece_parametro_no_soportado(error: Exception) -> bool:
    """True si el error apunta a que la API no admite `output_config`."""
    mensaje = str(error).lower()
    return any(
        pista in mensaje
        for pista in ("output_config", "output config", "json_schema", "structured output")
    )
