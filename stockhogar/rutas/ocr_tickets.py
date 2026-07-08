"""API endpoints para procesamiento OCR de tickets."""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from ..servicios.ocr import GestorOCR
from ..db import get_db

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
def procesar_ticket():
    """Procesa un ticket desde imagen.

    Retorna: {
        "exito": bool,
        "error": str | null,
        "confianza_ocr": float (0-100),
        "texto_original": str,
        "productos": [
            {
                "nombre": str,
                "cantidad": float,
                "cantidad_texto": str,
                "categoria": str,
                "icono": str,
                "encontrado": bool,
                "confianza": float
            }
        ]
    }
    """
    try:
        # Validar que haya archivo
        if "archivo" not in request.files:
            return jsonify({"error": "No se envió archivo"}), 400

        archivo = request.files["archivo"]

        if archivo.filename == "":
            return jsonify({"error": "Archivo vacío"}), 400

        if not archivo_permitido(archivo.filename):
            return jsonify({"error": "Formato no permitido. Usa PNG, JPG, etc."}), 400

        # Validar tamaño
        archivo.seek(0, os.SEEK_END)
        tamaño_bytes = archivo.tell()
        archivo.seek(0)

        if tamaño_bytes > TAMAÑO_MAXIMO_MB * 1024 * 1024:
            return (
                jsonify(
                    {"error": f"Archivo demasiado grande (máx {TAMAÑO_MAXIMO_MB}MB)"}
                ),
                400,
            )

        # Leer imagen
        imagen_bytes = archivo.read()

        # Procesar con OCR
        db = get_db()
        resultado = gestor_ocr.procesar_ticket(imagen_bytes, db)

        if resultado["exito"]:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Error procesando ticket: {str(e)}"}), 500


@bp.route("/validar-instalacion", methods=["GET"])
def validar_instalacion():
    """Valida que todas las dependencias OCR estén instaladas."""
    validaciones = {
        "tesseract": False,
        "opencv": False,
        "pytesseract": False,
        "fuzzywuzzy": False,
    }

    # Validar Tesseract
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        validaciones["tesseract"] = True
        validaciones["pytesseract"] = True
    except Exception as e:
        validaciones["error_tesseract"] = str(e)

    # Validar OpenCV
    try:
        import cv2

        validaciones["opencv"] = True
    except ImportError:
        validaciones["error_opencv"] = "opencv-python no está instalado"

    # Validar fuzzywuzzy
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

    return (
        jsonify({"ok": todas_ok, "validaciones": validaciones}),
        200 if todas_ok else 400,
    )
