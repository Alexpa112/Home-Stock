"""API endpoints para procesamiento OCR de tickets."""
import os
import tempfile
from datetime import date
from flask import Blueprint, request, session
from werkzeug.utils import secure_filename

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import LIMITE_OCR_DIARIO
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


def _uso_ocr_hoy(db, usuario_id):
    fila = db.execute(
        "SELECT contador FROM uso_ocr_diario WHERE usuario_id = ? AND fecha = ?",
        (usuario_id, date.today().isoformat()),
    ).fetchone()
    return fila["contador"] if fila else 0


def _incrementar_uso_ocr(db, usuario_id):
    hoy = date.today().isoformat()
    db.execute(
        "INSERT INTO uso_ocr_diario (usuario_id, fecha, contador) VALUES (?, ?, 1) "
        "ON CONFLICT(usuario_id, fecha) DO UPDATE SET contador = contador + 1",
        (usuario_id, hoy),
    )
    db.commit()


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

    db = get_db()
    usuario_id = session.get("usuario_id")
    if _uso_ocr_hoy(db, usuario_id) >= LIMITE_OCR_DIARIO:
        return APIResponse.error("err_limite_ocr_diario", 429)

    imagen_bytes = archivo.read()
    resultado = gestor_ocr.procesar_ticket(imagen_bytes, db)

    if resultado["exito"]:
        _incrementar_uso_ocr(db, usuario_id)
        return APIResponse.success(resultado, 200)
    else:
        return APIResponse.error(resultado.get("error", traducir("err_procesando_ticket")), 400)


@bp.route("/validar-instalacion", methods=["GET"])
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
        "fuzzywuzzy": False,
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
