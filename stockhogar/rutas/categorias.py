"""Rutas para gestionar las categorias de productos (editables desde la app)."""
from flask import Blueprint, jsonify, request

from ..config import CATEGORIA_DEFECTO
from ..db import get_db

bp = Blueprint("categorias", __name__, url_prefix="/api/categorias")


def categoria_a_dict(row):
    return {"id": row["id"], "nombre": row["nombre"], "icono": row["icono"]}


def normalizar_categoria(db, nombre):
    """Devuelve el nombre si existe como categoria, o el comodin por defecto."""
    fila = db.execute(
        "SELECT nombre FROM categorias WHERE nombre = ?", (nombre,)
    ).fetchone()
    return fila["nombre"] if fila else CATEGORIA_DEFECTO


@bp.route("", methods=["GET"])
def listar_categorias():
    db = get_db()
    filas = db.execute("SELECT * FROM categorias ORDER BY nombre COLLATE NOCASE").fetchall()
    return jsonify([categoria_a_dict(f) for f in filas])


@bp.route("", methods=["POST"])
def crear_categoria():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    icono = (datos.get("icono") or "🗂️").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    db = get_db()
    existente = db.execute(
        "SELECT id FROM categorias WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()
    if existente:
        return jsonify({"error": "Ya existe una categoría con ese nombre"}), 400

    cur = db.execute(
        "INSERT INTO categorias (nombre, icono) VALUES (?, ?)", (nombre, icono)
    )
    db.commit()
    fila = db.execute("SELECT * FROM categorias WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(categoria_a_dict(fila)), 201


@bp.route("/<int:categoria_id>", methods=["DELETE"])
def borrar_categoria(categoria_id):
    db = get_db()
    fila = db.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
    if fila is None:
        return jsonify({"error": "Categoría no encontrada"}), 404
    if fila["nombre"] == CATEGORIA_DEFECTO:
        return jsonify({"error": f"No se puede borrar la categoría \"{CATEGORIA_DEFECTO}\""}), 400

    en_uso = db.execute(
        "SELECT COUNT(*) AS n FROM productos WHERE categoria = ?", (fila["nombre"],)
    ).fetchone()["n"]
    if en_uso:
        return jsonify({
            "error": f"Hay {en_uso} producto(s) usando esta categoría; cámbialos de categoría antes de borrarla."
        }), 409

    db.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
    db.commit()
    return "", 204
