"""Rutas para gestionar categorías de gasto (editables desde la app),
catálogo independiente del de categorías de producto (ver rutas/categorias.py)."""
from flask import Blueprint, request, jsonify

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import CATEGORIA_GASTO_DEFECTO
from ..db import get_db
from ..translator import traducir
from ..utils import Validator, DataConverter

bp = Blueprint("categorias_gasto", __name__, url_prefix="/api/categorias-gasto")


def normalizar_categoria_gasto(db, nombre):
    """A diferencia de normalizar_categoria (producto), la categoría de un
    gasto es opcional: si no viene informada se devuelve None (sin
    categoría) en vez de caer en el comodín "Otros"."""
    if not nombre:
        return None
    fila = db.execute("SELECT nombre FROM categorias_gasto WHERE nombre = ?", (nombre,)).fetchone()
    return fila["nombre"] if fila else CATEGORIA_GASTO_DEFECTO


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_categorias_gasto():
    db = get_db()
    filas = db.execute("SELECT * FROM categorias_gasto ORDER BY nombre COLLATE NOCASE").fetchall()
    return APIResponse.success([DataConverter.categoria_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_categoria_gasto():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 50)
    icono = Validator.string_opcional(datos.get("icono"), "h-folder", 30)

    db = get_db()
    existente = db.execute(
        "SELECT id FROM categorias_gasto WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()
    if existente:
        return APIResponse.error("err_categoria_duplicada", 400)

    cur = db.execute("INSERT INTO categorias_gasto (nombre, icono) VALUES (?, ?)", (nombre, icono))
    db.commit()
    fila = db.execute("SELECT * FROM categorias_gasto WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.categoria_to_dict(fila), 201)


@bp.route("/<int:categoria_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_categoria_gasto(categoria_id):
    db = get_db()
    fila = db.execute("SELECT * FROM categorias_gasto WHERE id = ?", (categoria_id,)).fetchone()
    if not fila:
        return APIResponse.no_encontrado("recurso_categoria")
    if fila["nombre"] == CATEGORIA_GASTO_DEFECTO:
        mensaje = traducir("err_no_borrar_categoria_defecto").replace("{nombre}", CATEGORIA_GASTO_DEFECTO)
        return jsonify({"error": mensaje}), 400

    en_uso = db.execute(
        "SELECT COUNT(*) AS n FROM gastos WHERE categoria = ?", (fila["nombre"],)
    ).fetchone()["n"]
    if en_uso:
        return APIResponse.error(
            traducir("err_categoria_gasto_en_uso").replace("{en_uso}", str(en_uso)), 409
        )

    db.execute("DELETE FROM categorias_gasto WHERE id = ?", (categoria_id,))
    db.commit()
    return APIResponse.success()
