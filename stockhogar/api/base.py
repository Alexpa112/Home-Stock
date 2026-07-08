"""Base OOP para blueprints API - Patrón de responsabilidad única."""
from functools import wraps
from flask import jsonify, session
from ..utils.validation import ValidationError


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
        """Respuesta con error."""
        response = {"error": mensaje}
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
        return APIResponse.error("No has iniciado sesión", 401)

    @staticmethod
    def no_encontrado(recurso: str = "Recurso"):
        """Error 404."""
        return APIResponse.error(f"{recurso} no encontrado", 404)

    @staticmethod
    def no_permitido(mensaje: str = "No tienes permiso para esta acción"):
        """Error 403."""
        return APIResponse.error(mensaje, 403)


def requerir_sesion(f):
    """Decorador: requiere sesión activa."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario_id"):
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
        except Exception as e:
            import traceback
            traceback.print_exc()
            return APIResponse.error(f"Error interno: {str(e)}", 500)
    return decorated
