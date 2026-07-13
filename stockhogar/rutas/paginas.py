"""Ruta de la pagina principal (SPA)."""
import logging
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app, send_from_directory

from ..api import manejo_errores, APIResponse

logger = logging.getLogger(__name__)

bp = Blueprint("paginas", __name__)


@bp.route("/")
@manejo_errores
def index():
    return render_template("index.html")


@bp.route("/sw.js")
@manejo_errores
def service_worker():
    """Sirve el Service Worker desde la raíz para que su scope cubra toda la app."""
    respuesta = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    respuesta.headers["Service-Worker-Allowed"] = "/"
    respuesta.headers["Cache-Control"] = "no-cache"
    return respuesta


@bp.route("/aceptar-invitacion/<codigo>")
@manejo_errores
def aceptar_invitacion_pagina(codigo):
    """Página para aceptar invitación (solo si está logueado)."""
    usuario_id = session.get("usuario_id")

    # Si no está logueado, redirigir a login
    if not usuario_id:
        return redirect(url_for("auth.pagina_login"))

    # Renderizar página de aceptación
    return render_template("aceptar_invitacion.html", codigo=codigo)


@bp.route("/api/log/client", methods=["POST"])
@manejo_errores
def log_client_error():
    """Endpoint para que el cliente envíe logs (errores, warnings)."""
    datos = request.get_json(force=True) or {}
    nivel = datos.get("nivel", "info").lower()  # info, warning, error
    mensaje = datos.get("mensaje", "")
    contexto = datos.get("contexto", {})

    # Loguear según nivel
    contexto_str = f" | Contexto: {contexto}" if contexto else ""
    if nivel == "error":
        logger.error(f"[CLIENT] {mensaje}{contexto_str}")
    elif nivel == "warning":
        logger.warning(f"[CLIENT] {mensaje}{contexto_str}")
    else:
        logger.info(f"[CLIENT] {mensaje}{contexto_str}")

    return APIResponse.success({"logged": True})
