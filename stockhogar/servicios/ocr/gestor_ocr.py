"""Gestor OCR - orquestador del flujo completo."""
from typing import List, Dict
from .procesador_imagen import ProcesadorImagen
from .extractor_texto import ExtractorTexto
from .parseador_ticket import ParseadorTicket, LineaTicket
from .matcher_productos import MatcherProductos


class GestorOCR:
    """Orquesta el flujo completo OCR.

    1. Procesa imagen
    2. Extrae texto (OCR)
    3. Parsea líneas de producto
    4. Busca coincidencias en catálogo
    5. Retorna datos estructurados
    """

    def __init__(self):
        self.procesador = ProcesadorImagen()
        self.extractor = ExtractorTexto(idioma="spa")
        self.parseador = ParseadorTicket()
        self.matcher = MatcherProductos()

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
            resultado["error"] = f"Error procesando ticket: {str(e)}"
            return resultado

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
