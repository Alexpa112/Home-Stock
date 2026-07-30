"""
Historico/catalogo de articulos: nombre -> icono, categoria, unidad y
sub-descripcion habituales. Se siembra con un catalogo de productos de
supermercado (ver config.CATALOGO_DEFECTO) y se amplia solo con lo que el
usuario vaya creando, para poder sugerirlo automaticamente la proxima vez
que se escriba un nombre parecido (en un producto o en la lista de la
compra) y para poder navegarlo como catalogo al añadir a la lista.
"""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db

bp = Blueprint("historial", __name__, url_prefix="/api/historial")


def buscar_historial(db, nombre):
    """Busca un artículo en el catálogo (compartido por todas las hogares)."""
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
    """Aprende/actualiza un artículo en el catálogo compartido."""
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
        "FROM historial_articulos ORDER BY nombre COLLATE NOCASE",
    ).fetchall()
    return APIResponse.success([dict(fila) for fila in filas])


@bp.route("/catalogo", methods=["GET"])
@requerir_sesion
@manejo_errores
def buscar_catalogo():
    """Catálogo de artículos para autocompletar/grid al añadir a una lista:
    combina el historial estándar (compartido) con los artículos
    personalizados del hogar de la lista activa (aislados por
    usuario_propietario_id). Admite filtro opcional ?q=texto (LIKE)."""
    db = get_db()
    query = (request.args.get("q") or "").strip()
    like = f"%{query}%"

    if query:
        estandar = db.execute(
            "SELECT nombre, icono, categoria, unidad FROM historial_articulos "
            "WHERE nombre LIKE ? COLLATE NOCASE ORDER BY nombre COLLATE NOCASE LIMIT 30",
            (like,),
        ).fetchall()
    else:
        estandar = db.execute(
            "SELECT nombre, icono, categoria, unidad FROM historial_articulos "
            "ORDER BY nombre COLLATE NOCASE LIMIT 30",
        ).fetchall()

    from ..servicios.stock import hogar_actual_con_permiso

    personalizados = []
    hogar_id = hogar_actual_con_permiso(db, session)
    if hogar_id:
        propietario = db.execute(
            "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)
        ).fetchone()
        if propietario:
            if query:
                personalizados = db.execute(
                    "SELECT nombre, icono, categoria, unidad FROM articulos_personalizados "
                    "WHERE usuario_propietario_id = ? AND nombre LIKE ? COLLATE NOCASE "
                    "ORDER BY nombre COLLATE NOCASE LIMIT 30",
                    (propietario["usuario_propietario_id"], like),
                ).fetchall()
            else:
                personalizados = db.execute(
                    "SELECT nombre, icono, categoria, unidad FROM articulos_personalizados "
                    "WHERE usuario_propietario_id = ? ORDER BY nombre COLLATE NOCASE LIMIT 30",
                    (propietario["usuario_propietario_id"],),
                ).fetchall()

    resultado = (
        [{**dict(fila), "origen": "estandar"} for fila in estandar]
        + [{**dict(fila), "origen": "personalizado"} for fila in personalizados]
    )
    return APIResponse.success(resultado)
