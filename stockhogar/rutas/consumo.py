"""Auditoria de movimientos de stock y resumen de consumo por periodo."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import get_db
from ..servicios.stock import lista_actual_con_permiso

bp = Blueprint("consumo", __name__, url_prefix="/api/consumo")

DIAS_POR_DEFECTO = 30
DIAS_MAXIMO = 365


def _dias_solicitados():
    try:
        dias = int(request.args.get("dias", DIAS_POR_DEFECTO))
    except (TypeError, ValueError):
        dias = DIAS_POR_DEFECTO
    return max(1, min(dias, DIAS_MAXIMO))


@bp.route("/producto/<int:producto_id>", methods=["GET"])
@requerir_sesion
@manejo_errores
def movimientos_producto(producto_id):
    """Historial de movimientos de un producto (auditoría) en la lista activa."""
    db = get_db()
    lista_id = lista_actual_con_permiso(db, session)
    if not lista_id:
        return APIResponse.success([])

    filas = db.execute(
        """SELECT m.id, m.delta, m.cantidad_resultante, m.origen, m.fecha, u.nombre_usuario
           FROM movimientos_stock m
           LEFT JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.producto_id = ? AND m.lista_id = ?
           ORDER BY m.fecha DESC
           LIMIT 100""",
        (producto_id, lista_id),
    ).fetchall()

    return APIResponse.success([
        {
            "id": f["id"],
            "delta": f["delta"],
            "cantidad_resultante": f["cantidad_resultante"],
            "origen": f["origen"],
            "fecha": f["fecha"],
            "usuario": f["nombre_usuario"],
        }
        for f in filas
    ])


@bp.route("/resumen", methods=["GET"])
@requerir_sesion
@manejo_errores
def resumen_consumo():
    """Consumo agregado por día de la lista activa, para el gráfico.

    Consumo = suma de los deltas negativos (bajadas de stock) por día;
    las subidas (compras/reposición) no cuentan como consumo.
    """
    db = get_db()
    lista_id = lista_actual_con_permiso(db, session)
    if not lista_id:
        return APIResponse.success({"dias": [], "por_producto": []})

    dias = _dias_solicitados()
    # Modificador de datetime() como bind variable, no interpolado en el SQL:
    # aunque _dias_solicitados() ya fuerza int() y clampa a [1, 365] (no
    # explotable hoy), construir la query con f-string va contra la
    # convencion de bind variables del proyecto y seria inyeccion inmediata
    # si esa funcion cambiara en el futuro para aceptar el valor sin sanear.
    desde = f"-{dias} days"

    por_dia = db.execute(
        """SELECT substr(m.fecha, 1, 10) AS dia, SUM(-m.delta) AS consumo
            FROM movimientos_stock m
            WHERE m.lista_id = ? AND m.delta < 0
              AND m.fecha >= datetime('now', ?)
            GROUP BY dia
            ORDER BY dia ASC""",
        (lista_id, desde),
    ).fetchall()

    por_producto = db.execute(
        """SELECT p.nombre, p.icono, SUM(-m.delta) AS consumo
            FROM movimientos_stock m
            JOIN productos p ON p.id = m.producto_id
            WHERE m.lista_id = ? AND m.delta < 0
              AND m.fecha >= datetime('now', ?)
            GROUP BY m.producto_id
            ORDER BY consumo DESC
            LIMIT 10""",
        (lista_id, desde),
    ).fetchall()

    return APIResponse.success({
        "dias": [{"dia": f["dia"], "consumo": f["consumo"]} for f in por_dia],
        "por_producto": [
            {"nombre": f["nombre"], "icono": f["icono"], "consumo": f["consumo"]} for f in por_producto
        ],
    })
