"""Autenticación: login, registro, logout y gestión de usuarios."""
import hashlib
import secrets
import time

from flask import Blueprint, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import VERSION_TERMINOS
from ..db import ahora, get_db
from ..servicios import intentos_login
from ..servicios.email_service import EmailService
from ..utils import Validator, DataConverter

bp = Blueprint("auth", __name__)

# Endpoints accesibles sin haber iniciado sesion (usados por el guardian
# global en __init__.py).
RUTAS_PUBLICAS = {
    "auth.estado",
    "auth.login",
    "auth.registrar",
    "auth.verificar_codigo_dos_pasos",
    "auth.reenviar_codigo_dos_pasos",
    "oauth.oauth_google",
    "oauth.oauth_google_callback",
    "oauth.oauth_apple",
    "oauth.oauth_apple_callback",
    "paginas.log_client_error",
    "paginas.csrf_token",
    "paginas.mantenimiento_stream",
    "idiomas.obtener_todas_traducciones",
    "idiomas.obtener_idioma",
    "legal.configuracion_legal",
}


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
    terminos_pendientes = False
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = db.execute(
            "SELECT email, nombre, tema_preferido, idioma_preferido, teclado_virtual_activo, vista_lista_compra, agrupar_categorias, doble_factor_activo, terminos_version_aceptada FROM usuarios WHERE id = ?",
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
            "terminos_pendientes": terminos_pendientes,
        }
    )


@bp.route("/api/auth/registrar", methods=["POST"])
@manejo_errores
def registrar():
    db = get_db()
    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = datos.get("password") or ""

    if len(password) < 8:
        return APIResponse.validacion("err_password_min_8")

    if not datos.get("acepta_terminos"):
        return APIResponse.validacion("err_debe_aceptar_terminos")

    existente = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if existente:
        return APIResponse.error("err_usuario_duplicado", 400)

    db.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, terminos_version_aceptada, terminos_fecha_aceptacion) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre_usuario, generate_password_hash(password), ahora(), VERSION_TERMINOS, ahora()),
    )
    db.commit()

    # Iniciar sesión automáticamente después de registrar
    usuario = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()

    session.permanent = True
    session["usuario"] = nombre_usuario
    session["usuario_id"] = usuario["id"]

    return APIResponse.success({"creado": True, "usuario": nombre_usuario}, 201)


