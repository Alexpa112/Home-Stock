"""Alta del primer usuario, login, logout y gestion de usuarios."""
from flask import Blueprint, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..utils import Validator, DataConverter

bp = Blueprint("auth", __name__)

# Endpoints accesibles sin haber iniciado sesion (usados por el guardian
# global en __init__.py).
RUTAS_PUBLICAS = {
    "auth.pagina_login",
    "auth.estado",
    "auth.login",
    "auth.registrar",
    "oauth.oauth_google",
    "oauth.oauth_google_callback",
    "oauth.oauth_apple",
    "oauth.oauth_apple_callback",
    "static",
}


def hay_usuarios(db):
    return db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] > 0


def usuario_actual():
    return session.get("usuario")


@bp.route("/login")
def pagina_login():
    return render_template("login.html", modo_setup=not hay_usuarios(get_db()))


@bp.route("/api/auth/estado")
@manejo_errores
def estado():
    db = get_db()
    return APIResponse.success({"necesita_setup": not hay_usuarios(db), "usuario": usuario_actual()})


@bp.route("/api/auth/registrar", methods=["POST"])
@manejo_errores
def registrar():
    db = get_db()
    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = datos.get("password") or ""

    if len(password) < 4:
        return APIResponse.validacion("La contraseña debe tener al menos 4 caracteres")

    if hay_usuarios(db) and not usuario_actual():
        return APIResponse.no_autorizado()

    existente = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if existente:
        return APIResponse.error("Ya existe un usuario con ese nombre", 400)

    db.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
        (nombre_usuario, generate_password_hash(password), ahora()),
    )
    db.commit()
    return APIResponse.success({"creado": True}, 201)


@bp.route("/api/auth/login", methods=["POST"])
@manejo_errores
def login():
    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = datos.get("password") or ""

    db = get_db()
    fila = db.execute(
        "SELECT * FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if fila is None or not check_password_hash(fila["password_hash"], password):
        return APIResponse.no_autorizado()

    session.permanent = True
    session["usuario"] = fila["nombre_usuario"]
    session["usuario_id"] = fila["id"]
    return APIResponse.success({"usuario": fila["nombre_usuario"]})


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
    """Actualizar nombre y/o contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    nombre = datos.get("nombre", "").strip()
    password = datos.get("password", "").strip()

    db = get_db()
    usuario = db.execute(
        "SELECT nombre_usuario FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Actualizar nombre si se proporciona
    if nombre:
        if len(nombre) > 80:
            return APIResponse.validacion("El nombre no puede exceder 80 caracteres")
        db.execute(
            "UPDATE usuarios SET nombre_usuario = ? WHERE id = ?",
            (nombre, usuario_id)
        )
        session["usuario"] = nombre

    # Actualizar contraseña si se proporciona
    if password:
        if len(password) < 4:
            return APIResponse.validacion("La contraseña debe tener mínimo 4 caracteres")
        nuevo_hash = generate_password_hash(password)
        db.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (nuevo_hash, usuario_id)
        )

    db.commit()
    return APIResponse.success({"usuario": session.get("usuario")})


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
    if len(password_nueva) < 4:
        return APIResponse.validacion("La nueva contraseña debe tener al menos 4 caracteres")

    if password_nueva != password_confirmacion:
        return APIResponse.validacion("Las contraseñas no coinciden")

    db = get_db()
    usuario = db.execute(
        "SELECT password_hash FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Verificar contraseña actual
    if not check_password_hash(usuario["password_hash"], password_actual):
        return APIResponse.error("La contraseña actual es incorrecta", 400)

    # Actualizar contraseña
    nuevo_hash = generate_password_hash(password_nueva)
    db.execute(
        "UPDATE usuarios SET password_hash = ? WHERE id = ?",
        (nuevo_hash, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Contraseña cambiada correctamente"})


@bp.route("/api/usuarios", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_usuarios():
    db = get_db()
    filas = db.execute(
        "SELECT id, nombre_usuario, fecha_creacion FROM usuarios ORDER BY fecha_creacion"
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])


@bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_usuario(usuario_id):
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    if total <= 1:
        return APIResponse.error("No puedes borrar el único usuario que queda", 400)

    db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    db.commit()
    if session.get("usuario_id") == usuario_id:
        session.clear()
    return APIResponse.success()
