"""Verificacion en dos pasos por correo: codigos, reenvios y activacion."""
from .blueprint import bp
from .comunes import falta_reautenticar, restaurar_idioma
import hashlib
import hmac
import secrets
import time
from flask import session
from flask_wtf.csrf import generate_csrf
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json, texto_json
from ...db import get_db
from ...nucleo.red import ip_cliente, limite_por_ip
from ...servicios.cuenta import auditoria
from ...servicios.cuenta.email_service import EmailService


def generar_y_enviar_codigo(db, usuario_id, email):
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.execute(
        "INSERT INTO codigos_dos_factor (usuario_id, codigo_hash, expira, intentos) VALUES (?, ?, ?, 0) "
        "ON CONFLICT(usuario_id) DO UPDATE SET codigo_hash = excluded.codigo_hash, expira = excluded.expira, intentos = 0",
        (usuario_id, hash_codigo(codigo), int(time.time()) + DURACION_CODIGO_SEGUNDOS),
    )
    db.commit()
    EmailService.enviar_codigo_verificacion(email, codigo)


def hash_codigo(codigo):
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


DURACION_CODIGO_SEGUNDOS = 10 * 60


MAX_INTENTOS_CODIGO = 10


MAX_REENVIOS_POR_HORA = 3


VENTANA_REENVIOS_SEGUNDOS = 60 * 60


def contador_2fa(db, usuario_id, tipo):
    """Cuenta intentos o reenvíos de 2FA en la última hora."""
    ahora = int(time.time())
    ventana = ahora - VENTANA_REENVIOS_SEGUNDOS
    fila = db.execute(
        "SELECT COUNT(*) AS n FROM intentos_2fa WHERE usuario_id = ? AND tipo = ? AND fecha > ?",
        (usuario_id, tipo, ventana),
    ).fetchone()
    return fila["n"] if fila else 0


def registrar_intento_2fa(db, usuario_id, tipo):
    """Registra un intento o reenvío de 2FA."""
    db.execute(
        "INSERT INTO intentos_2fa (usuario_id, tipo, fecha) VALUES (?, ?, ?)",
        (usuario_id, tipo, int(time.time())),
    )
    db.commit()


@bp.route("/api/auth/verificar-codigo", methods=["POST"])
@manejo_errores
def verificar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    ip = ip_cliente()
    if limite_por_ip(f"2fa_verificar:{ip}", 10, 60 * 60):
        return APIResponse.error("err_demasiados_intentos_2fa", 429)

    datos = cuerpo_json()
    codigo = texto_json(datos, "codigo")

    db = get_db()

    # Bloqueo si se excedieron intentos en la última hora
    intentos = contador_2fa(db, usuario_id, "verificar")
    if intentos >= MAX_INTENTOS_CODIGO:
        session.pop("pendiente_2fa_usuario_id", None)
        return APIResponse.error("err_demasiados_intentos_2fa", 429)

    fila = db.execute(
        "SELECT codigo_hash, expira FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()

    if fila is None or fila["expira"] < int(time.time()):
        session.pop("pendiente_2fa_usuario_id", None)
        return APIResponse.error("err_codigo_expirado", 400)

    # Usar hmac.compare_digest para evitar ataques de temporización (A-5)
    if not hmac.compare_digest(hash_codigo(codigo), fila["codigo_hash"]):
        registrar_intento_2fa(db, usuario_id, "verificar")
        return APIResponse.error("err_codigo_incorrecto", 400)

    db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,))
    db.execute("DELETE FROM intentos_2fa WHERE usuario_id = ? AND tipo = 'verificar'", (usuario_id,))
    db.commit()
    usuario = db.execute("SELECT nombre_usuario, session_version, idioma_preferido FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    session.pop("pendiente_2fa_usuario_id", None)
    session.permanent = True
    session["usuario"] = usuario["nombre_usuario"]
    session["usuario_id"] = usuario_id
    session["session_version"] = usuario["session_version"]
    session["auth_ts"] = int(time.time())
    restaurar_idioma(usuario["idioma_preferido"])
    return APIResponse.success({"usuario": usuario["nombre_usuario"], "csrf_token": generate_csrf()})


@bp.route("/api/auth/reenviar-codigo", methods=["POST"])
@manejo_errores
def reenviar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    ip = ip_cliente()
    if limite_por_ip(f"2fa_reenvio:{ip}", 5, 60 * 60):
        return APIResponse.error("err_demasiados_reenvios_2fa", 429)

    db = get_db()

    # Bloqueo si se excedieron reenvíos en la última hora (A-5)
    reenvios = contador_2fa(db, usuario_id, "reenvio")
    if reenvios >= MAX_REENVIOS_POR_HORA:
        return APIResponse.error("err_demasiados_reenvios_2fa", 429)

    fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if fila is None or not fila["email"]:
        return APIResponse.no_autorizado()

    generar_y_enviar_codigo(db, usuario_id, fila["email"])
    registrar_intento_2fa(db, usuario_id, "reenvio")
    db.execute("DELETE FROM intentos_2fa WHERE usuario_id = ? AND tipo = 'verificar'", (usuario_id,))
    db.commit()
    return APIResponse.success({"reenviado": True})


@bp.route("/api/auth/doble-factor", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_doble_factor():
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    activar = bool(datos.get("activo"))

    db = get_db()
    if activar:
        fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not fila or not fila["email"]:
            return APIResponse.error("err_doble_factor_requiere_email", 400)
    else:
        error_reauth = falta_reautenticar(db, usuario_id, datos)
        if error_reauth:
            return error_reauth

    db.execute("UPDATE usuarios SET doble_factor_activo = ? WHERE id = ?", (int(activar), usuario_id))
    if not activar:
        # Desactivar 2FA reduce la seguridad de la cuenta: invalida otras
        # sesiones que pudieran haber quedado abiertas con el 2FA aun
        # activo, para que el cambio se note de verdad (S-08). Refresca la
        # propia sesion a la nueva version para no cerrarse a si mismo.
        db.execute("UPDATE usuarios SET session_version = session_version + 1 WHERE id = ?", (usuario_id,))
        nueva_version = db.execute("SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()["session_version"]
        session["session_version"] = nueva_version
    auditoria.registrar(db, "cambio_2fa", usuario_id=usuario_id, ip=ip_cliente(), activo=activar)
    db.commit()
    return APIResponse.success({"doble_factor_activo": activar})
