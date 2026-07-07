"""Alta del primer usuario, login, logout y gestion de usuarios."""
from flask import Blueprint, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import ahora, get_db

bp = Blueprint("auth", __name__)

# Endpoints accesibles sin haber iniciado sesion (usados por el guardian
# global en __init__.py).
RUTAS_PUBLICAS = {
    "auth.pagina_login",
    "auth.estado",
    "auth.login",
    "auth.registrar",
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
def estado():
    db = get_db()
    return jsonify({"necesita_setup": not hay_usuarios(db), "usuario": usuario_actual()})


@bp.route("/api/auth/registrar", methods=["POST"])
def registrar():
    db = get_db()
    datos = request.get_json(force=True) or {}
    nombre_usuario = (datos.get("usuario") or "").strip()
    password = datos.get("password") or ""

    # Solo el primer usuario puede auto-registrarse (alta inicial). Para
    # añadir mas gente despues hace falta haber iniciado sesion.
    if hay_usuarios(db) and not usuario_actual():
        return jsonify({"error": "Inicia sesión para añadir más usuarios"}), 401

    if not nombre_usuario or len(password) < 4:
        return jsonify(
            {"error": "El usuario es obligatorio y la contraseña debe tener al menos 4 caracteres"}
        ), 400

    existente = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if existente:
        return jsonify({"error": "Ya existe un usuario con ese nombre"}), 400

    db.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion) VALUES (?, ?, ?)",
        (nombre_usuario, generate_password_hash(password), ahora()),
    )
    db.commit()
    return jsonify({"creado": True}), 201


@bp.route("/api/auth/login", methods=["POST"])
def login():
    datos = request.get_json(force=True) or {}
    nombre_usuario = (datos.get("usuario") or "").strip()
    password = datos.get("password") or ""

    db = get_db()
    fila = db.execute(
        "SELECT * FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()
    if fila is None or not check_password_hash(fila["password_hash"], password):
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    session.permanent = True
    session["usuario"] = fila["nombre_usuario"]
    session["usuario_id"] = fila["id"]
    return jsonify({"usuario": fila["nombre_usuario"]})


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return "", 204


@bp.route("/api/usuarios", methods=["GET"])
def listar_usuarios():
    db = get_db()
    filas = db.execute(
        "SELECT id, nombre_usuario, fecha_creacion FROM usuarios ORDER BY fecha_creacion"
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
def borrar_usuario(usuario_id):
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    if total <= 1:
        return jsonify({"error": "No puedes borrar el único usuario que queda"}), 400

    db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    db.commit()
    if session.get("usuario_id") == usuario_id:
        session.clear()
    return "", 204
