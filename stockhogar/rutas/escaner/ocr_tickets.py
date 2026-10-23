"""API endpoints para procesamiento OCR de tickets."""
import os
from flask import Blueprint

from ...api import APIResponse, manejo_errores, requerir_sesion

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# ELIMINADO: POST /api/ocr/procesar-ticket (hallazgos A-6, A-7 y S-16 de la
# auditoria 2026-08). Tenia tres agujeros a la vez y el frontend NO lo usaba
# (escanea por /api/tickets/analizar, ver lib/api.ts):
#
#  - Ignoraba por completo el opt-out `usuario_ocr_local`: quien habia marcado
#    "escanear solo en local" y subia la foto por aqui mandaba su ticket a
#    Anthropic contra su voluntad expresa. La app declara ese control como el
#    mecanismo de oposicion del art. 21 RGPD, asi que era incumplimiento.
#  - Leia el catalogo `productos` sin filtrar por hogar (misma fuga que A-1).
#  - Validaba el fichero solo por extension, sin pasar por validar_y_recodificar.
#
# La cuota diaria que vivia aqui (LIMITE_OCR_DIARIO) se movio a
# servicios/cuota_ocr.py y ahora protege /api/tickets/analizar, que es el
# endpoint real. GET /validar-instalacion se conserva: es diagnostico y no
# procesa nada.


@bp.route("/validar-instalacion", methods=["GET"])
@requerir_sesion
@manejo_errores
def validar_instalacion():
    """Valida que todas las dependencias OCR estén instaladas.

    Informa por separado de la clave y del paquete del motor principal: con la
    clave puesta pero sin el paquete `anthropic` instalado, el escáner caía en
    silencio a Tesseract y el diagnóstico no daba ninguna pista.
    """
    validaciones = {
        "tesseract": False,
        "opencv": False,
        "pytesseract": False,
        "rapidfuzz": False,
        "claude_api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "claude_paquete": False,
    }

    try:
        import anthropic  # noqa: F401
        validaciones["claude_paquete"] = True
    except ImportError:
        validaciones["error_claude"] = (
            "El paquete 'anthropic' no está instalado: el escáner usará Tesseract. "
            "Instala con: pip install anthropic"
        )

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        validaciones["tesseract"] = True
        validaciones["pytesseract"] = True
    except Exception as e:
        # El texto de la excepcion puede traer rutas del servidor: se queda en el log.
        import logging
        logging.getLogger(__name__).warning("Tesseract no disponible: %s", e)
        validaciones["error_tesseract"] = "Tesseract no disponible o no instalado"

    try:
        import cv2
        validaciones["opencv"] = True
    except ImportError:
        validaciones["error_opencv"] = "opencv-python no está instalado"

    try:
        from rapidfuzz import fuzz  # noqa: F401
        validaciones["rapidfuzz"] = True
    except ImportError:
        validaciones["error_rapidfuzz"] = "rapidfuzz no está instalado"

    # Informativos (no entran en "ok": el escaner funciona sin el motor neuronal, con Tesseract)
    try:
        from ...integraciones import ocr_rapid
        validaciones["motor_neuronal"] = ocr_rapid.disponible()
    except Exception:
        validaciones["motor_neuronal"] = False
    try:
        from ...servicios.ocr.diccionario import obtener
        validaciones["diccionario_articulos"] = len(obtener().entradas)
    except Exception:
        validaciones["diccionario_articulos"] = 0

    todas_ok = all(
        v is True
        for k, v in validaciones.items()
        if k in ["tesseract", "opencv", "pytesseract", "rapidfuzz"]
    )

    return APIResponse.success({"ok": todas_ok, "validaciones": validaciones})
