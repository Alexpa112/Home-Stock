"""Contrasena, otras sesiones, verificacion de email y recuperacion de contrasena."""
from .blueprint import bp
from .comunes import DURACION_TOKEN_RESET_SEGUNDOS, enviar_token_verificacion_email, hash_token, password_valida
import secrets
import time
from flask import session
from werkzeug.security import generate_password_hash
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json, texto_json
from ...config import LONGITUD_PASSWORD_MINIMA
from ...db import get_db
from ...nucleo.red import ip_cliente, limite_por_ip
from ...servicios.cuenta import auditoria
from ...servicios.cuenta.email_service import EmailService
from ...servicios.cuenta.password_pwned import es_password_filtrada


@bp.route("/api/auth/cambiar-password", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_password():
    """Cambiar contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    password_actual = texto_json(datos, "password_actual", recortar=False)
    password_nueva = texto_json(datos, "password_nueva", recortar=False)
    password_confirmacion = texto_json(datos, "password_confirmacion", recortar=False)

    # Validar contraseña nueva
    if len(password_nueva) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_nueva_password_min_8")

    if password_nueva != password_confirmacion:
        return APIResponse.validacion("error_contrasenas_no_coinciden")

    db = get_db()
    usuario = db.execute(
        "SELECT password_hash FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Verificar contraseña actual
    if not password_valida(usuario["password_hash"], password_actual):
        return APIResponse.error("err_password_actual_incorrecta", 400)

    # M-10: la comprobacion de contraseñas filtradas solo se aplicaba en el
    # registro y en el reset, no aqui. El usuario se registraba con una que
    # pasaba el filtro y acto seguido la cambiaba por una conocida, que es el
    # camino que se recorre para "poner una que recuerde". Como
    # es_password_filtrada falla abierto si HIBP no responde, se añade ademas
    # la regla local de que no puede repetir la anterior.
    if password_valida(usuario["password_hash"], password_nueva):
        return APIResponse.validacion("err_password_igual_anterior")

    if es_password_filtrada(password_nueva):
        return APIResponse.validacion("err_password_filtrada")

    # Actualizar contraseña. session_version + 1 invalida cualquier otra
    # sesion abierta con esta cuenta (S-08) - la propia se refresca abajo.
    nuevo_hash = generate_password_hash(password_nueva)
    db.execute(
        "UPDATE usuarios SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
        (nuevo_hash, usuario_id)
    )
    session["session_version"] = db.execute(
        "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()["session_version"]
    auditoria.registrar(db, "cambio_password", usuario_id=usuario_id, ip=ip_cliente())
    db.commit()

    return APIResponse.success({"mensaje": "Contraseña cambiada correctamente"})


@bp.route("/api/auth/cerrar-otras-sesiones", methods=["POST"])
@requerir_sesion
@manejo_errores
def cerrar_otras_sesiones():
    """Invalida cualquier otra sesion abierta con esta cuenta (S-08), sin
    cerrar la que hace la peticion: incrementa session_version en BD y
    refresca la propia sesion al nuevo valor."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    db.execute("UPDATE usuarios SET session_version = session_version + 1 WHERE id = ?", (usuario_id,))
    session["session_version"] = db.execute(
        "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()["session_version"]
    auditoria.registrar(db, "cerrar_otras_sesiones", usuario_id=usuario_id, ip=ip_cliente())
    db.commit()
    return APIResponse.success({"mensaje": "sesiones_cerradas_confirmacion"})


@bp.route("/api/auth/enviar-verificacion-email", methods=["POST"])
@requerir_sesion
@manejo_errores
def enviar_verificacion_email():
    """Genera un token de un solo uso y envia el enlace de verificacion de
    email (S-07). Invalida cualquier token previo no usado del mismo tipo
    para este usuario, para que solo el ultimo enlace enviado sea valido."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    fila = db.execute("SELECT nombre_usuario, email, email_verificado FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if not fila or not fila["email"]:
        return APIResponse.error("err_email_no_configurado", 400)
    if fila["email_verificado"]:
        return APIResponse.error("err_email_ya_verificado", 400)

    enviar_token_verificacion_email(db, usuario_id, fila["nombre_usuario"], fila["email"])
    return APIResponse.success({"mensaje": "verificacion_email_enviada"})


@bp.route("/api/auth/verificar-email", methods=["POST"])
@manejo_errores
def verificar_email():
    # POST con el token en el cuerpo (antes GET con el token en la URL): asi no queda
    # escrito en el log de acceso de gunicorn ni en historiales de proxies.
    token = str(cuerpo_json().get("token") or "")[:200]
    db = get_db()
    fila = db.execute(
        "SELECT id, usuario_id, expira, usado FROM tokens_verificacion WHERE token_hash = ? AND tipo = 'verificar_email'",
        (hash_token(token),),
    ).fetchone()

    if fila is None:
        return APIResponse.error("err_token_invalido", 400)
    if fila["usado"]:
        return APIResponse.error("err_token_usado", 400)
    if fila["expira"] < int(time.time()):
        return APIResponse.error("err_token_expirado", 400)

    db.execute("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (fila["usuario_id"],))
    db.execute("UPDATE tokens_verificacion SET usado = 1 WHERE id = ?", (fila["id"],))
    db.commit()
    return APIResponse.success({"mensaje": "email_verificado_ok"})


@bp.route("/api/auth/solicitar-reset-password", methods=["POST"])
@manejo_errores
def solicitar_reset_password():
    """Solicitud publica de restablecimiento de contraseña. Responde SIEMPRE
    con el mismo mensaje generico, exista o no la cuenta (S-10, mismo
    principio anti-enumeracion), y solo envia email si existe y tiene un
    email verificado."""
    ip = ip_cliente()
    if limite_por_ip(f"reset_password:{ip}", 5, 60 * 60):
        return APIResponse.error("err_demasiadas_peticiones", 429)

    datos = cuerpo_json()
    identificador = texto_json(datos, "usuario_o_email")
    respuesta_generica = APIResponse.success({"mensaje": "mensaje_reset_generico"})
    if not identificador:
        return respuesta_generica

    db = get_db()
    fila = db.execute(
        "SELECT id, nombre_usuario, email, email_verificado FROM usuarios "
        "WHERE LOWER(nombre_usuario) = LOWER(?) OR LOWER(email) = LOWER(?)",
        (identificador, identificador),
    ).fetchone()

    if fila and fila["email"] and fila["email_verificado"]:
        db.execute(
            "UPDATE tokens_verificacion SET usado = 1 WHERE usuario_id = ? AND tipo = 'reset_password' AND usado = 0",
            (fila["id"],),
        )
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira) VALUES (?, 'reset_password', ?, ?)",
            (fila["id"], hash_token(token), int(time.time()) + DURACION_TOKEN_RESET_SEGUNDOS),
        )
        db.commit()
        EmailService.enviar_recuperacion_password(fila["email"], fila["nombre_usuario"], token)

    return respuesta_generica


@bp.route("/api/auth/restablecer-password", methods=["POST"])
@manejo_errores
def restablecer_password():
    datos = cuerpo_json()
    token = texto_json(datos, "token")
    password_nueva = texto_json(datos, "password_nueva", recortar=False)

    if len(password_nueva) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_password_min_8")
    if es_password_filtrada(password_nueva):
        return APIResponse.validacion("err_password_filtrada")

    db = get_db()
    fila = db.execute(
        "SELECT id, usuario_id, expira, usado FROM tokens_verificacion WHERE token_hash = ? AND tipo = 'reset_password'",
        (hash_token(token),),
    ).fetchone()

    if fila is None:
        return APIResponse.error("err_token_invalido", 400)
    if fila["usado"]:
        return APIResponse.error("err_token_usado", 400)
    if fila["expira"] < int(time.time()):
        return APIResponse.error("err_token_expirado", 400)

    # session_version + 1 invalida todas las sesiones activas de esta cuenta
    # (S-08): si el token se filtro/uso por error, quien tuviera una sesion
    # abierta con la contraseña vieja tambien queda fuera.
    db.execute(
        "UPDATE usuarios SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
        (generate_password_hash(password_nueva), fila["usuario_id"]),
    )
    db.execute("UPDATE tokens_verificacion SET usado = 1 WHERE id = ?", (fila["id"],))
    auditoria.registrar(db, "reset_password", usuario_id=fila["usuario_id"], ip=ip_cliente())
    db.commit()
    return APIResponse.success({"mensaje": "password_restablecida_ok"})
