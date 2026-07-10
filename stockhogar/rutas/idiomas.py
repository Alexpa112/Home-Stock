"""Rutas para gestionar idiomas y configuración de idioma."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..translator import IDIOMAS_DISPONIBLES, traducir, obtener_idiomas, traducir_todas_para_idioma
from .espacios import obtener_espacio_actual

bp = Blueprint("idiomas", __name__, url_prefix="/api/idiomas")


@bp.route("/disponibles", methods=["GET"])
@manejo_errores
def listar_idiomas():
    """Lista idiomas disponibles."""
    idiomas = obtener_idiomas()
    return APIResponse.success({
        "idiomas": idiomas,
        "actual": session.get("idioma", "es")
    })


@bp.route("/cambiar", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_idioma():
    """Cambia el idioma del usuario.

    Guardar en:
    1. Sesión (inmediato)
    2. BD (persistencia)
    """
    datos = request.get_json(force=True) or {}
    idioma = (datos.get("idioma") or "es").strip().lower()

    # Validar idioma
    if idioma not in IDIOMAS_DISPONIBLES:
        return APIResponse.validacion(
            f"Idioma no soportado. Disponibles: {', '.join(IDIOMAS_DISPONIBLES)}"
        )

    # 1. Guardar en sesión
    session['idioma'] = idioma

    # 2. Guardar en BD (si está autenticado)
    try:
        usuario_id = session.get("usuario_id")
        if usuario_id:
            db = get_db()
            db.execute(
                "UPDATE usuarios SET idioma_preferido = ? WHERE id = ?",
                (idioma, usuario_id)
            )
            db.commit()
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "No se pudo persistir el idioma preferido en BD (usuario_id=%s)", usuario_id
        )
        # Sigue en sesión aunque falle la persistencia en BD

    return APIResponse.success({
        "idioma": idioma,
        "mensaje": traducir("app_name", idioma)
    })


@bp.route("/obtener", methods=["GET"])
@manejo_errores
def obtener_idioma():
    """Obtiene el idioma actual."""
    idioma = session.get("idioma", "es")
    return APIResponse.success({
        "idioma": idioma,
        "nombre": traducir("idioma", idioma)
    })


@bp.route("/traducir", methods=["POST"])
@manejo_errores
def traducir_claves():
    """Traduce múltiples claves a un idioma.

    Útil para sincronizar UI desde JavaScript.
    """
    datos = request.get_json(force=True) or {}
    idioma = (datos.get("idioma") or session.get("idioma", "es")).lower()
    claves = datos.get("claves", [])

    # Validar
    if idioma not in IDIOMAS_DISPONIBLES:
        idioma = "es"

    if not isinstance(claves, list):
        return APIResponse.validacion("claves debe ser una lista")

    # Traducir
    traducciones = {}
    for clave in claves:
        traducciones[clave] = traducir(clave, idioma)

    return APIResponse.success({
        "idioma": idioma,
        "traducciones": traducciones
    })


@bp.route("/todos/<idioma>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_todas_traducciones(idioma):
    """Obtiene TODAS las traducciones para un idioma, incluyendo categorías dinámicas.

    Usado al iniciar la app para traducir toda la página.
    """
    idioma = idioma.lower()

    # Validar idioma
    if idioma not in IDIOMAS_DISPONIBLES:
        return APIResponse.validacion(
            f"Idioma no soportado. Disponibles: {', '.join(IDIOMAS_DISPONIBLES)}"
        )

    # Obtener todas las traducciones base
    todas = traducir_todas_para_idioma(idioma).copy()

    # Mapeo de categorías predefinidas a otros idiomas
    categoria_mapeo = {
        'es': {
            'Alimentacion': 'Alimentación',
            'Bebidas': 'Bebidas',
            'Bebé': 'Bebé',
            'Carnes y Embutidos': 'Carnes y Embutidos',
            'Cereales y Pasta': 'Cereales y Pasta',
            'Congelados': 'Congelados',
            'Despensa': 'Despensa',
            'Frutas y Verduras': 'Frutas y Verduras',
            'Higiene': 'Higiene',
            'Limpieza': 'Limpieza',
            'Lácteos y Huevos': 'Lácteos y Huevos',
            'Mascotas': 'Mascotas',
            'Otros': 'Otros',
            'Panadería y Bollería': 'Panadería y Bollería',
            'Pescados y Mariscos': 'Pescados y Mariscos',
            'Snacks y Dulces': 'Snacks y Dulces',
        },
        'gl': {
            'Alimentacion': 'Alimentación',
            'Bebidas': 'Bebidas',
            'Bebé': 'Bebé',
            'Carnes y Embutidos': 'Carnes e Embutidos',
            'Cereales y Pasta': 'Cereais e Pasta',
            'Congelados': 'Conxelados',
            'Despensa': 'Despensa',
            'Frutas y Verduras': 'Froitas e Vexetais',
            'Higiene': 'Hixiene',
            'Limpieza': 'Limpeza',
            'Lácteos y Huevos': 'Lácteos e Ovos',
            'Mascotas': 'Mascotas',
            'Otros': 'Outros',
            'Panadería y Bollería': 'Panadería e Bollería',
            'Pescados y Mariscos': 'Peixes e Mariscos',
            'Snacks y Dulces': 'Snacks e Doces',
        },
        'en': {
            'Alimentacion': 'Food',
            'Bebidas': 'Beverages',
            'Bebé': 'Baby',
            'Carnes y Embutidos': 'Meat & Cold Cuts',
            'Cereales y Pasta': 'Cereals & Pasta',
            'Congelados': 'Frozen',
            'Despensa': 'Pantry',
            'Frutas y Verduras': 'Fruits & Vegetables',
            'Higiene': 'Hygiene',
            'Limpieza': 'Cleaning',
            'Lácteos y Huevos': 'Dairy & Eggs',
            'Mascotas': 'Pets',
            'Otros': 'Other',
            'Panadería y Bollería': 'Bakery & Pastries',
            'Pescados y Mariscos': 'Fish & Seafood',
            'Snacks y Dulces': 'Snacks & Sweets',
        },
        'pt': {
            'Alimentacion': 'Alimentação',
            'Bebidas': 'Bebidas',
            'Bebé': 'Bebê',
            'Carnes y Embutidos': 'Carnes e Embutidos',
            'Cereales y Pasta': 'Cereais e Massa',
            'Congelados': 'Congelados',
            'Despensa': 'Despensa',
            'Frutas y Verduras': 'Frutas e Vegetais',
            'Higiene': 'Higiene',
            'Limpieza': 'Limpeza',
            'Lácteos y Huevos': 'Laticínios e Ovos',
            'Mascotas': 'Animais de Estimação',
            'Otros': 'Outros',
            'Panadería y Bollería': 'Padaria e Bolos',
            'Pescados y Mariscos': 'Peixes e Frutos do Mar',
            'Snacks y Dulces': 'Lanches e Doces',
        },
        'fr': {
            'Alimentacion': 'Alimentation',
            'Bebidas': 'Boissons',
            'Bebé': 'Bébé',
            'Carnes y Embutidos': 'Viandes et Charcuterie',
            'Cereales y Pasta': 'Céréales et Pâtes',
            'Congelados': 'Surgelés',
            'Despensa': 'Garde-manger',
            'Frutas y Verduras': 'Fruits et Légumes',
            'Higiene': 'Hygiène',
            'Limpieza': 'Nettoyage',
            'Lácteos y Huevos': 'Produits Laitiers et Œufs',
            'Mascotas': 'Animaux de Compagnie',
            'Otros': 'Autres',
            'Panadería y Bollería': 'Boulangerie et Pâtisserie',
            'Pescados y Mariscos': 'Poissons et Fruits de Mer',
            'Snacks y Dulces': 'Snacks et Bonbons',
        },
        'it': {
            'Alimentacion': 'Alimentazione',
            'Bebidas': 'Bevande',
            'Bebé': 'Bambino',
            'Carnes y Embutidos': 'Carni e Salumi',
            'Cereales y Pasta': 'Cereali e Pasta',
            'Congelados': 'Surgelati',
            'Despensa': 'Dispensa',
            'Frutas y Verduras': 'Frutta e Verdura',
            'Higiene': 'Igiene',
            'Limpieza': 'Pulizia',
            'Lácteos y Huevos': 'Latticini e Uova',
            'Mascotas': 'Animali Domestici',
            'Otros': 'Altro',
            'Panadería y Bollería': 'Panetteria e Pasticceria',
            'Pescados y Mariscos': 'Pesce e Frutti di Mare',
            'Snacks y Dulces': 'Snack e Dolcetti',
        },
        'de': {
            'Alimentacion': 'Lebensmittel',
            'Bebidas': 'Getränke',
            'Bebé': 'Baby',
            'Carnes y Embutidos': 'Fleisch und Wurstwaren',
            'Cereales y Pasta': 'Getreide und Nudeln',
            'Congelados': 'Gefrierwaren',
            'Despensa': 'Vorratskammer',
            'Frutas y Verduras': 'Obst und Gemüse',
            'Higiene': 'Hygiene',
            'Limpieza': 'Reinigung',
            'Lácteos y Huevos': 'Milchprodukte und Eier',
            'Mascotas': 'Haustiere',
            'Otros': 'Sonstiges',
            'Panadería y Bollería': 'Bäckerei und Gebäck',
            'Pescados y Mariscos': 'Fisch und Meeresfrüchte',
            'Snacks y Dulces': 'Snacks und Süßigkeiten',
        },
    }

    # Agregar traducciones de categorías al diccionario
    mapeo_idioma = categoria_mapeo.get(idioma, categoria_mapeo.get('es', {}))  # Fallback a español

    # Agregar TODAS las categorías del mapeo (no solo las que están en la BD del usuario)
    for categoria_original, traduccion in mapeo_idioma.items():
        clave = f'categoria_{categoria_original.lower().replace(" ", "_").replace("&", "y")}'
        todas[clave] = traduccion

    return APIResponse.success({
        "idioma": idioma,
        "traducciones": todas
    })
