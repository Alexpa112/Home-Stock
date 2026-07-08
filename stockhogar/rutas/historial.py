"""
Historico/catalogo de articulos: nombre -> icono, categoria, unidad y
sub-descripcion habituales. Se siembra con un catalogo de productos de
supermercado (ver config.CATALOGO_DEFECTO) y se amplia solo con lo que el
usuario vaya creando, para poder sugerirlo automaticamente la proxima vez
que se escriba un nombre parecido (en un producto o en la lista de la
compra) y para poder navegarlo como catalogo al añadir a la lista.
"""
from flask import Blueprint

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db

bp = Blueprint("historial", __name__, url_prefix="/api/historial")


def buscar_historial(db, nombre):
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    fila = db.execute(
        "SELECT icono, categoria, unidad, sub_descripcion, cantidad_defecto FROM historial_articulos "
        "WHERE nombre = ? COLLATE NOCASE",
        (nombre,),
    ).fetchone()
    return dict(fila) if fila else None


def recordar_articulo(
    db, nombre, icono, categoria=None, unidad=None, sub_descripcion=None, cantidad_defecto=None
):
    nombre = (nombre or "").strip()
    if not nombre or not icono:
        return
    db.execute(
        "INSERT INTO historial_articulos "
        "(nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
        "VALUES (?, ?, ?, COALESCE(?, 'ud'), ?, COALESCE(?, 1), ?) "
        "ON CONFLICT(nombre) DO UPDATE SET icono = excluded.icono, "
        "categoria = COALESCE(?, historial_articulos.categoria), "
        "unidad = COALESCE(?, historial_articulos.unidad), "
        "sub_descripcion = COALESCE(?, historial_articulos.sub_descripcion), "
        "cantidad_defecto = COALESCE(?, historial_articulos.cantidad_defecto), "
        "fecha_actualizacion = excluded.fecha_actualizacion",
        (
            nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, ahora(),
            categoria, unidad, sub_descripcion, cantidad_defecto,
        ),
    )


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_historial():
    db = get_db()
    filas = db.execute(
        "SELECT nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto "
        "FROM historial_articulos ORDER BY nombre COLLATE NOCASE"
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])
