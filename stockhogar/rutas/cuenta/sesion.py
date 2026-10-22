"""Estado de la sesion, registro, inicio y cierre de sesion."""
from .blueprint import bp
from .comunes import password_valida, restaurar_idioma
from .doble_factor import generar_y_enviar_codigo
import time

from flask import session
from flask_wtf.csrf import generate_csrf
from werkzeug.security import generate_password_hash
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json, texto_json
from ...api.base import revocar_sesion_actual
from ...config import LONGITUD_PASSWORD_MINIMA, REGISTRO_ABIERTO, VERSION_TERMINOS
from ...db import ahora, get_db
from ...nucleo.red import ip_cliente, limite_por_ip
from ...servicios.cuenta import auditoria, intentos_login
from ...servicios.cuenta.password_pwned import es_password_filtrada
from ...utils import Validator, ValidationError


def hay_usuarios(db):
    return db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] > 0


def usuario_actual():
    return session.get("usuario")


@bp.route("/api/auth/estado")
@manejo_errores
def estado():
    db = get_db()
    email = None
    nombre = None
    tema_preferido = "auto"
    idioma_preferido = "es"
    teclado_virtual_activo = "on"
    vista_lista_compra = "lista"
    agrupar_categorias = "off"
    doble_factor_activo = False
    email_verificado = False
    ocr_local = False
    terminos_pendientes = False
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = db.execute(
            "SELECT email, nombre, tema_preferido, idioma_preferido, teclado_virtual_activo, vista_lista_compra, agrupar_categorias, doble_factor_activo, email_verificado, usuario_ocr_local, terminos_version_aceptada FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        if fila:
            email = fila["email"]
            nombre = fila["nombre"]
            tema_preferido = fila["tema_preferido"]
            idioma_preferido = fila["idioma_preferido"]
            teclado_virtual_activo = fila["teclado_virtual_activo"]
            vista_lista_compra = fila["vista_lista_compra"]
            agrupar_categorias = fila["agrupar_categorias"]
            doble_factor_activo = bool(fila["doble_factor_activo"])
            email_verificado = bool(fila["email_verificado"])
            ocr_local = bool(fila["usuario_ocr_local"])
            terminos_pendientes = fila["terminos_version_aceptada"] != VERSION_TERMINOS
    return APIResponse.success(
        {
            "necesita_setup": not hay_usuarios(db),
            "usuario": usuario_actual(),
            "usuario_id": usuario_id,
            "nombre": nombre,
            "email": email,
            "tema_preferido": tema_preferido,
            "idioma_preferido": idioma_preferido,
            "teclado_virtual_activo": teclado_virtual_activo,
            "vista_lista_compra": vista_lista_compra,
            "agrupar_categorias": agrupar_categorias,
            "doble_factor_activo": doble_factor_activo,
            "email_verificado": email_verificado,
            "ocr_local": ocr_local,
            "terminos_pendientes": terminos_pendientes,
        }
    )


@bp.route("/api/auth/registrar", methods=["POST"])
@manejo_errores
def registrar():
    if not REGISTRO_ABIERTO:
        return APIResponse.error("err_registro_cerrado", 403)

    db = get_db()
    datos = cuerpo_json()
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = texto_json(datos, "password", recortar=False)

    # Sin limite se podian crear cuentas a miles (cada una cuesta un hash scrypt).
    if limite_por_ip(f"registro:{ip_cliente()}", 10, 60 * 60):
        return APIResponse.error("err_demasiados_intentos_login", 429)

    if len(password) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_password_min_8")

    if not datos.get("acepta_terminos"):
        return APIResponse.validacion("err_debe_aceptar_terminos")

    if es_password_filtrada(password):
        return APIResponse.validacion("err_password_filtrada")

    existente = db.execute(
        "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
    ).fetchone()
    if existente:
        # NUNCA abrir sesion sobre una cuenta existente: antes se devolvia "creado"
        # con la sesion de la cuenta ajena sin comprobar la contrasena (toma de cuenta).
        # El login ya es opaco ante usuario inexistente; aqui avisar del nombre en uso
        # es lo normal en cualquier registro.
        return APIResponse.error("err_usuario_duplicado", 409)
    try:
        db.execute(
            "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, terminos_version_aceptada, terminos_fecha_aceptacion) "
            "VALUES (?, ?, ?, ?, ?)",
            (nombre_usuario, generate_password_hash(password), ahora(), VERSION_TERMINOS, ahora()),
        )
        db.commit()
        usuario = db.execute(
            "SELECT id, session_version FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
        ).fetchone()
    except Exception:
        raise ValidationError("No se pudo completar el registro")

    auditoria.registrar(db, "registro", usuario_id=usuario["id"], ip=ip_cliente())
    db.commit()

    session.permanent = True
    session["usuario"] = nombre_usuario
    session["usuario_id"] = usuario["id"]
    session["session_version"] = usuario["session_version"] or 0
    session["auth_ts"] = int(time.time())

    return APIResponse.success({"creado": True, "usuario": nombre_usuario, "csrf_token": generate_csrf()}, 201)


@bp.route("/api/auth/login", methods=["POST"])
@manejo_errores
def login():
    ip = ip_cliente()
    datos = cuerpo_json()
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)

    if intentos_login.bloqueada(ip, nombre_usuario):
        return APIResponse.error("err_demasiados_intentos_login", 429)

    password = texto_json(datos, "password", recortar=False)

    db = get_db()
    fila = db.execute(
        "SELECT * FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
    ).fetchone()
    # password_valida gasta siempre el mismo tiempo exista o no la cuenta y
    # tolera password_hash NULL (cuentas OAuth), ver M-6 y M-9.
    if fila is None or not password_valida(fila["password_hash"], password):
        intentos_login.registrar_fallo(ip, nombre_usuario)
        auditoria.registrar(db, "login", usuario_id=fila["id"] if fila else None, ip=ip, resultado="fallo", usuario_intentado=nombre_usuario)
        db.commit()
        return APIResponse.error("err_credenciales_incorrectas", 401)

    intentos_login.limpiar_exito(ip, nombre_usuario)
    auditoria.registrar(db, "login", usuario_id=fila["id"], ip=ip, resultado="ok")
    db.commit()

    if fila["doble_factor_activo"] and fila["email"]:
        generar_y_enviar_codigo(db, fila["id"], fila["email"])
        session["pendiente_2fa_usuario_id"] = fila["id"]
        return APIResponse.success({"requiere_codigo": True, "csrf_token": generate_csrf()})

    session.permanent = True
    session["usuario"] = fila["nombre_usuario"]
    session["usuario_id"] = fila["id"]
    session["session_version"] = fila["session_version"]
    session["auth_ts"] = int(time.time())
    restaurar_idioma(fila["idioma_preferido"])
    return APIResponse.success({"usuario": fila["nombre_usuario"], "csrf_token": generate_csrf()})


@bp.route("/api/auth/logout", methods=["POST"])
@requerir_sesion
@manejo_errores
def logout():
    revocar_sesion_actual()
    session.clear()
    return APIResponse.success()
