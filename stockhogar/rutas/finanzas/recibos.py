"""Foto de recibo adjunta a un gasto (subida validada y recodificada, cifrada en reposo)."""
from .blueprint import bp
from .comunes import obtener_gasto_con_permiso
from datetime import date
from pathlib import Path
from flask import Response, request, session
from ...api import APIResponse, manejo_errores, requerir_sesion
from ...nucleo import cifrado
from ...config import LIMITE_RECIBOS_DIARIO_POR_USUARIO
from ...db import get_db
from ...translator import traducir
from ...utils.imagenes import validar_y_recodificar


RECIBO_EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "heif"}


RECIBO_TAMANO_MAXIMO_MB = 8


RECIBO_MIME_POR_EXTENSION = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "heic": "image/heic", "heif": "image/heif",
}


def _extension_recibo_permitida(filename):
    # M-15: usar Path().suffix consistentemente con el resto del codigo en vez
    # de rsplit, que discrepaba permitiendo bypasses por dotfile (como .png).
    extension = Path(filename).suffix.lower().lstrip(".")
    return bool(extension) and extension in RECIBO_EXTENSIONES_PERMITIDAS


@bp.route("/<int:gasto_id>/recibo", methods=["POST"])
@requerir_sesion
@manejo_errores
def subir_recibo(gasto_id):
    """Adjunta (o reemplaza) la foto de recibo de un gasto."""
    db = get_db()
    gasto, error = obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar")
    if error:
        return error

    usuario_id = session.get("usuario_id")
    hoy = date.today().isoformat()
    uso_hoy = db.execute(
        "SELECT contador FROM uso_recibos_diario WHERE usuario_id = ? AND fecha = ?", (usuario_id, hoy)
    ).fetchone()
    if uso_hoy and uso_hoy["contador"] >= LIMITE_RECIBOS_DIARIO_POR_USUARIO:
        return APIResponse.error("err_limite_recibos_diario", 429)

    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("err_sin_imagen")
    if not _extension_recibo_permitida(archivo.filename):
        return APIResponse.validacion("err_formato_no_permitido")

    archivo.seek(0, 2)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > RECIBO_TAMANO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(RECIBO_TAMANO_MAXIMO_MB))
        )

    extension = Path(archivo.filename).suffix.lower().lstrip(".")
    mime_type = RECIBO_MIME_POR_EXTENSION.get(extension, "application/octet-stream")

    # Recodificar (S-16): confirma que el contenido es de verdad una imagen
    # del formato que dice la extension (no solo un fichero renombrado) y
    # descarta metadatos/bytes extra antes de guardarla en la BD a largo
    # plazo. HEIC/HEIF no pasa por Pillow (ver utils/imagenes.py) y se
    # guarda tal cual, igual que antes de este cambio.
    imagen_validada, error_validacion = validar_y_recodificar(archivo.read(), extension)
    if error_validacion:
        return APIResponse.validacion(error_validacion)

    db.execute(
        "UPDATE gastos SET imagen_recibo = ?, imagen_recibo_mime = ? WHERE id = ?",
        (cifrado.cifrar_bytes(imagen_validada), mime_type, gasto_id),
    )
    db.execute(
        "INSERT INTO uso_recibos_diario (usuario_id, fecha, contador) VALUES (?, ?, 1) "
        "ON CONFLICT(usuario_id, fecha) DO UPDATE SET contador = contador + 1",
        (usuario_id, hoy),
    )
    db.commit()
    return APIResponse.success({"tiene_recibo": True})


@bp.route("/<int:gasto_id>/recibo", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_recibo(gasto_id):
    """Sirve la foto de recibo adjunta a un gasto."""
    db = get_db()
    gasto, error = obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="ver", con_imagen=True)
    if error:
        return error
    if not gasto["imagen_recibo"]:
        return APIResponse.no_encontrado("recurso_recibo")

    imagen = cifrado.descifrar_bytes(gasto["imagen_recibo"])
    if imagen is None:
        return APIResponse.no_encontrado("recurso_recibo")
    return Response(imagen, mimetype=gasto["imagen_recibo_mime"] or "application/octet-stream")


@bp.route("/<int:gasto_id>/recibo", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_recibo(gasto_id):
    """Elimina la foto de recibo adjunta a un gasto."""
    db = get_db()
    gasto, error = obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar")
    if error:
        return error

    db.execute("UPDATE gastos SET imagen_recibo = NULL, imagen_recibo_mime = NULL WHERE id = ?", (gasto_id,))
    db.commit()
    return APIResponse.success()
