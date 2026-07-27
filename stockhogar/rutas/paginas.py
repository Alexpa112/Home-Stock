"""Ruta de la pagina principal (SPA)."""
import logging
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app, send_from_directory, Response, stream_with_context
from flask_wtf.csrf import generate_csrf

from .. import csrf
from ..api import manejo_errores, APIResponse
from ..db import get_db
from ..servicios import mantenimiento

logger = logging.getLogger(__name__)

bp = Blueprint("paginas", __name__)


@bp.route("/")
@manejo_errores
def index():
    tema_preferido = "auto"
    idioma_preferido = "es"
    teclado_virtual_activo = "on"
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = get_db().execute(
            "SELECT tema_preferido, idioma_preferido, teclado_virtual_activo FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        if fila:
            tema_preferido = fila["tema_preferido"]
            idioma_preferido = fila["idioma_preferido"]
            teclado_virtual_activo = fila["teclado_virtual_activo"]
    return render_template(
        "index.html",
        tema_preferido=tema_preferido,
        idioma_preferido=idioma_preferido,
        teclado_virtual_activo=teclado_virtual_activo,
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


@bp.route("/api/csrf-token", methods=["GET"])
@manejo_errores
def csrf_token():
    """Token CSRF para clientes que no renderizan la plantilla Jinja (SPA
    Next.js separada del backend): sin esto no hay forma de rellenar la
    cabecera X-CSRFToken que exige Flask-WTF en toda petición mutable."""
    return APIResponse.success({"csrf_token": generate_csrf()})


@bp.route("/api/mantenimiento/stream")
@csrf.exempt
def mantenimiento_stream():
    """SSE: mantiene la conexión abierta y emite un evento en cuanto el estado
    de mantenimiento cambie. El cliente JS se suscribe al arrancar y así recibe
    el aviso al instante, sin esperar el polling de 60 s.

    No requiere sesión (también llega a usuarios no logueados en la pantalla de
    mantenimiento) ni CSRF (GET de solo lectura con EventSource).
    """
    def generar():
        ultimo = mantenimiento.activo()
        # Estado inicial al conectar: el cliente sabe desde el primer byte
        # si ya está en mantenimiento o no.
        yield f"event: mantenimiento\ndata: {'activo' if ultimo else 'inactivo'}\n\n"
        while True:
            # Bloquea ~55 s o hasta que activo() detecte un cambio y haga notify_all.
            mantenimiento.esperar_cambio(timeout_s=55.0)
            ahora = mantenimiento.activo()
            if ahora != ultimo:
                ultimo = ahora
                yield f"event: mantenimiento\ndata: {'activo' if ahora else 'inactivo'}\n\n"

    return Response(
        stream_with_context(generar()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.route("/api/log/client", methods=["POST"])
@csrf.exempt
@manejo_errores
def log_client_error():
    """Endpoint para que el cliente envíe logs (errores, warnings).

    Exento de CSRF: se envía con navigator.sendBeacon (no soporta cabeceras
    personalizadas como X-CSRFToken) y también en el momento en que el propio
    error de la página puede impedir que el token esté disponible.
    """
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
