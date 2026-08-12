"""Matching entre productos del ticket y catálogo local."""
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fuzzy_process

from .catalogo import catalogo_del_hogar


class MatcherProductos:
    """Busca coincidencias entre OCR y productos en catálogo.

    - Búsqueda fuzzy (tolerancia a errores de OCR)
    - Sugerencias de categoría
    - Sugerencias de icono
    """

    def __init__(self):
        self.umbral_coincidencia = 60  # % de similitud mínima

    def buscar_en_catalogo(self, nombre_ocr: str, db, hogar_id=None) -> Optional[Dict]:
        """Busca mejor coincidencia en catálogo.

        Args:
            nombre_ocr: Nombre extraído del OCR
            db: Conexión a base de datos

        Returns:
            Dict con producto coincidente o None
        """
        if not nombre_ocr or len(nombre_ocr) < 2:
            return None

        # Catálogo del hogar activo, nunca el global (A-1).
        if hogar_id is None:
            return None
        productos = catalogo_del_hogar(db, hogar_id)

        if not productos:
            return None

        nombres_catalogo = [p["nombre"] for p in productos]

        # Búsqueda fuzzy
        mejor_coincidencia, puntuacion = fuzzy_process.extractOne(
            nombre_ocr, nombres_catalogo, scorer=fuzz.token_set_ratio
        )

        # Verificar umbral
        if puntuacion < self.umbral_coincidencia:
            return None

        # Encontrar producto completo
        for producto in productos:
            if producto["nombre"] == mejor_coincidencia:
                return {
                    "nombre": producto["nombre"],
                    "categoria": producto["categoria"],
                    "icono": producto["icono"],
                    "confianza": min(puntuacion / 100, 1.0),
                }

        return None

    def sugerir_categoria(self, nombre: str) -> Optional[str]:
        """Sugiere categoría basada en nombre."""
        # Palabras clave por categoría
        palabras_claves = {
            "Alimentación": [
                "pan",
                "leche",
                "queso",
                "yogur",
                "cereales",
                "pasta",
                "arroz",
            ],
            "Frutas": ["manzana", "plátano", "naranja", "limón", "fresa", "uva"],
            "Verduras": [
                "tomate",
                "lechuga",
                "cebolla",
                "patata",
                "zanahoria",
                "calabacín",
            ],
            "Carnes": ["pollo", "pavo", "cerdo", "ternera", "cordero", "jamón"],
            "Bebidas": ["agua", "café", "té", "zumo", "refresco", "vino", "cerveza"],
            "Limpieza": [
                "detergente",
                "jabón",
                "limpiador",
                "desinfectante",
                "gel",
            ],
            "Higiene": ["papel", "pañuelos", "toallitas", "desodorante", "champú"],
        }

        nombre_lower = nombre.lower()

        # Buscar palabras clave
        for categoria, palabras in palabras_claves.items():
            for palabra in palabras:
                if palabra in nombre_lower:
                    return categoria

        return None

    def sugerir_icono(self, nombre: str, categoria: Optional[str] = None) -> str:
        """Sugiere icono basado en nombre y categoría."""
        iconos_predeterminados = {
            "Alimentación": "[FOOD]",
            "Frutas": "[FRUIT]",
            "Verduras": "[VEG]",
            "Carnes": "[MEAT]",
            "Bebidas": "[DRINK]",
            "Limpieza": "[CLEAN]",
            "Higiene": "[HYGIENE]",
            "Otros": "[BOX]",
        }

        # Si tenemos categoría, usar su icono
        if categoria and categoria in iconos_predeterminados:
            return iconos_predeterminados[categoria]

        # Intentar inferir de nombre
        nombre_lower = nombre.lower()

        mapeo_iconos = {
            "leche": "[MILK]",
            "pan": "[BREAD]",
            "frutas": "[FRUIT]",
            "verduras": "[VEG]",
            "carne": "[MEAT]",
            "pollo": "[POULTRY]",
            "cerveza": "[BEER]",
            "vino": "[WINE]",
            "agua": "[WATER]",
            "café": "[COFFEE]",
            "té": "[TEA]",
            "huevo": "[EGG]",
            "queso": "[CHEESE]",
            "chocolate": "[CHOCO]",
        }

        for palabra, icono in mapeo_iconos.items():
            if palabra in nombre_lower:
                return icono

        return "[BOX]"
