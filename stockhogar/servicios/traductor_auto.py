"""
Servicio de traducción automática de nombres y descripciones de productos.

Utiliza un diccionario de palabras comunes de supermercado en múltiples idiomas
más búsqueda de términos similares.
"""

import json
from pathlib import Path

from . import diccionario_gallego, traductor_argos

# Diccionario de palabras clave de supermercado en múltiples idiomas
DICCIONARIO_PRODUCTOS = {
    # Alimentos básicos
    "leche": {
        "es": "Leche",
        "gl": "Leite",
        "en": "Milk",
        "pt": "Leite",
        "fr": "Lait",
        "it": "Latte",
        "de": "Milch"
    },
    "pan": {
        "es": "Pan",
        "gl": "Pan",
        "en": "Bread",
        "pt": "Pão",
        "fr": "Pain",
        "it": "Pane",
        "de": "Brot"
    },
    "huevo": {
        "es": "Huevo",
        "gl": "Ovo",
        "en": "Egg",
        "pt": "Ovo",
        "fr": "Œuf",
        "it": "Uovo",
        "de": "Ei"
    },
    "queso": {
        "es": "Queso",
        "gl": "Queixo",
        "en": "Cheese",
        "pt": "Queijo",
        "fr": "Fromage",
        "it": "Formaggio",
        "de": "Käse"
    },
    "mantequilla": {
        "es": "Mantequilla",
        "gl": "Manteiga",
        "en": "Butter",
        "pt": "Manteiga",
        "fr": "Beurre",
        "it": "Burro",
        "de": "Butter"
    },
    "carne": {
        "es": "Carne",
        "gl": "Carne",
        "en": "Meat",
        "pt": "Carne",
        "fr": "Viande",
        "it": "Carne",
        "de": "Fleisch"
    },
    "pollo": {
        "es": "Pollo",
        "gl": "Polo",
        "en": "Chicken",
        "pt": "Frango",
        "fr": "Poulet",
        "it": "Pollo",
        "de": "Huhn"
    },
    "pescado": {
        "es": "Pescado",
        "gl": "Peixe",
        "en": "Fish",
        "pt": "Peixe",
        "fr": "Poisson",
        "it": "Pesce",
        "de": "Fisch"
    },
    "verdura": {
        "es": "Verdura",
        "gl": "Verdura",
        "en": "Vegetable",
        "pt": "Verdura",
        "fr": "Légume",
        "it": "Verdura",
        "de": "Gemüse"
    },
    "fruta": {
        "es": "Fruta",
        "gl": "Froita",
        "en": "Fruit",
        "pt": "Fruta",
        "fr": "Fruit",
        "it": "Frutta",
        "de": "Obst"
    },
    "manzana": {
        "es": "Manzana",
        "gl": "Mazá",
        "en": "Apple",
        "pt": "Maçã",
        "fr": "Pomme",
        "it": "Mela",
        "de": "Apfel"
    },
    "naranja": {
        "es": "Naranja",
        "gl": "Laranxa",
        "en": "Orange",
        "pt": "Laranja",
        "fr": "Orange",
        "it": "Arancia",
        "de": "Orange"
    },
    "agua": {
        "es": "Agua",
        "gl": "Auga",
        "en": "Water",
        "pt": "Água",
        "fr": "Eau",
        "it": "Acqua",
        "de": "Wasser"
    },
    "café": {
        "es": "Café",
        "gl": "Café",
        "en": "Coffee",
        "pt": "Café",
        "fr": "Café",
        "it": "Caffè",
        "de": "Kaffee"
    },
    "té": {
        "es": "Té",
        "gl": "Chá",
        "en": "Tea",
        "pt": "Chá",
        "fr": "Thé",
        "it": "Tè",
        "de": "Tee"
    },
    "azúcar": {
        "es": "Azúcar",
        "gl": "Azucre",
        "en": "Sugar",
        "pt": "Açúcar",
        "fr": "Sucre",
        "it": "Zucchero",
        "de": "Zucker"
    },
    "sal": {
        "es": "Sal",
        "gl": "Sal",
        "en": "Salt",
        "pt": "Sal",
        "fr": "Sel",
        "it": "Sale",
        "de": "Salz"
    },
    "aceite": {
        "es": "Aceite",
        "gl": "Aceite",
        "en": "Oil",
        "pt": "Óleo",
        "fr": "Huile",
        "it": "Olio",
        "de": "Öl"
    },
    "jabón": {
        "es": "Jabón",
        "gl": "Xabón",
        "en": "Soap",
        "pt": "Sabão",
        "fr": "Savon",
        "it": "Sapone",
        "de": "Seife"
    },
    "papel": {
        "es": "Papel",
        "gl": "Papel",
        "en": "Paper",
        "pt": "Papel",
        "fr": "Papier",
        "it": "Carta",
        "de": "Papier"
    },
}

