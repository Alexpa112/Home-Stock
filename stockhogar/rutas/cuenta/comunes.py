"""Piezas compartidas por las rutas de cuenta: tokens, validacion de email y contrasena, reautenticacion e idioma."""
import hashlib
import re
import secrets
import time
from flask import session
from werkzeug.security import check_password_hash, generate_password_hash
from ...api import APIResponse
from ...nucleo.red import limite_por_ip
from ...servicios.cuenta.email_service import EmailService


DURACION_TOKEN_VERIFICACION_SEGUNDOS = 24 * 60 * 60


DURACION_TOKEN_RESET_SEGUNDOS = 60 * 60


_REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


# Hash señuelo con el que se compara cuando el usuario no existe o no tiene
# contraseña, para que el coste en tiempo sea el mismo que el de un usuario
# real y no se pueda enumerar por temporizacion (M-9). Se calcula una vez al
# importar, no en cada peticion.
_HASH_SEÑUELO = generate_password_hash("contraseña señuelo que nadie usa")


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def email_valido(email):
    return bool(email) and len(email) <= 254 and bool(_REGEX_EMAIL.match(email))


def password_valida(password_hash, password):
    """Comprueba la contraseña gastando siempre el mismo tiempo.

    Dos motivos, ambos hallazgos de la auditoria:

    - M-6: las cuentas creadas por OAuth tienen `password_hash` NULL y
      `check_password_hash(None, ...)` lanza AttributeError. Como eso ocurria
      ANTES de registrar_fallo(), esas cuentas quedaban exentas del limite de
      intentos y devolvian un 500 que las distinguia de las inexistentes.
    - M-9: si el usuario no existe no se pagaba el coste de scrypt (~116 ms),
      asi que el tiempo de respuesta revelaba que cuentas existen. Aqui se
      compara contra un hash señuelo para gastar lo mismo en ambos casos.
    """
    if not password_hash:
        check_password_hash(_HASH_SEÑUELO, password or "")
        return False
    return check_password_hash(password_hash, password or "")


def enviar_token_verificacion_email(db, usuario_id, nombre_usuario, email):
    """Invalida los tokens de verificacion previos, emite uno nuevo y lo envia."""
    db.execute(
        "UPDATE tokens_verificacion SET usado = 1 WHERE usuario_id = ? AND tipo = 'verificar_email' AND usado = 0",
        (usuario_id,),
    )
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira) VALUES (?, 'verificar_email', ?, ?)",
        (usuario_id, hash_token(token), int(time.time()) + DURACION_TOKEN_VERIFICACION_SEGUNDOS),
    )
    db.commit()
    EmailService.enviar_verificacion_email(email, nombre_usuario, token)


def falta_reautenticar(db, usuario_id, datos):
    """Respuesta de error si la accion sensible no trae la contrasena actual correcta.

    Desactivar el 2FA o borrar la cuenta con solo la cookie permitia a quien tuviera
    una sesion abierta (movil prestado, cookie robada) dejar la cuenta sin proteccion
    o destruirla. Las cuentas creadas por Google no tienen contrasena: su prueba de
    identidad es el propio proveedor, asi que no se les exige."""
    fila = db.execute("SELECT password_hash FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if fila and fila["password_hash"]:
        if limite_por_ip(f"reauth:{usuario_id}", 10, 60 * 60):
            return APIResponse.error("err_demasiados_intentos_login", 429)
        if not password_valida(fila["password_hash"], datos.get("password_actual") or ""):
            return APIResponse.error("err_password_actual_incorrecta", 400)
    return None


def restaurar_idioma(idioma):
    """Al iniciar sesión recupera el idioma guardado en el perfil."""
    from ...translator import IDIOMAS_DISPONIBLES
    if idioma in IDIOMAS_DISPONIBLES:
        session["idioma"] = idioma
