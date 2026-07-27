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
    "paginas.service_worker",
    "paginas.log_client_error",
    "paginas.csrf_token",
    "paginas.mantenimiento_stream",
    "idiomas.obtener_todas_traducciones",
    "static",
}


def hay_usuarios(db):
    return db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] > 0


def usuario_actual():
    return session.get("usuario")


@bp.route("/login")
def pagina_login():
    next_url = request.args.get("next", "")
    # Solo permitir rutas internas relativas para evitar open-redirect.
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = ""
    return render_template("login.html", modo_setup=not hay_usuarios(get_db()), next_url=next_url)


@bp.route("/api/auth/estado")
@manejo_errores
def estado():
    db = get_db()
    email = None
    tema_preferido = "auto"
    idioma_preferido = "es"
    teclado_virtual_activo = "on"
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = db.execute(
            "SELECT email, tema_preferido, idioma_preferido, teclado_virtual_activo FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        if fila:
            email = fila["email"]
            tema_preferido = fila["tema_preferido"]
            idioma_preferido = fila["idioma_preferido"]
            teclado_virtual_activo = fila["teclado_virtual_activo"]
    return APIResponse.success(
        {
            "necesita_setup": not hay_usuarios(db),
            "usuario": usuario_actual(),
            "email": email,
            "tema_preferido": tema_preferido,
            "idioma_preferido": idioma_preferido,
            "teclado_virtual_activo": teclado_virtual_activo,
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

    existente = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if existente:
        return APIResponse.error("err_usuario_duplicado", 400)

    db.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
        (nombre_usuario, generate_password_hash(password), ahora()),
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
            return APIResponse.validacion("err_nombre_max_80")
        duplicado = db.execute(
            "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE AND id != ?",
            (nombre, usuario_id)
        ).fetchone()
        if duplicado:
            return APIResponse.error("err_usuario_duplicado", 400)
        db.execute(
            "UPDATE usuarios SET nombre_usuario = ? WHERE id = ?",
            (nombre, usuario_id)
        )
        session["usuario"] = nombre

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
    return APIResponse.success({"usuario": session.get("usuario")})


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
                SELECT l.usuario_propietario_id FROM listas l
                WHERE l.id IN (
                    SELECT id FROM listas WHERE usuario_propietario_id = ?
                    UNION
                    SELECT lista_id FROM permisos_lista WHERE usuario_id = ?
                )
           )
           OR u.id IN (
                SELECT p.usuario_id FROM permisos_lista p
                WHERE p.lista_id IN (
                    SELECT id FROM listas WHERE usuario_propietario_id = ?
                    UNION
                    SELECT lista_id FROM permisos_lista WHERE usuario_id = ?
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
