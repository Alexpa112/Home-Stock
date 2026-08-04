"""Rutas para escanear tickets de compra y volcarlos al stock."""
import logging
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
from ..servicios.ocr.groq_ocr import GroqOCR
from ..servicios.ocr.matcher_inteligente import MatcherInteligente
from ..utils import Validator
from ..servicios.stock import crear_producto_nuevo, sumar_stock, hogar_actual_con_permiso

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "heic", "heif", "pdf"}
TAMANO_MAXIMO_MB = 10

_MIME_POR_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
}


def _items_desde_ia(respuesta_ia, productos_catalogo, db):
    """Convierte la respuesta de la IA (ya emparejada con el catálogo) al
    mismo formato de "items" que produce ProcesadorTicketsV2, para que
    crear_respuesta_usuario() y el resto del flujo (confirmar_ticket, UI) no
    tengan que distinguir qué motor de OCR se usó.
    """
    catalogo_por_id = {p["id"]: p for p in productos_catalogo}
    matcher = MatcherInteligente()
    items = []
    for item in respuesta_ia.get("productos", []):
        producto_id = item.get("producto_id")
        catalogado = catalogo_por_id.get(producto_id) if producto_id is not None else None

        if catalogado:
            nombre = catalogado["nombre"]
            categoria = catalogado["categoria"]
            confianza_match = 1.0
        else:
            nombre = (item.get("nombre_ticket") or "").strip().title()
            if not nombre:
                continue
            categoria = matcher.deducir_categoria(nombre) or "Otros"
            confianza_match = 0
            producto_id = None

        items.append({
            "nombre": nombre,
            "cantidad": item.get("cantidad") or 1,
            "unidad": item.get("unidad") or "ud",
            "categoria": categoria,
            "producto_id": producto_id,
            "confianza_match": confianza_match,
            # La IA no da confianza de OCR por línea ni precios: se asume
            # cantidad fiable y no se aplica la validación de precio del
            # pipeline local (pensada para lo que devuelve Tesseract).
            "confianza_cantidad": 100,
            "precio_valido": True,
        })
    return items


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


def _convertir_heic_a_imagen(ruta_heic):
    """Convierte una foto HEIC/HEIF (formato por defecto de la camara de
    iPhone al elegir "Subir archivo" desde la galeria, en vez de "Hacer
    foto") a PNG con libheif (heif-convert).

    Mismo motivo que con el PDF (ver _convertir_pdf_a_imagen): se usa el
    binario de sistema (paquete Debian libheif-examples, con build nativo
    para armv7l/aarch64) en vez de bindings Python (pillow-heif, pyheif),
    que no siempre publican wheels para armv7l y forzarian compilar libheif
    desde fuente en la Raspberry Pi.
    """
    ruta_png = ruta_heic + "_convertida.png"
    try:
        resultado = subprocess.run(
            ["heif-convert", ruta_heic, ruta_png],
            capture_output=True, timeout=30
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

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
    ruta_png_convertida = None
    try:
        archivo.save(tmp.name)

        ruta_imagen = tmp.name
        if sufijo == ".pdf":
            ruta_png_convertida = _convertir_pdf_a_imagen(tmp.name)
            if not ruta_png_convertida:
                return APIResponse.error("err_procesando_ticket", 500)
            ruta_imagen = ruta_png_convertida
        elif sufijo in (".heic", ".heif"):
            ruta_png_convertida = _convertir_heic_a_imagen(tmp.name)
            if not ruta_png_convertida:
                return APIResponse.error("err_procesando_ticket", 500)
            ruta_imagen = ruta_png_convertida

        db = get_db()

        # Motor principal: Groq/Llama 4 Scout (foto + catálogo del usuario,
        # OCR y emparejamiento semántico en un solo paso). Si no hay
        # GROQ_API_KEY, o la llamada falla o no reconoce nada, se cae al
        # pipeline local (Tesseract + ProcesadorTicketsV2) como respaldo.
        items = None
        groq = GroqOCR()
        if groq.disponible():
            productos_catalogo = [
                dict(row)
                for row in db.execute(
                    "SELECT id, nombre, categoria FROM productos ORDER BY nombre"
                ).fetchall()
            ]
            with open(ruta_imagen, "rb") as f:
                imagen_bytes = f.read()
            mime_type = _MIME_POR_EXTENSION.get(Path(ruta_imagen).suffix.lower(), "image/jpeg")
            respuesta_ia = groq.procesar(imagen_bytes, productos_catalogo, mime_type=mime_type)
            if respuesta_ia is not None:
                items = _items_desde_ia(respuesta_ia, productos_catalogo, db)
                logging.getLogger(__name__).info(
                    "Ticket analizado con Groq: %d items detectados. Items: %s",
                    len(items), [(i["nombre"], i["cantidad"], i["confianza_match"]) for i in items],
                )

        if items is None:
            # Extraer texto con OCR (Tesseract)
            texto_ocr = ticket_ocr.extraer_texto(ruta_imagen)

            # Procesar con sistema v2 (inteligente, sin IA)
            proc = ProcesadorTicketsV2()
            items = proc.procesar_completo(texto_ocr, db)

            # Diagnostico: sin esto, un ticket mal reconocido (OCR ilegible o
            # parser que descarta/lee mal las lineas) no deja ningun rastro para
            # saber si el fallo esta en Tesseract o en el parser, y el Panel de
            # Gestion del Servidor es la unica forma de ver que paso en la Pi.
            logging.getLogger(__name__).info(
                "Ticket analizado con Tesseract: %d lineas OCR, %d items detectados. Texto OCR:\n%s\nItems: %s",
                len(texto_ocr.splitlines()), len(items), texto_ocr,
                [(i["nombre"], i["cantidad"], i["confianza_match"]) for i in items],
            )

        # Formatear respuesta para UI con sugerencias
        respuesta = crear_respuesta_usuario(items, db)

    except Exception as e:
        # No se devuelve str(e) al cliente: puede filtrar rutas de fichero
        # temporales o detalles internos de librerías (ver @manejo_errores,
        # que para el resto de endpoints ya evita esto con un mensaje
        # generico). Aqui se hacia una excepcion para dar una pista sobre
        # Tesseract, pero el detalle real solo debe ir al log del servidor.
        logging.getLogger(__name__).exception("Error analizando ticket")
        return APIResponse.error("err_interno_generico", 500)
    finally:
        os.unlink(tmp.name)
        if ruta_png_convertida and os.path.exists(ruta_png_convertida):
            os.unlink(ruta_png_convertida)

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
        cantidad = Validator.entero_no_negativo(Validator.con_defecto(item, "cantidad", 1), "cantidad")
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
