"""API endpoints para procesamiento OCR de tickets."""
import os
import tempfile
from flask import Blueprint, request
from werkzeug.utils import secure_filename

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..translator import traducir
from ..servicios.ocr import GestorOCR

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# Extensiones permitidas
EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp"}
TAMAÑO_MAXIMO_MB = 10

# Gestor OCR (singleton)
gestor_ocr = GestorOCR()


def archivo_permitido(filename):
    """Valida que el archivo sea una imagen permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


@bp.route("/procesar-ticket", methods=["POST"])
@requerir_sesion
@manejo_errores
def procesar_ticket():
    """Procesa un ticket desde imagen.

    Retorna: {
        "exito": bool,
        "error": str | null,
        "confianza_ocr": float (0-100),
        "texto_original": str,
        "productos": [...]
    }
    """
    if "archivo" not in request.files:
        return APIResponse.validacion("err_sin_archivo")

    archivo = request.files["archivo"]

    if archivo.filename == "":
        return APIResponse.validacion("err_archivo_vacio")

    if not archivo_permitido(archivo.filename):
        return APIResponse.validacion("err_formato_no_permitido")

    archivo.seek(0, os.SEEK_END)
    tamaño_bytes = archivo.tell()
    archivo.seek(0)

    if tamaño_bytes > TAMAÑO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(TAMAÑO_MAXIMO_MB))
        )

    imagen_bytes = archivo.read()
    db = get_db()
    resultado = gestor_ocr.procesar_ticket(imagen_bytes, db)

    if resultado["exito"]:
        return APIResponse.success(resultado, 200)
    else:
        return APIResponse.error(resultado.get("error", traducir("err_procesando_ticket")), 400)


@bp.route("/validar-instalacion", methods=["GET"])
@manejo_errores
def validar_instalacion():
    """Valida que todas las dependencias OCR estén instaladas."""
    validaciones = {
        "tesseract": False,
        "opencv": False,
        "pytesseract": False,
        "fuzzywuzzy": False,
    }

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        validaciones["tesseract"] = True
        validaciones["pytesseract"] = True
    except Exception as e:
        validaciones["error_tesseract"] = str(e)

    try:
        import cv2
        validaciones["opencv"] = True
    except ImportError:
        validaciones["error_opencv"] = "opencv-python no está instalado"

    try:
        from fuzzywuzzy import fuzz
        validaciones["fuzzywuzzy"] = True
    except ImportError:
        validaciones["error_fuzzywuzzy"] = "fuzzywuzzy no está instalado"

    todas_ok = all(
        v is True
        for k, v in validaciones.items()
        if k in ["tesseract", "opencv", "pytesseract", "fuzzywuzzy"]
    )

    return APIResponse.success({"ok": todas_ok, "validaciones": validaciones})
