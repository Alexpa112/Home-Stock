"""Rutas de gestion de espacios: stocks independientes (casa, oficina, etc.)."""
from flask import Blueprint, jsonify, request, session

from ..db import ahora, get_db

bp = Blueprint("espacios", __name__, url_prefix="/api/espacios")


def espacio_a_dict(row):
    return {"id": row["id"], "nombre": row["nombre"], "icono": row["icono"]}


def obtener_espacio_actual(db):
    """Id del espacio activo para esta sesion, validando que siga existiendo."""
    espacio_id = session.get("espacio_id")
    if espacio_id is not None:
        existe = db.execute("SELECT 1 FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
        if existe:
            return espacio_id

    primero = db.execute("SELECT id FROM espacios ORDER BY id LIMIT 1").fetchone()
    espacio_id = primero["id"] if primero else None
    session["espacio_id"] = espacio_id
    return espacio_id


@bp.route("", methods=["GET"])
def listar_espacios():
    db = get_db()
    filas = db.execute("SELECT * FROM espacios ORDER BY nombre COLLATE NOCASE").fetchall()
    return jsonify([espacio_a_dict(f) for f in filas])


@bp.route("", methods=["POST"])
def crear_espacio():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    icono = (datos.get("icono") or "").strip() or "🏠"

    db = get_db()
    existente = db.execute(
        "SELECT id FROM espacios WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()
    if existente:
        return jsonify({"error": "Ya tienes un stock con ese nombre"}), 400

    cur = db.execute(
        "INSERT INTO espacios (nombre, icono, fecha_creacion) VALUES (?, ?, ?)",
        (nombre, icono, ahora()),
    )
    db.commit()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(espacio_a_dict(fila)), 201


@bp.route("/<int:espacio_id>", methods=["PATCH"])
def actualizar_espacio(espacio_id):
    db = get_db()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
    if fila is None:
        return jsonify({"error": "No encontrado"}), 404

    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or fila["nombre"]).strip() or fila["nombre"]
    icono = (datos.get("icono") or fila["icono"]).strip() or fila["icono"]
    db.execute("UPDATE espacios SET nombre = ?, icono = ? WHERE id = ?", (nombre, icono, espacio_id))
    db.commit()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
    return jsonify(espacio_a_dict(fila))


@bp.route("/<int:espacio_id>", methods=["DELETE"])
def borrar_espacio(espacio_id):
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM espacios").fetchone()["n"]
    if total <= 1:
        return jsonify({"error": "No puedes borrar el único stock que tienes"}), 400

    db.execute("DELETE FROM lista_compra WHERE espacio_id = ?", (espacio_id,))
    db.execute("DELETE FROM productos WHERE espacio_id = ?", (espacio_id,))
    db.execute("DELETE FROM espacios WHERE id = ?", (espacio_id,))
    db.commit()

    if session.get("espacio_id") == espacio_id:
        session.pop("espacio_id", None)
    return "", 204


@bp.route("/actual", methods=["GET"])
def obtener_actual():
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
    return jsonify(espacio_a_dict(fila))


@bp.route("/actual", methods=["POST"])
def cambiar_actual():
    datos = request.get_json(force=True) or {}
    db = get_db()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (datos.get("espacio_id"),)).fetchone()
    if fila is None:
        return jsonify({"error": "Stock no encontrado"}), 404
    session["espacio_id"] = fila["id"]
    return jsonify(espacio_a_dict(fila))
