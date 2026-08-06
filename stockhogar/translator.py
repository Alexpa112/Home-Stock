"""
Sistema de traducción basado en JSON.

Carga diccionarios de traducción desde translations.json
y proporciona funciones helper para traducir strings.
"""
import json
import os
from pathlib import Path
from flask import session


# Cargar diccionarios
TRANSLATIONS_FILE = Path(__file__).parent / "translations.json"

try:
    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except FileNotFoundError:
    TRANSLATIONS = {"es": {}}

IDIOMAS_DISPONIBLES = list(TRANSLATIONS.keys())

# Nombre nativo (endónimo) de cada idioma soportado, para el selector de idioma.
NOMBRES_NATIVOS = {
    "es": "Español",
    "gl": "Galego",
    "en": "English",
    "pt": "Português",
    "fr": "Français",
    "it": "Italiano",
    "de": "Deutsch",
}


def obtener_idioma():
    """Obtiene el idioma actual de la sesión o default."""
    return session.get("idioma", "es")


def traducir(clave, idioma=None):
    """Traduce una clave a un idioma.

    Args:
        clave (str): Clave de traducción (ej: 'app_name')
        idioma (str, optional): Código de idioma. Si no se proporciona, usa sesión.

    Returns:
        str: Texto traducido o la clave si no existe
    """
    if idioma is None:
        idioma = obtener_idioma()

    # Validar idioma
    if idioma not in TRANSLATIONS:
        idioma = "es"

    # Obtener traducción
    diccionario = TRANSLATIONS[idioma]
    return diccionario.get(clave, TRANSLATIONS["es"].get(clave, clave))


def traducir_html(texto, idioma=None):
    """Traduce un string que contiene claves de traducción.

    Útil para HTML donde queremos mantener estructura pero traducir textos.

    Args:
        texto (str): Texto con claves entre {{ }}
        idioma (str, optional): Código de idioma

    Returns:
        str: Texto traducido
    """
    if idioma is None:
        idioma = obtener_idioma()

    # Reemplazar todas las claves {{clave}}
    import re
    patron = r'\{\{(\w+)\}\}'

    def reemplazar(match):
        clave = match.group(1)
        return traducir(clave, idioma)

    return re.sub(patron, reemplazar, texto)


def obtener_idiomas():
    """Retorna diccionario con idiomas disponibles."""
    idiomas = {}
    for codigo in IDIOMAS_DISPONIBLES:
        nativo = NOMBRES_NATIVOS.get(codigo, codigo)
        idiomas[codigo] = {
            "nombre": nativo,
            "nativo": nativo,
        }
    return idiomas


# Helper para templates Jinja2
def traduccion_dict(clave, idioma=None):
    """Devuelve diccionario de traducciones para una clave en todos los idiomas.

    Útil para debugging.
    """
    resultado = {}
    for lang in IDIOMAS_DISPONIBLES:
        resultado[lang] = traducir(clave, lang)
    return resultado


# Funciones alias cortas
def _(clave, idioma=None):
    """Alias corto para traducir."""
    return traducir(clave, idioma)


def t(clave):
    """Traducir con idioma de sesión actual."""
    return traducir(clave)


def traducir_todas_para_idioma(idioma):
    """Devuelve TODAS las traducciones para un idioma.

    Útil para cargar traducción completa en frontend.
    """
    if idioma not in TRANSLATIONS:
        idioma = "es"

    return TRANSLATIONS[idioma]
