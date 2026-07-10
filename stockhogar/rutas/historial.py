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


def buscar_historial(db, nombre, espacio_id):
    """Busca primero lo aprendido en este espacio y, si no hay nada, cae al catálogo global."""
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    fila = db.execute(
        "SELECT icono, categoria, unidad, sub_descripcion, cantidad_defecto FROM historial_articulos "
        "WHERE nombre = ? COLLATE NOCASE AND (espacio_id = ? OR espacio_id IS NULL) "
        "ORDER BY espacio_id IS NULL ASC LIMIT 1",
        (nombre, espacio_id),
    ).fetchone()
    return dict(fila) if fila else None


def recordar_articulo(
    db, espacio_id, nombre, icono, categoria=None, unidad=None, sub_descripcion=None, cantidad_defecto=None
):
    """Aprende/actualiza un artículo en el historial de ESTE espacio (nunca en el global)."""
    nombre = (nombre or "").strip()
    if not nombre or not icono or not espacio_id:
        return
    db.execute(
        "INSERT INTO historial_articulos "
        "(espacio_id, nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, COALESCE(?, 'ud'), ?, COALESCE(?, 1), ?) "
        "ON CONFLICT(espacio_id, nombre) WHERE espacio_id IS NOT NULL DO UPDATE SET icono = excluded.icono, "
        "categoria = COALESCE(?, historial_articulos.categoria), "
        "unidad = COALESCE(?, historial_articulos.unidad), "
        "sub_descripcion = COALESCE(?, historial_articulos.sub_descripcion), "
        "cantidad_defecto = COALESCE(?, historial_articulos.cantidad_defecto), "
        "fecha_actualizacion = excluded.fecha_actualizacion",
        (
            espacio_id, nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, ahora(),
            categoria, unidad, sub_descripcion, cantidad_defecto,
        ),
    )


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_historial():
    from .espacios import obtener_espacio_actual

    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    filas = db.execute(
        "SELECT nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, espacio_id "
        "FROM historial_articulos WHERE espacio_id = ? OR espacio_id IS NULL "
        "ORDER BY nombre COLLATE NOCASE, espacio_id IS NULL ASC",
        (espacio_id,),
    ).fetchall()

    # Puede haber una fila global y otra propia del espacio con el mismo nombre; nos
    # quedamos con la primera de cada nombre (la propia del espacio, por el ORDER BY).
    vistos = set()
    resultado = []
    for fila in filas:
        clave = fila["nombre"].lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        d = dict(fila)
        d.pop("espacio_id", None)
        resultado.append(d)
    return APIResponse.success(resultado)
