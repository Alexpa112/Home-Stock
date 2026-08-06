"""Validacion y recodificacion de imagenes subidas por el usuario (S-16).

Antes solo se comprobaba la EXTENSION del nombre de fichero, nunca el
contenido real: un fichero renombrado a ".jpg" que en realidad fuera otra
cosa (o un "polyglot", valido a la vez como imagen y como otro formato)
pasaba sin problema. Abrir el fichero con Pillow y volver a guardarlo
descarta cualquier dato que no sea la imagen en si (metadatos EXIF,
comentarios, bytes añadidos tras el fin de la imagen) de un plumazo, sin
necesitar un parser de metadatos aparte.

No cubre HEIC/HEIF: Pillow no los decodifica en este proyecto a proposito
(ver stockhogar/rutas/tickets.py::_convertir_heic_a_imagen, no hay wheel de
pillow-heif para armv7l). Los ficheros HEIC/HEIF quedan fuera de esta
validacion; quien los acepte debe convertirlos primero con heif-convert.
"""
import io
import logging

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

_FORMATOS_PILLOW_POR_EXTENSION = {
    "jpg": "JPEG", "jpeg": "JPEG", "png": "PNG",
    "gif": "GIF", "webp": "WEBP", "bmp": "BMP",
}


def validar_y_recodificar(imagen_bytes: bytes, extension: str):
    """Comprueba que `imagen_bytes` es de verdad una imagen del formato que
    dice su extension, y devuelve una copia recodificada (sin metadatos).

    Devuelve (bytes_recodificados, None) si es valida, o (None, mensaje_error)
    si no. `extension` sin el punto, en minusculas (p.ej. "jpg").
    """
    formato_esperado = _FORMATOS_PILLOW_POR_EXTENSION.get(extension)
    if formato_esperado is None:
        # Extension no cubierta por esta validacion (p.ej. heic/heif): se
        # deja pasar sin recodificar, la llama quien sepa tratarla.
        return imagen_bytes, None

    try:
        imagen = Image.open(io.BytesIO(imagen_bytes))
        imagen.verify()
        # Image.verify() invalida el objeto para seguir leyendo pixeles;
        # hay que reabrirlo para poder recodificarlo despues.
        imagen = Image.open(io.BytesIO(imagen_bytes))
        if imagen.format != formato_esperado:
            return None, "err_formato_no_permitido"

        salida = io.BytesIO()
        if formato_esperado == "JPEG" and imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")
        imagen.save(salida, format=formato_esperado)
        return salida.getvalue(), None
    except (UnidentifiedImageError, OSError, ValueError):
        return None, "err_formato_no_permitido"
