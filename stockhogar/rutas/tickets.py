"""Rutas para escanear tickets de compra y volcarlos al stock."""
import os
import tempfile
from pathlib import Path

from flask import Blueprint, request

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..integraciones import ticket_ocr
from ..servicios.ocr import ProcesadorTicketsV2, crear_respuesta_usuario
from ..utils import Validator
from .productos import crear_producto_nuevo, sumar_stock

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp"}
TAMANO_MAXIMO_MB = 10


def _extension_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


@bp.route("/analizar", methods=["POST"])
@requerir_sesion
@manejo_errores
def analizar_ticket():
    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("No se ha recibido ninguna imagen")

    if not _extension_permitida(archivo.filename):
        return APIResponse.validacion("Formato no permitido. Usa PNG, JPG, etc.")

    archivo.seek(0, os.SEEK_END)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > TAMANO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(f"Archivo demasiado grande (máx {TAMANO_MAXIMO_MB}MB)")

    sufijo = Path(archivo.filename).suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
    tmp.close()
    try:
        archivo.save(tmp.name)

        # Extraer texto con OCR (Tesseract)
        texto_ocr = ticket_ocr.extraer_texto(tmp.name)

        # Procesar con sistema v2 (inteligente, sin IA)
        proc = ProcesadorTicketsV2()
        db = get_db()
        items = proc.procesar_completo(texto_ocr, db)

        # Formatear respuesta para UI con sugerencias
        respuesta = crear_respuesta_usuario(items, db)

    except Exception as e:
        return APIResponse.error(
            f"No se pudo leer la imagen. Comprueba que Tesseract está instalado. Detalle: {str(e)}",
            500
        )
    finally:
        os.unlink(tmp.name)

    return APIResponse.success(respuesta)


@bp.route("/confirmar", methods=["POST"])
@requerir_sesion
@manejo_errores
def confirmar_ticket():
    datos = request.get_json(force=True) or {}
    items = datos.get("items") or []

    db = get_db()
    creados = 0
    actualizados = 0

    for item in items:
        nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue
        cantidad = Validator.entero_no_negativo(item.get("cantidad"), "cantidad")
        unidad = (item.get("unidad") or "ud").strip() or "ud"

        producto_id = item.get("producto_id")
        if producto_id:
            sumar_stock(db, int(producto_id), cantidad)
            actualizados += 1
        else:
            categoria = item.get("categoria") or "Otros"
            crear_producto_nuevo(db, nombre, categoria, cantidad, unidad)
            creados += 1

    db.commit()
    return APIResponse.success({"creados": creados, "actualizados": actualizados})
