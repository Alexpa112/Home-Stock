"""Rutas para gestionar idiomas y configuración de idioma."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..translator import IDIOMAS_DISPONIBLES, traducir, obtener_idiomas, traducir_todas_para_idioma

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
        pass  # Si falla BD, al menos quedó en sesión

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
@manejo_errores
def obtener_todas_traducciones(idioma):
    """Obtiene TODAS las traducciones para un idioma.

    Usado al iniciar la app para traducir toda la página.
    """
    idioma = idioma.lower()

    # Validar idioma
    if idioma not in IDIOMAS_DISPONIBLES:
        return APIResponse.validacion(
            f"Idioma no soportado. Disponibles: {', '.join(IDIOMAS_DISPONIBLES)}"
        )

    # Obtener todas las traducciones
    todas = traducir_todas_para_idioma(idioma)

    return APIResponse.success({
        "idioma": idioma,
        "traducciones": todas
    })