@bp.route("/api/auth/login", methods=["POST"])
@manejo_errores
def login():
    ip = request.remote_addr or "desconocida"
    if intentos_login.bloqueada(ip):
        return APIResponse.error("err_demasiados_intentos_login", 429)

    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = datos.get("password") or ""

    db = get_db()
    fila = db.execute(
        "SELECT * FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if fila is None or not check_password_hash(fila["password_hash"], password):
        intentos_login.registrar_fallo(ip)
        return APIResponse.no_autorizado()

    intentos_login.limpiar_exito(ip)

    if fila["doble_factor_activo"] and fila["email"]:
        _generar_y_enviar_codigo(db, fila["id"], fila["email"])
        session["pendiente_2fa_usuario_id"] = fila["id"]
        return APIResponse.success({"requiere_codigo": True})

    session.permanent = True
    session["usuario"] = fila["nombre_usuario"]
    session["usuario_id"] = fila["id"]
    return APIResponse.success({"usuario": fila["nombre_usuario"]})


def _generar_y_enviar_codigo(db, usuario_id, email):
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.execute(
        "INSERT INTO codigos_dos_factor (usuario_id, codigo_hash, expira, intentos) VALUES (?, ?, ?, 0) "
        "ON CONFLICT(usuario_id) DO UPDATE SET codigo_hash = excluded.codigo_hash, expira = excluded.expira, intentos = 0",
        (usuario_id, _hash_codigo(codigo), int(time.time()) + DURACION_CODIGO_SEGUNDOS),
    )
    db.commit()
    EmailService.enviar_codigo_verificacion(email, codigo)


def _hash_codigo(codigo):
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


DURACION_CODIGO_SEGUNDOS = 10 * 60
MAX_INTENTOS_CODIGO = 5


@bp.route("/api/auth/verificar-codigo", methods=["POST"])
@manejo_errores
def verificar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    datos = request.get_json(force=True) or {}
    codigo = (datos.get("codigo") or "").strip()

    db = get_db()
    fila = db.execute(
        "SELECT codigo_hash, expira, intentos FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()

    if fila is None or fila["intentos"] >= MAX_INTENTOS_CODIGO or fila["expira"] < int(time.time()):
        session.pop("pendiente_2fa_usuario_id", None)
        return APIResponse.error("err_codigo_expirado", 400)

    if _hash_codigo(codigo) != fila["codigo_hash"]:
        db.execute("UPDATE codigos_dos_factor SET intentos = intentos + 1 WHERE usuario_id = ?", (usuario_id,))
        db.commit()
        return APIResponse.error("err_codigo_incorrecto", 400)

    db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,))
    db.commit()
    usuario = db.execute("SELECT nombre_usuario FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    session.pop("pendiente_2fa_usuario_id", None)
    session.permanent = True
    session["usuario"] = usuario["nombre_usuario"]
    session["usuario_id"] = usuario_id
    return APIResponse.success({"usuario": usuario["nombre_usuario"]})


@bp.route("/api/auth/reenviar-codigo", methods=["POST"])
@manejo_errores
def reenviar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    db = get_db()
    fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if fila is None or not fila["email"]:
        return APIResponse.no_autorizado()

    _generar_y_enviar_codigo(db, usuario_id, fila["email"])
    return APIResponse.success({"reenviado": True})


@bp.route("/api/auth/doble-factor", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_doble_factor():
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    activar = bool(datos.get("activo"))

    db = get_db()
    if activar:
        fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not fila or not fila["email"]:
            return APIResponse.error("err_doble_factor_requiere_email", 400)

    db.execute("UPDATE usuarios SET doble_factor_activo = ? WHERE id = ?", (int(activar), usuario_id))
    db.commit()
    return APIResponse.success({"doble_factor_activo": activar})


@bp.route("/api/auth/aceptar-terminos", methods=["POST"])
@requerir_sesion
@manejo_errores
def aceptar_terminos():
    """Registra la aceptación de la versión vigente de Términos y Privacidad.

    Cubre tanto al usuario que se registra por Google/Apple (no pasa por el
    formulario de registro, así que no acepta ahí) como al que ya tenía
    cuenta antes de introducir esta versión de los términos.
    """
    usuario_id = session.get("usuario_id")
    db = get_db()
    db.execute(
        "UPDATE usuarios SET terminos_version_aceptada = ?, terminos_fecha_aceptacion = ? WHERE id = ?",
        (VERSION_TERMINOS, ahora(), usuario_id),
    )
    db.commit()
    return APIResponse.success({"version_terminos": VERSION_TERMINOS})


@bp.route("/api/auth/logout", methods=["POST"])
@requerir_sesion
@manejo_errores
def logout():
    session.clear()
    return APIResponse.success()


@bp.route("/api/auth/perfil", methods=["PUT"])
@requerir_sesion
@manejo_errores
def actualizar_perfil():
    """Actualizar usuario (login), nombre a mostrar y/o contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    nombre_usuario_nuevo = datos.get("usuario", "").strip()
    nombre = datos.get("nombre", "").strip()
    password = datos.get("password", "").strip()

    db = get_db()
    usuario = db.execute(
        "SELECT nombre_usuario FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Actualizar usuario (login) si se proporciona
    if nombre_usuario_nuevo:
        if len(nombre_usuario_nuevo) > 80:
            return APIResponse.validacion("err_nombre_max_80")
        duplicado = db.execute(
            "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE AND id != ?",
            (nombre_usuario_nuevo, usuario_id)
        ).fetchone()
        if duplicado:
            return APIResponse.error("err_usuario_duplicado", 400)
        db.execute(
            "UPDATE usuarios SET nombre_usuario = ? WHERE id = ?",
            (nombre_usuario_nuevo, usuario_id)
        )
        session["usuario"] = nombre_usuario_nuevo

    # Actualizar nombre a mostrar si se proporciona (independiente del usuario de login)
    if nombre:
        if len(nombre) > 80:
            return APIResponse.validacion("err_nombre_max_80")
        db.execute(
            "UPDATE usuarios SET nombre = ? WHERE id = ?",
            (nombre, usuario_id)
        )

    # Actualizar contraseña si se proporciona
    if password:
        if len(password) < 8:
            return APIResponse.validacion("err_password_min_8")
        nuevo_hash = generate_password_hash(password)
        db.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (nuevo_hash, usuario_id)
        )

    db.commit()
    fila = db.execute("SELECT nombre FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return APIResponse.success({"usuario": session.get("usuario"), "nombre": fila["nombre"] if fila else None})


@bp.route("/api/auth/tema", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_tema():
    """Guarda la preferencia de tema (light/dark/auto) del usuario."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    tema = (datos.get("tema") or "auto").strip().lower()

    if tema not in ("light", "dark", "auto"):
        return APIResponse.validacion("Tema no válido. Debe ser 'light', 'dark' o 'auto'")

    db = get_db()
    db.execute("UPDATE usuarios SET tema_preferido = ? WHERE id = ?", (tema, usuario_id))
    db.commit()

    return APIResponse.success({"tema": tema})


@bp.route("/api/auth/teclado-virtual", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_teclado_virtual():
    """Guarda si el usuario quiere el teclado virtual propio (on/off)."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    valor = (datos.get("teclado_virtual_activo") or "on").strip().lower()

    if valor not in ("on", "off"):
        return APIResponse.validacion("Valor no válido. Debe ser 'on' u 'off'")

    db = get_db()
    db.execute("UPDATE usuarios SET teclado_virtual_activo = ? WHERE id = ?", (valor, usuario_id))
    db.commit()

    return APIResponse.success({"teclado_virtual_activo": valor})


@bp.route("/api/auth/cambiar-password", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_password():
    """Cambiar contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    password_actual = datos.get("password_actual") or ""
    password_nueva = datos.get("password_nueva") or ""
    password_confirmacion = datos.get("password_confirmacion") or ""

    # Validar contraseña nueva
    if len(password_nueva) < 8:
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
    if not check_password_hash(usuario["password_hash"], password_actual):
        return APIResponse.error("err_password_actual_incorrecta", 400)

    # Actualizar contraseña
    nuevo_hash = generate_password_hash(password_nueva)
    db.execute(
        "UPDATE usuarios SET password_hash = ? WHERE id = ?",
        (nuevo_hash, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Contraseña cambiada correctamente"})


@bp.route("/api/auth/preferencias-listas", methods=["POST"])
@requerir_sesion
@manejo_errores
def actualizar_preferencias_listas():
    """Actualiza las preferencias de vista de la lista de la compra (lista/recuadros) y agrupación por categorías."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}

    vista = (datos.get("vista_lista_compra") or "lista").strip().lower()
    agrupar = (datos.get("agrupar_categorias") or "off").strip().lower()

    if vista not in ("lista", "recuadros"):
        return APIResponse.validacion("Vista no válida. Debe ser 'lista' o 'recuadros'")
    if agrupar not in ("on", "off"):
        return APIResponse.validacion("Agrupación no válida. Debe ser 'on' u 'off'")

    db = get_db()
    db.execute(
        "UPDATE usuarios SET vista_lista_compra = ?, agrupar_categorias = ? WHERE id = ?",
        (vista, agrupar, usuario_id)
    )
    db.commit()

    return APIResponse.success({
        "vista_lista_compra": vista,
        "agrupar_categorias": agrupar
    })


@bp.route("/api/usuarios", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_usuarios():
    """Lista solo los usuarios con los que la sesión actual comparte al menos
    una lista (propia o compartida), nunca todos los usuarios de la instalación."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    filas = db.execute(
        """
        SELECT DISTINCT u.id, u.nombre_usuario, u.fecha_creacion
        FROM usuarios u
        WHERE u.id = ?
           OR u.id IN (
                SELECT l.usuario_propietario_id FROM hogares l
                WHERE l.id IN (
                    SELECT id FROM hogares WHERE usuario_propietario_id = ?
                    UNION
                    SELECT hogar_id FROM permisos_hogar WHERE usuario_id = ?
                )
           )
           OR u.id IN (
                SELECT p.usuario_id FROM permisos_hogar p
                WHERE p.hogar_id IN (
                    SELECT id FROM hogares WHERE usuario_propietario_id = ?
                    UNION
                    SELECT hogar_id FROM permisos_hogar WHERE usuario_id = ?
                )
           )
        ORDER BY u.fecha_creacion
        """,
        (usuario_id, usuario_id, usuario_id, usuario_id, usuario_id),
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])


@bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_usuario(usuario_id):
    if session.get("usuario_id") != usuario_id:
        return APIResponse.no_permitido()

    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    if total <= 1:
        return APIResponse.error("err_ultimo_usuario", 400)

    db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    db.commit()
    session.clear()
    return APIResponse.success()
