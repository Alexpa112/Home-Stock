"""Rutas de la lista de la compra."""
from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("lista_compra", __name__, url_prefix="/api/lista-compra")


def compra_a_dict(row):
    return {
        "id": row["id"],
        "producto_id": row["producto_id"],
        "nombre": row["nombre"],
        "unidad": row["unidad"],
        "origen": row["origen"],
        "sincronizado_bring": bool(row["sincronizado_bring"]),
    }


@bp.route("", methods=["GET"])
def listar_lista_compra():
    db = get_db()
    filas = db.execute(
        "SELECT * FROM lista_compra ORDER BY origen, nombre COLLATE NOCASE"
    ).fetchall()
    return jsonify([compra_a_dict(f) for f in filas])


@bp.route("", methods=["POST"])
def anadir_lista_compra():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    unidad = (datos.get("unidad") or "ud").strip() or "ud"

    db = get_db()
    cur = db.execute(
        "INSERT INTO lista_compra (nombre, unidad, origen) VALUES (?, ?, 'manual')",
        (nombre, unidad),
    )
    db.commit()
    fila = db.execute("SELECT * FROM lista_compra WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(compra_a_dict(fila)), 201


@bp.route("/<int:item_id>", methods=["DELETE"])
def borrar_lista_compra(item_id):
    db = get_db()
    db.execute("DELETE FROM lista_compra WHERE id = ?", (item_id,))
    db.commit()
    return "", 204
