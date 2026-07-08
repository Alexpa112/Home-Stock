"""Rutas para escanear tickets de compra y volcarlos al stock."""
import os
import tempfile
from pathlib import Path

from flask import Blueprint, request

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..integraciones import ticket_ocr
from ..utils import Validator
from .productos import crear_producto_nuevo, sumar_stock

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


@bp.route("/analizar", methods=["POST"])
@requerir_sesion
@manejo_errores
def analizar_ticket():
    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("No se ha recibido ninguna imagen")

    sufijo = Path(archivo.filename).suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
    try:
        archivo.save(tmp.name)
        tmp.close()
        items = ticket_ocr.procesar_ticket(tmp.name)
    except Exception:
        return APIResponse.error("No se pudo leer la imagen. Comprueba que Tesseract está instalado.", 500)
    finally:
        os.unlink(tmp.name)

    return APIResponse.success(items)


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
