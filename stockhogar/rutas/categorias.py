"""Rutas para gestionar categorías de productos (editables desde la app)."""
from flask import Blueprint, request, jsonify

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import CATEGORIA_DEFECTO
from ..db import get_db
from ..translator import traducir
from ..utils import Validator, DataConverter

bp = Blueprint("categorias", __name__, url_prefix="/api/categorias")


def normalizar_categoria(db, nombre):
    """Devuelve el nombre si existe como categoría, o el comodín por defecto."""
    fila = db.execute("SELECT nombre FROM categorias WHERE nombre = ?", (nombre,)).fetchone()
    return fila["nombre"] if fila else CATEGORIA_DEFECTO


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_categorias():
    db = get_db()
    filas = db.execute("SELECT * FROM categorias ORDER BY nombre COLLATE NOCASE").fetchall()
    return APIResponse.success([DataConverter.categoria_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_categoria():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 50)
    icono = Validator.string_opcional(datos.get("icono"), "h-folder", 30)

    db = get_db()
    existente = db.execute(
        "SELECT id FROM categorias WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()
    if existente:
        return APIResponse.error("err_categoria_duplicada", 400)

    cur = db.execute("INSERT INTO categorias (nombre, icono) VALUES (?, ?)", (nombre, icono))
    db.commit()
    fila = db.execute("SELECT * FROM categorias WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.categoria_to_dict(fila), 201)


@bp.route("/<int:categoria_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_categoria(categoria_id):
    db = get_db()
    fila = db.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
    if not fila:
        return APIResponse.no_encontrado("recurso_categoria")
    if fila["nombre"] == CATEGORIA_DEFECTO:
        mensaje = traducir("err_no_borrar_categoria_defecto").replace("{nombre}", CATEGORIA_DEFECTO)
        return jsonify({"error": mensaje}), 400

    en_uso = db.execute(
        "SELECT COUNT(*) AS n FROM productos WHERE categoria = ?", (fila["nombre"],)
    ).fetchone()["n"]
    if en_uso:
        return APIResponse.error(
            traducir("err_categoria_en_uso").replace("{en_uso}", str(en_uso)), 409
        )

    db.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
    db.commit()
    return APIResponse.success()
