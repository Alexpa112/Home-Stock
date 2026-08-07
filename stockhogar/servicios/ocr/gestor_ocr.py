"""Gestor OCR - orquestador del flujo completo."""
import logging
from typing import List, Dict
from .procesador_imagen import ProcesadorImagen
from .extractor_texto import ExtractorTexto
from .parseador_ticket import ParseadorTicket, LineaTicket
from .matcher_productos import MatcherProductos
from .claude_ocr import ClaudeOCR

logger = logging.getLogger(__name__)


class GestorOCR:
    """Orquesta el flujo completo OCR.

    Motor principal: Claude Vision API (gratuita) - la mejor visión disponible,
    manda la foto + catálogo y hace OCR + comprensión semántica en un paso.
    Si no hay ANTHROPIC_API_KEY configurada, o la llamada falla
    (sin conexión, cuota agotada...), cae al pipeline local:
    1. Procesa imagen
    2. Extrae texto (OCR con Tesseract)
    3. Parsea líneas de producto
    4. Busca coincidencias en catálogo (fuzzy matching)
    5. Retorna datos estructurados
    """

    def __init__(self):
        self.procesador = ProcesadorImagen()
        self.extractor = ExtractorTexto(idioma="spa")
        self.parseador = ParseadorTicket()
        self.matcher = MatcherProductos()
        self.claude = ClaudeOCR()

    def procesar_ticket(self, imagen_bytes, db) -> Dict:
        """Procesa ticket completo.

        Args:
            imagen_bytes: Bytes de la imagen
            db: Conexión a base de datos

        Returns:
            Dict con resultado del procesamiento
        """
        resultado = {
            "exito": False,
            "error": None,
            "confianza_ocr": 0,
            "productos": [],
            "texto_original": "",
        }

        productos_catalogo = [
            dict(row)
            for row in db.execute(
                "SELECT id, nombre, categoria, icono FROM productos ORDER BY nombre"
            ).fetchall()
        ]

        # Motor principal: Claude Vision API (gratuita, la mejor para OCR)
        if self.claude.disponible():
            respuesta_ia = self.claude.procesar(imagen_bytes, productos_catalogo)
            if respuesta_ia is not None:
                resultado["productos"] = self._mapear_respuesta_ia(
                    respuesta_ia, productos_catalogo
                )
                resultado["confianza_ocr"] = 100
                resultado["exito"] = len(resultado["productos"]) > 0
                if not resultado["exito"]:
                    resultado["error"] = "No se detectaron productos en el ticket"
                return resultado
            logger.warning("Claude no disponible o fallo la llamada, usando pipeline local (Tesseract)")

        try:
            # 1. Procesar imagen
            imagen_procesada = self.procesador.procesar(imagen_bytes)

            # 2. Extraer texto
            texto, confianza_ocr = self.extractor.extraer(imagen_procesada)
            resultado["texto_original"] = texto
            resultado["confianza_ocr"] = confianza_ocr

            if not texto:
                resultado["error"] = "No se detectó texto en la imagen"
                return resultado

            # 3. Parsear líneas de producto
            lineas = self.parseador.parsear(texto)

            if not lineas:
                resultado["error"] = "No se detectaron productos en el ticket"
                return resultado

            # 4. Buscar coincidencias y enriquecer
            productos_finales = []
            for linea in lineas:
                producto = self._enriquecer_producto(linea, db)
                productos_finales.append(producto)

            resultado["productos"] = productos_finales
            resultado["exito"] = len(productos_finales) > 0

            return resultado

        except Exception as e:
            logger.exception("Error procesando ticket OCR")
            resultado["error"] = f"Error procesando ticket: {str(e)}"
            return resultado

    def _mapear_respuesta_ia(self, respuesta: Dict, productos_catalogo: List[Dict]) -> List[Dict]:
        """Convierte la respuesta JSON de la IA al formato que espera el frontend."""
        catalogo_por_id = {p["id"]: p for p in productos_catalogo}
        productos_finales = []

        for item in respuesta.get("productos", []):
            cantidad = item.get("cantidad") or 1
            unidad = item.get("unidad") or "ud"
            producto_id = item.get("producto_id")
            catalogado = catalogo_por_id.get(producto_id) if producto_id is not None else None

            if catalogado:
                productos_finales.append({
                    "nombre": catalogado["nombre"],
                    "cantidad": cantidad,
                    "cantidad_texto": f"{cantidad} {unidad}",
                    "categoria": catalogado["categoria"],
                    "icono": catalogado["icono"],
                    "confianza": 90,
                    "confianza_nombre": 90,
                    "encontrado": True,
                })
            else:
                nombre_ticket = (item.get("nombre_ticket") or "").strip().title() or "Producto"
                categoria = self.matcher.sugerir_categoria(nombre_ticket) or "Otros"
                icono = self.matcher.sugerir_icono(nombre_ticket, categoria)
                productos_finales.append({
                    "nombre": nombre_ticket,
                    "cantidad": cantidad,
                    "cantidad_texto": f"{cantidad} {unidad}",
                    "categoria": categoria,
                    "icono": icono,
                    "confianza": 0,
                    "confianza_nombre": 0,
                    "encontrado": False,
                })

        return productos_finales

    def _enriquecer_producto(self, linea: LineaTicket, db) -> Dict:
        """Enriquece línea del ticket con info del catálogo."""
        # Buscar en catálogo
        coincidencia = self.matcher.buscar_en_catalogo(linea.nombre, db)

        if coincidencia:
            return {
                "nombre": coincidencia["nombre"],
                "cantidad": linea.cantidad,
                "cantidad_texto": linea.cantidad_texto,
                "categoria": coincidencia["categoria"],
                "icono": coincidencia["icono"],
                "confianza": coincidencia["confianza"],
                "confianza_nombre": coincidencia["confianza"],
                "encontrado": True,
            }

        # Si no encontró, sugerir categoría e icono
        categoria = self.matcher.sugerir_categoria(linea.nombre)
        icono = self.matcher.sugerir_icono(linea.nombre, categoria)

        return {
            "nombre": linea.nombre,
            "cantidad": linea.cantidad,
            "cantidad_texto": linea.cantidad_texto,
            "categoria": categoria or "Otros",
            "icono": icono,
            "confianza": 0,
            "confianza_nombre": 0,
            "encontrado": False,
        }
