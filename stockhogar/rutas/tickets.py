"""Rutas para escanear tickets de compra y volcarlos al stock."""
import os
import subprocess
import tempfile
from pathlib import Path

from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..translator import traducir
from ..integraciones import ticket_ocr
from ..servicios.ocr import ProcesadorTicketsV2, crear_respuesta_usuario
from ..utils import Validator
from ..servicios.stock import crear_producto_nuevo, sumar_stock, hogar_actual_con_permiso

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp", "pdf"}
TAMANO_MAXIMO_MB = 10


def _extension_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def _convertir_pdf_a_imagen(ruta_pdf):
    """Convierte la primera pagina de un PDF a PNG con Poppler (pdftoppm).

    Se usa el binario de sistema en vez de una libreria Python (p.ej.
    PyMuPDF) porque poppler-utils tiene paquete Debian nativo para
    armv7l/aarch64 (Raspberry Pi); las alternativas Python no siempre
    publican wheels para armv7l y forzarian compilar desde fuente.
    """
    prefijo = ruta_pdf + "_pagina"
    try:
        resultado = subprocess.run(
            ["pdftoppm", "-png", "-r", "300", "-singlefile", ruta_pdf, prefijo],
            capture_output=True, timeout=30
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    ruta_png = prefijo + ".png"
    if resultado.returncode != 0 or not os.path.exists(ruta_png):
        return None
    return ruta_png


@bp.route("/analizar", methods=["POST"])
@requerir_sesion
@manejo_errores
def analizar_ticket():
    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("err_sin_imagen")

    if not _extension_permitida(archivo.filename):
        return APIResponse.validacion("err_formato_no_permitido")

    archivo.seek(0, os.SEEK_END)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > TAMANO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(TAMANO_MAXIMO_MB))
        )

    sufijo = Path(archivo.filename).suffix.lower() or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=sufijo, delete=False)
    tmp.close()
    ruta_png_pdf = None
    try:
        archivo.save(tmp.name)

        ruta_imagen = tmp.name
        if sufijo == ".pdf":
            ruta_png_pdf = _convertir_pdf_a_imagen(tmp.name)
            if not ruta_png_pdf:
                return APIResponse.error("err_procesando_ticket", 500)
            ruta_imagen = ruta_png_pdf

        # Extraer texto con OCR (Tesseract)
        texto_ocr = ticket_ocr.extraer_texto(ruta_imagen)

        # Procesar con sistema v2 (inteligente, sin IA)
        proc = ProcesadorTicketsV2()
        db = get_db()
        items = proc.procesar_completo(texto_ocr, db)

        # Formatear respuesta para UI con sugerencias
        respuesta = crear_respuesta_usuario(items, db)

    except Exception as e:
        # No se devuelve str(e) al cliente: puede filtrar rutas de fichero
        # temporales o detalles internos de librerías (ver @manejo_errores,
        # que para el resto de endpoints ya evita esto con un mensaje
        # generico). Aqui se hacia una excepcion para dar una pista sobre
        # Tesseract, pero el detalle real solo debe ir al log del servidor.
        import logging
        logging.getLogger(__name__).exception("Error analizando ticket")
        return APIResponse.error("err_interno_generico", 500)
    finally:
        os.unlink(tmp.name)
        if ruta_png_pdf and os.path.exists(ruta_png_pdf):
            os.unlink(ruta_png_pdf)

    return APIResponse.success(respuesta)


@bp.route("/confirmar", methods=["POST"])
@requerir_sesion
@manejo_errores
def confirmar_ticket():
    """Confirma los items de un ticket escaneado y los aplica al stock.

    Requiere permiso de 'editar' en la lista activa: sin esta comprobacion,
    sumar_stock()/crear_producto_nuevo() resolvian la lista de sesion sin
    verificar ningun permiso (a diferencia de todos los endpoints de
    productos.py), permitiendo a un usuario con acceso de solo lectura -o
    sin ningun acceso ya revocado- seguir modificando el stock de una lista
    ajena subiendo un ticket.
    """
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    items = datos.get("items") or []

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
            sumar_stock(db, int(producto_id), cantidad, hogar_id)
            actualizados += 1
        else:
            categoria = item.get("categoria") or "Otros"
            crear_producto_nuevo(db, nombre, categoria, cantidad, unidad, hogar_id=hogar_id)
            creados += 1

    db.commit()
    return APIResponse.success({"creados": creados, "actualizados": actualizados})