class TraductorAutomatico:
    """Traductor automático para productos basado en diccionario."""

    @staticmethod
    def traducir_texto(texto, idioma_destino, idioma_origen="es"):
        """
        Traduce un texto a un idioma específico.

        Usa búsqueda por palabras clave en el diccionario.
        Si no encuentra una traducción exacta, devuelve el texto original.
        """
        if not texto or idioma_destino == idioma_origen:
            return texto

        # Gallego: Argos Translate no distribuye modelo neuronal para gl,
        # así que usamos nuestro propio diccionario.
        if idioma_destino == "gl" and idioma_origen == "es":
            return diccionario_gallego.traducir_texto(texto)

        # Resto de idiomas: traducción offline con Argos Translate.
        if idioma_origen == "es":
            traduccion_argos = traductor_argos.traducir_texto(texto, idioma_destino)
            if traduccion_argos:
                return traduccion_argos

        texto_limpio = texto.lower().strip()

        # Fallback: diccionario propio de palabras clave
        if texto_limpio in DICCIONARIO_PRODUCTOS:
            traducciones = DICCIONARIO_PRODUCTOS[texto_limpio]
            if idioma_destino in traducciones:
                return traducciones[idioma_destino]

        # Buscar palabras clave dentro del texto
        palabras_traducidas = []
        for palabra in texto.split():
            palabra_limpia = palabra.lower().strip('.,')
            if palabra_limpia in DICCIONARIO_PRODUCTOS:
                traducciones = DICCIONARIO_PRODUCTOS[palabra_limpia]
                if idioma_destino in traducciones:
                    palabras_traducidas.append(traducciones[idioma_destino])
                else:
                    palabras_traducidas.append(palabra)
            else:
                palabras_traducidas.append(palabra)

        # Si encontramos traducciones para algunas palabras, devolver el resultado
        if palabras_traducidas and palabras_traducidas != texto.split():
            return " ".join(palabras_traducidas)

        # Si no hay traducción, devolver el original
        return texto

    @staticmethod
    def traducir_a_todos_idiomas(texto, idioma_origen="es"):
        """
        Traduce un texto a todos los idiomas soportados.

        Returns:
            dict: {idioma: texto_traducido, ...}
        """
        idiomas = ["es", "gl", "en", "pt", "fr", "it", "de"]
        resultado = {}

        for idioma in idiomas:
            if idioma == idioma_origen:
                resultado[idioma] = texto
            else:
                resultado[idioma] = TraductorAutomatico.traducir_texto(
                    texto, idioma, idioma_origen
                )

        return resultado

    @staticmethod
    def obtener_diccionario():
        """Devuelve el diccionario completo de traducciones."""
        return DICCIONARIO_PRODUCTOS


def traducir_producto(nombre, descripcion=""):
    """
    Traduce nombre y descripción de un producto a todos los idiomas.

    Returns:
        dict: {
            'nombre': {idioma: traducción, ...},
            'descripcion': {idioma: traducción, ...}
        }
    """
    return {
        'nombre': TraductorAutomatico.traducir_a_todos_idiomas(nombre),
        'descripcion': TraductorAutomatico.traducir_a_todos_idiomas(descripcion) if descripcion else {}
    }
