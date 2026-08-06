"""Endpoints de API y configuración (frontend manejado por Next.js)."""
import logging
from flask import Blueprint, request
from flask_wtf.csrf import generate_csrf

from .. import csrf
from ..api import manejo_errores, APIResponse
from ..red import ip_cliente, limite_por_ip
from ..servicios import mantenimiento

logger = logging.getLogger(__name__)

bp = Blueprint("paginas", __name__)

# Limite de /api/log/client (S-14): mucho mas permisivo que el de login,
# solo para contener un cliente roto en bucle o un abuso deliberado del
# endpoint como vector de "log injection". En memoria del proceso (ver
# red.limite_por_ip): no hace falta exactitud entre workers para este caso.
MAX_LOGS_POR_MINUTO = 30
LOG_MENSAJE_MAX = 500
LOG_CONTEXTO_MAX = 1000


@bp.route("/api/csrf-token", methods=["GET"])
@manejo_errores
def csrf_token():
    """Token CSRF para clientes que no renderizan la plantilla Jinja (SPA
    Next.js separada del backend): sin esto no hay forma de rellenar la
    cabecera X-CSRFToken que exige Flask-WTF en toda petición mutable."""
    return APIResponse.success({"csrf_token": generate_csrf()})


@bp.route("/api/mantenimiento/estado")
@csrf.exempt
@manejo_errores
def mantenimiento_estado():
    """Sustituye al antiguo SSE /api/mantenimiento/stream (S-02): ese endpoint
    bloqueaba un hilo de gunicorn por cliente conectado (Condition.wait()), y
    con --workers 2 --threads 4 (8 hilos totales, ver Dockerfile.raspbian)
    unas pocas pestañas ya saturaban el backend. Este responde al instante,
    sin retener ningun hilo; el frontend hace polling corto (ver
    lib/useMantenimientoStream.ts), igual que ya hace usePollingRefresh.ts
    para otros datos.

    No requiere sesión: tambien debe llegar a usuarios no logueados en la
    pantalla de mantenimiento.
    """
    return APIResponse.success({"activo": mantenimiento.activo()})


@bp.route("/api/log/client", methods=["POST"])
@csrf.exempt
@manejo_errores
def log_client_error():
    """Endpoint para que el cliente envíe logs (errores, warnings).

    Exento de CSRF: se envía con navigator.sendBeacon (no soporta cabeceras
    personalizadas como X-CSRFToken) y también en el momento en que el propio
    error de la página puede impedir que el token esté disponible.
    """
    if limite_por_ip(f"log_client:{ip_cliente()}", MAX_LOGS_POR_MINUTO, 60):
        return APIResponse.error("err_demasiadas_peticiones", 429)

    datos = request.get_json(force=True) or {}
    nivel = datos.get("nivel", "info").lower()  # info, warning, error
    mensaje = str(datos.get("mensaje", ""))
    contexto = datos.get("contexto", {})

    # Sanear saltos de linea y truncar (S-14): sin esto, un cliente (o un
    # atacante llamando directamente al endpoint, que no exige CSRF) podia
    # fabricar entradas de log falsas multi-linea que aparentaran venir de
    # otro proceso/nivel al leerse en el fichero de logs.
    mensaje = mensaje.replace("\r", " ").replace("\n", " ")[:LOG_MENSAJE_MAX]
    contexto_str = f" | Contexto: {contexto}" if contexto else ""
    contexto_str = contexto_str.replace("\r", " ").replace("\n", " ")[:LOG_CONTEXTO_MAX]
    if nivel == "error":
        logger.error(f"[CLIENT] {mensaje}{contexto_str}")
    elif nivel == "warning":
        logger.warning(f"[CLIENT] {mensaje}{contexto_str}")
    else:
        logger.info(f"[CLIENT] {mensaje}{contexto_str}")

    return APIResponse.success({"logged": True})
