"""Rutas de gestión de espacios: stocks independientes (casa, oficina, etc.)."""
import re

from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import PALETA_ESPACIOS
from ..db import ahora, get_db
from ..utils import Validator, DataConverter

bp = Blueprint("espacios", __name__, url_prefix="/api/espacios")

_HEX_VALIDO = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color_valido(color):
    color = (color or "").strip()
    return color if _HEX_VALIDO.match(color) else None


def obtener_espacio_actual(db):
    """Id del espacio activo para esta sesion, validando que siga existiendo."""
    try:
        espacio_id = session.get("espacio_id")
        if espacio_id is not None:
            existe = db.execute("SELECT 1 FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
            if existe:
                return espacio_id
    except (RuntimeError, KeyError):
        # RuntimeError: no request context; KeyError: session not available
        pass

    # Si no hay espacio en sesión o no existe, obtener el primero
    primero = db.execute("SELECT id FROM espacios ORDER BY id LIMIT 1").fetchone()
    espacio_id = primero["id"] if primero else 1

    try:
        session["espacio_id"] = espacio_id
    except (RuntimeError, KeyError):
        # No request context para guardar en sesión, solo devolver el id
        pass

    return espacio_id


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_espacios():
    db = get_db()
    filas = db.execute(
        "SELECT e.*, (SELECT COUNT(*) FROM productos p WHERE p.espacio_id = e.id) AS productos_count "
        "FROM espacios e ORDER BY e.nombre COLLATE NOCASE"
    ).fetchall()
    return APIResponse.success([DataConverter.espacio_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_espacio():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return APIResponse.validacion("El nombre es obligatorio")
    icono = (datos.get("icono") or "").strip() or "h-home"

    db = get_db()
    existente = db.execute(
        "SELECT id FROM espacios WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()
    if existente:
        return APIResponse.validacion("Ya tienes un stock con ese nombre")

    color = _color_valido(datos.get("color"))
    if not color:
        total = db.execute("SELECT COUNT(*) AS n FROM espacios").fetchone()["n"]
        color = PALETA_ESPACIOS[total % len(PALETA_ESPACIOS)]

    cur = db.execute(
        "INSERT INTO espacios (nombre, icono, color, fecha_creacion) VALUES (?, ?, ?, ?)",
        (nombre, icono, color, ahora()),
    )
    db.commit()
    fila = db.execute(
        "SELECT *, 0 AS productos_count FROM espacios WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return APIResponse.success(DataConverter.espacio_to_dict(fila), 201)


@bp.route("/<int:espacio_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_espacio(espacio_id):
    db = get_db()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
    if fila is None:
        return APIResponse.no_encontrado("Stock")

    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or fila["nombre"]).strip() or fila["nombre"]
    icono = (datos.get("icono") or fila["icono"]).strip() or fila["icono"]
    color = _color_valido(datos.get("color")) or fila["color"]
    db.execute(
        "UPDATE espacios SET nombre = ?, icono = ?, color = ? WHERE id = ?",
        (nombre, icono, color, espacio_id),
    )
    db.commit()
    fila = db.execute(
        "SELECT e.*, (SELECT COUNT(*) FROM productos p WHERE p.espacio_id = e.id) AS productos_count "
        "FROM espacios e WHERE e.id = ?",
        (espacio_id,),
    ).fetchone()
    return APIResponse.success(DataConverter.espacio_to_dict(fila))


@bp.route("/<int:espacio_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_espacio(espacio_id):
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM espacios").fetchone()["n"]
    if total <= 1:
        return APIResponse.validacion("No puedes borrar el único stock que tienes")

    db.execute("DELETE FROM lista_compra WHERE espacio_id = ?", (espacio_id,))
    db.execute("DELETE FROM productos WHERE espacio_id = ?", (espacio_id,))
    db.execute("DELETE FROM espacios WHERE id = ?", (espacio_id,))
    db.commit()

    if session.get("espacio_id") == espacio_id:
        session.pop("espacio_id", None)
    return APIResponse.success(None, 204)


@bp.route("/actual", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_actual():
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (espacio_id,)).fetchone()
    return APIResponse.success(DataConverter.espacio_to_dict(fila))


@bp.route("/actual", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_actual():
    datos = request.get_json(force=True) or {}
    db = get_db()
    fila = db.execute("SELECT * FROM espacios WHERE id = ?", (datos.get("espacio_id"),)).fetchone()
    if fila is None:
        return APIResponse.no_encontrado("Stock")
    session["espacio_id"] = fila["id"]
    return APIResponse.success(DataConverter.espacio_to_dict(fila))
