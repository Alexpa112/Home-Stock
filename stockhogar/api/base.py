"""Base OOP para blueprints API - Patrón de responsabilidad única."""
from functools import wraps
from flask import g, jsonify, request, session
from ..utils.validation import ValidationError
from ..translator import traducir
from ..db import get_db


def cuerpo_json():
    """Cuerpo JSON de la petición como dict, o {} si no viene ninguno.

    Sustituye a `request.get_json(force=True) or {}`, que dejaba pasar
    cualquier JSON válido: con un cuerpo escalar (`5`) o una lista, `datos`
    NO era un dict y el primer `datos.get(...)` lanzaba AttributeError, que
    @manejo_errores traduce a 500. Era un 500 provocable sin autenticar en las
    rutas públicas (login, registrar, solicitar-reset-password, log/client).

    Un cuerpo que no sea un objeto es un error del cliente, así que se lanza
    ValidationError y el decorador responde 400.
    """
    datos = request.get_json(force=True, silent=True)
    if datos is None:
        return {}
    if not isinstance(datos, dict):
        raise ValidationError("el cuerpo de la peticion debe ser un objeto JSON")
    return datos


def session_version_en_bd():
    """session_version que la BD tiene para el usuario de la sesión.

    Devuelve None si no hay usuario en sesión o la cuenta ya no existe. El
    resultado se cachea en `g` porque lo consultan tanto el guardián global
    (exigir_sesion) como este decorador, y sin la caché serían dos consultas
    por petición.
    """
    if "session_version_bd" in g:
        return g.session_version_bd

    usuario_id = session.get("usuario_id")
    fila = None
    if usuario_id:
        fila = get_db().execute(
            "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
    g.session_version_bd = fila["session_version"] if fila else None
    return g.session_version_bd



def sesion_revocada() -> bool:
    """True si la cookie trae una session_version que la BD ya no reconoce.

    Ocurre tras un cambio de contraseña, un reset, desactivar el 2FA o pulsar
    "cerrar otras sesiones". Solo se exige si la cookie YA trae
    session_version: una sesión anterior al despliegue que introdujo el campo
    se deja pasar hasta que se renueve con un login nuevo, para no forzar un
    cierre de sesión masivo de cookies válidas ya emitidas.
    """
    if "session_version" not in session or not session.get("usuario_id"):
        return False
    try:
        version_bd = session_version_en_bd()
    except Exception:
        # Esta funcion corre en el guardian global (before_request), FUERA de
        # @manejo_errores: una excepcion aqui no se convertia en un JSON de
        # error sino en la pagina 500 de Flask, y el cliente recibia HTML donde
        # esperaba JSON. Se ha visto con "database is locked" cuando otra
        # conexion mantiene una escritura mas alla del busy_timeout.
        #
        # Ante un fallo de BD se responde "no revocada" a proposito: dar por
        # revocada la sesion cerraria la sesion a TODO el mundo por un problema
        # pasajero de la base de datos. No se cachea nada, asi que la siguiente
        # peticion vuelve a comprobarlo.
        import logging
        logging.getLogger(__name__).warning(
            "No se pudo comprobar session_version; se deja pasar la peticion",
            exc_info=True,
        )
        return False
    return session.get("session_version") != version_bd


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
        if session_version_en_bd() is None:
            # La cuenta ya no existe (borrada desde otro dispositivo, BD
            # restaurada...). Sin esto el usuario_id fantasma llega a los
            # INSERT con FK hacia `usuarios` y sale un 500 en vez de un 401.
            session.clear()
            return APIResponse.no_autorizado()
        # session_version (S-08): ver sesion_revocada(). El guardián global ya
        # limpia la sesión en este caso, pero se comprueba también aquí para
        # que el decorador siga siendo autosuficiente.
        if sesion_revocada():
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
