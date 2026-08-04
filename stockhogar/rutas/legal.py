"""Configuración pública para las páginas legales del frontend (Aviso Legal,
Política de Privacidad, Términos y Política de Cookies): quién es el
responsable, cómo contactar y en qué dominio se publica la app. Endpoint
público (no requiere sesión) porque cualquier visitante debe poder leer estos
textos antes incluso de registrarse.
"""
from flask import Blueprint

from ..api import APIResponse, manejo_errores
from ..config import DOMINIO_PUBLICO, EMAIL_CONTACTO_LEGAL, TITULAR_LEGAL, VERSION_TERMINOS

bp = Blueprint("legal", __name__, url_prefix="/api/legal")


@bp.route("/config", methods=["GET"])
@manejo_errores
def configuracion_legal():
    return APIResponse.success({
        "titular": TITULAR_LEGAL,
        "email_contacto": EMAIL_CONTACTO_LEGAL,
        "dominio": DOMINIO_PUBLICO,
        "version_terminos": VERSION_TERMINOS,
    })
