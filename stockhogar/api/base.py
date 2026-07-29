"""Base OOP para blueprints API - Patrón de responsabilidad única."""
from functools import wraps
from flask import jsonify, session
from ..utils.validation import ValidationError
from ..translator import traducir
from ..db import get_db


class APIResponse:
    """Respuestas JSON estándar."""

    @staticmethod
    def success(data=None, status_code=200):
        """Respuesta exitosa."""
        if data is None:
            return "", status_code
        return jsonify(data), status_code

    @staticmethod
    def error(mensaje: str, status_code: int = 400, detalles: dict = None):
        """Respuesta con error. `mensaje` es una clave de traducción."""
        response = {"error": traducir(mensaje)}
        if detalles:
            response.update(detalles)
        return jsonify(response), status_code

    @staticmethod
    def validacion(error_mensaje: str):
        """Error de validación 400."""
        return APIResponse.error(error_mensaje, 400)

    @staticmethod
    def no_autorizado():
        """Error 401."""
        return APIResponse.error("err_no_autenticado", 401)

    @staticmethod
    def no_encontrado(recurso: str = "Recurso"):
        """Error 404. `recurso` es una clave de traducción del nombre del recurso."""
        recurso_traducido = traducir(recurso)
        mensaje = traducir("err_recurso_no_encontrado").replace("{recurso}", recurso_traducido)
        return jsonify({"error": mensaje}), 404

    @staticmethod
    def no_permitido(mensaje: str = None):
        """Error 403."""
        if mensaje is None:
            mensaje = "err_no_permitido"
        return APIResponse.error(mensaje, 403)


def requerir_sesion(f):
    """Decorador: requiere sesión activa con un usuario que siga existiendo.

    Una cookie de sesión firmada sigue siendo válida aunque la cuenta se
    haya borrado (p.ej. "Eliminar Cuenta" desde otro dispositivo) o la BD
    se haya restaurado. Sin esta comprobación, ese usuario_id fantasma
    llega intacto a los INSERT con FK hacia `usuarios` (p.ej. crear lista)
    y salta un IntegrityError que el manejo_errores genérico convierte en
    un 500 "error interno" en vez de pedir volver a iniciar sesión.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        usuario_id = session.get("usuario_id")
        if not usuario_id:
            return APIResponse.no_autorizado()
        existe = get_db().execute(
            "SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if not existe:
            session.clear()
            return APIResponse.no_autorizado()
        return f(*args, **kwargs)
    return decorated


def manejo_errores(f):
    """Decorador: captura excepciones comunes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return APIResponse.validacion(str(e))
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Error no controlado en %s", f.__name__
            )
            return APIResponse.error("err_interno_generico", 500)
    return decorated
