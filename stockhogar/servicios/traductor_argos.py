"""
Traducción offline de nombres/descripciones de producto usando Argos Translate.

Argos no distribuye un modelo neuronal para gallego (gl); ese idioma se cubre
aparte con stockhogar.servicios.diccionario_gallego. Este módulo cubre
es -> en, fr, it, de, pt.

Los paquetes de idioma se descargan una única vez (requiere red) y después de
eso la traducción funciona sin conexión.
"""

import threading

_lock = threading.Lock()
_instalado = False

IDIOMA_ORIGEN = "es"
IDIOMAS_DIRECTOS = {"en", "pt"}  # Argos tiene modelo directo es->idioma
IDIOMAS_VIA_INGLES = {"fr", "it", "de"}  # se traduce es->en->idioma


def _asegurar_paquetes_instalados():
    """Instala (si falta) los paquetes de Argos necesarios: es-en, en-es, en-fr, en-it, en-de, es-pt."""
    global _instalado
    if _instalado:
        return
    with _lock:
        if _instalado:
            return
        import argostranslate.package

        necesarios = {("es", "en"), ("en", "fr"), ("en", "it"), ("en", "de"), ("es", "pt")}
        instalados = {
            (p.from_code, p.to_code) for p in argostranslate.package.get_installed_packages()
        }
        faltantes = necesarios - instalados
        if faltantes:
            argostranslate.package.update_package_index()
            disponibles = argostranslate.package.get_available_packages()
            for origen, destino in faltantes:
                paquete = next(
                    (p for p in disponibles if p.from_code == origen and p.to_code == destino),
                    None,
                )
                if paquete:
                    argostranslate.package.install_from_path(paquete.download())
        _instalado = True


def disponible(idioma_destino):
    return idioma_destino in IDIOMAS_DIRECTOS or idioma_destino in IDIOMAS_VIA_INGLES


def traducir_texto(texto, idioma_destino):
    """
    Traduce texto de español al idioma indicado usando Argos Translate.

    Devuelve None si el idioma no está soportado por Argos o si falla la traducción
    (para que el llamador pueda usar un fallback).
    """
    if not texto or not disponible(idioma_destino):
        return None

    try:
        _asegurar_paquetes_instalados()
        import argostranslate.translate as at

        if idioma_destino in IDIOMAS_DIRECTOS:
            return at.translate(texto, IDIOMA_ORIGEN, idioma_destino)

        en_ingles = at.translate(texto, IDIOMA_ORIGEN, "en")
        return at.translate(en_ingles, "en", idioma_destino)
    except Exception:
        return None
