"""Ruta de la pagina principal (SPA)."""
import logging
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app, send_from_directory

from ..api import manejo_errores, APIResponse
from ..db import get_db

logger = logging.getLogger(__name__)

bp = Blueprint("paginas", __name__)


@bp.route("/")
@manejo_errores
def index():
    tema_preferido = "auto"
    idioma_preferido = "es"
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = get_db().execute(
            "SELECT tema_preferido, idioma_preferido FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        if fila:
            tema_preferido = fila["tema_preferido"]
            idioma_preferido = fila["idioma_preferido"]
    return render_template(
        "index.html", tema_preferido=tema_preferido, idioma_preferido=idioma_preferido
    )


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
    # (nota: el guardián global en __init__.py:exigir_sesion ya intercepta
    # esta ruta antes de llegar aquí y preserva el "next"; este chequeo queda
    # como defensa adicional).
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
