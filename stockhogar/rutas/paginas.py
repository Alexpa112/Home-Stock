"""Endpoints de API y configuración (frontend manejado por Next.js)."""
import logging
from flask import Blueprint, request, Response, stream_with_context
from flask_wtf.csrf import generate_csrf

from .. import csrf
from ..api import manejo_errores, APIResponse
from ..servicios import mantenimiento

logger = logging.getLogger(__name__)

bp = Blueprint("paginas", __name__)


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
            # Espera corta (no los ~55s de antes): si el cliente se fue sin
            # cerrar limpio (frecuente en iOS al suspender/matar la PWA), este
            # yield periódico hace que el intento de escritura falle enseguida
            # y libere el hilo de gunicorn, en vez de retenerlo minutos u horas
            # a la espera del keepalive TCP por defecto del sistema.
            mantenimiento.esperar_cambio(timeout_s=10.0)
            ahora = mantenimiento.activo()
            if ahora != ultimo:
                ultimo = ahora
                yield f"event: mantenimiento\ndata: {'activo' if ahora else 'inactivo'}\n\n"
            else:
                yield ": heartbeat\n\n"

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
