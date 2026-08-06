"""Recetas del hogar (P-06): lista de ingredientes reutilizable para anadir
de golpe a la lista de la compra los que falten."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..servicios.stock import hogar_actual_con_permiso
from ..utils import Validator, ValidationError
from .articulos_compra import anadir_o_sumar_articulo

bp = Blueprint("recetas", __name__, url_prefix="/api/recetas")

MAX_INGREDIENTES = 50


def _receta_a_dict(db, receta):
    ingredientes = db.execute(
        "SELECT id, nombre, cantidad, unidad FROM receta_ingredientes WHERE receta_id = ? ORDER BY id",
        (receta["id"],),
    ).fetchall()
    return {
        "id": receta["id"],
        "nombre": receta["nombre"],
        "icono": receta["icono"],
        "fecha_creacion": receta["fecha_creacion"],
        "ingredientes": [dict(i) for i in ingredientes],
    }


def _validar_ingredientes(ingredientes):
    if not isinstance(ingredientes, list) or not ingredientes:
        raise ValidationError("La receta debe tener al menos un ingrediente")
    if len(ingredientes) > MAX_INGREDIENTES:
        raise ValidationError(f"Como maximo {MAX_INGREDIENTES} ingredientes por receta")

    validados = []
    for ing in ingredientes:
        nombre = Validator.string_requerido(ing.get("nombre"), "nombre del ingrediente", 80)
        cantidad = Validator.entero_minimo(ing.get("cantidad") or 1, "cantidad")
        unidad = Validator.string_opcional(ing.get("unidad"), "ud", 20)
        validados.append((nombre, cantidad, unidad))
    return validados


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_recetas():
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    recetas = db.execute(
        "SELECT * FROM recetas WHERE hogar_id = ? ORDER BY LOWER(nombre)", (hogar_id,)
    ).fetchall()
    return APIResponse.success([_receta_a_dict(db, r) for r in recetas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_receta():
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 100)
    icono = Validator.string_opcional(datos.get("icono"), None, 30)
    ingredientes = _validar_ingredientes(datos.get("ingredientes"))

    cur = db.execute(
        "INSERT INTO recetas (hogar_id, nombre, icono, fecha_creacion) VALUES (?, ?, ?, ?) RETURNING id",
        (hogar_id, nombre, icono, ahora()),
    )
    receta_id = cur.fetchone()["id"]
    for nombre_ing, cantidad, unidad in ingredientes:
        db.execute(
            "INSERT INTO receta_ingredientes (receta_id, nombre, cantidad, unidad) VALUES (?, ?, ?, ?)",
            (receta_id, nombre_ing, cantidad, unidad),
        )
    db.commit()

    receta = db.execute("SELECT * FROM recetas WHERE id = ?", (receta_id,)).fetchone()
    return APIResponse.success(_receta_a_dict(db, receta), 201)


def _obtener_receta_con_permiso(db, receta_id, nivel_requerido=None):
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido=nivel_requerido)
    if not hogar_id:
        return None, APIResponse.no_permitido()
    receta = db.execute(
        "SELECT * FROM recetas WHERE id = ? AND hogar_id = ?", (receta_id, hogar_id)
    ).fetchone()
    if not receta:
        return None, APIResponse.no_encontrado("recurso_receta")
    return receta, None


@bp.route("/<int:receta_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_receta(receta_id):
    db = get_db()
    receta, error = _obtener_receta_con_permiso(db, receta_id, nivel_requerido="editar")
    if error:
        return error

    datos = request.get_json(force=True) or {}
    if "nombre" in datos:
        nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 100)
        db.execute("UPDATE recetas SET nombre = ? WHERE id = ?", (nombre, receta_id))
    if "icono" in datos:
        icono = Validator.string_opcional(datos.get("icono"), None, 30)
        db.execute("UPDATE recetas SET icono = ? WHERE id = ?", (icono, receta_id))
    if "ingredientes" in datos:
        ingredientes = _validar_ingredientes(datos.get("ingredientes"))
        db.execute("DELETE FROM receta_ingredientes WHERE receta_id = ?", (receta_id,))
        for nombre_ing, cantidad, unidad in ingredientes:
            db.execute(
                "INSERT INTO receta_ingredientes (receta_id, nombre, cantidad, unidad) VALUES (?, ?, ?, ?)",
                (receta_id, nombre_ing, cantidad, unidad),
            )
    db.commit()

    receta = db.execute("SELECT * FROM recetas WHERE id = ?", (receta_id,)).fetchone()
    return APIResponse.success(_receta_a_dict(db, receta))


@bp.route("/<int:receta_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_receta(receta_id):
    db = get_db()
    receta, error = _obtener_receta_con_permiso(db, receta_id, nivel_requerido="editar")
    if error:
        return error

    db.execute("DELETE FROM recetas WHERE id = ?", (receta_id,))
    db.commit()
    return APIResponse.success()


@bp.route("/<int:receta_id>/anadir-a-lista", methods=["POST"])
@requerir_sesion
@manejo_errores
def anadir_receta_a_lista(receta_id):
    """Añade todos los ingredientes de la receta a la lista de la compra
    activa (reutiliza la misma resolución de historial/artículo
    personalizado que anadir_articulo, ver articulos_compra.py)."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    receta = db.execute("SELECT * FROM recetas WHERE id = ? AND hogar_id = ?", (receta_id, hogar_id)).fetchone()
    if not receta:
        return APIResponse.no_encontrado("recurso_receta")

    ingredientes = db.execute(
        "SELECT nombre, cantidad, unidad FROM receta_ingredientes WHERE receta_id = ?", (receta_id,)
    ).fetchall()

    anadidos = [
        anadir_o_sumar_articulo(db, hogar_id, ing["nombre"], cantidad=ing["cantidad"], unidad=ing["unidad"])
        for ing in ingredientes
    ]
    return APIResponse.success({"anadidos": len(anadidos), "articulos": anadidos})
