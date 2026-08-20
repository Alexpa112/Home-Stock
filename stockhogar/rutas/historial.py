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
        "SELECT icono, categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso FROM historial_articulos "
        "WHERE LOWER(nombre) = LOWER(?)",
        (nombre,),
    ).fetchone()
    return dict(fila) if fila else None


def buscar_historial_por_codigo(db, codigo_barras):
    """Busca en el catálogo un artículo ya asociado a un código de barras/EAN (P-03)."""
    codigo_barras = (codigo_barras or "").strip()
    if not codigo_barras:
        return None
    fila = db.execute(
        "SELECT nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso "
        "FROM historial_articulos WHERE codigo_barras = ?",
        (codigo_barras,),
    ).fetchone()
    return dict(fila) if fila else None


def recordar_articulo(
    db, nombre, icono, categoria=None, unidad=None, sub_descripcion=None, cantidad_defecto=None, dias_aviso=None,
    codigo_barras=None,
):
    """Aprende/actualiza un artículo en el catálogo compartido."""
    nombre = (nombre or "").strip()
    if not nombre or not icono:
        return
    db.execute(
        "INSERT INTO historial_articulos "
        "(nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso, codigo_barras, fecha_actualizacion) "
        "VALUES (?, ?, ?, COALESCE(?, 'ud'), ?, COALESCE(?, 1), COALESCE(?, 30), ?, ?) "
        "ON CONFLICT(nombre) DO UPDATE SET icono = excluded.icono, "
        "categoria = COALESCE(?, historial_articulos.categoria), "
        "unidad = COALESCE(?, historial_articulos.unidad), "
        "sub_descripcion = COALESCE(?, historial_articulos.sub_descripcion), "
        "cantidad_defecto = COALESCE(?, historial_articulos.cantidad_defecto), "
        "dias_aviso = COALESCE(?, historial_articulos.dias_aviso), "
        "codigo_barras = COALESCE(?, historial_articulos.codigo_barras), "
        "fecha_actualizacion = excluded.fecha_actualizacion",
        (
            nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso, codigo_barras, ahora(),
            categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso, codigo_barras,
        ),
    )


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_historial():
    db = get_db()
    filas = db.execute(
        "SELECT nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, dias_aviso "
        "FROM historial_articulos ORDER BY LOWER(nombre)",
    ).fetchall()
    return APIResponse.success([dict(fila) for fila in filas])


@bp.route("/codigo/<codigo_barras>", methods=["GET"])
@requerir_sesion
@manejo_errores
def buscar_por_codigo(codigo_barras):
    """Busca un artículo del catálogo por su código de barras/EAN escaneado (P-03)."""
    db = get_db()
    encontrado = buscar_historial_por_codigo(db, codigo_barras)
    if not encontrado:
        return APIResponse.error("err_codigo_no_reconocido", status_code=404)
    return APIResponse.success(encontrado)


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
            "WHERE LOWER(nombre) LIKE LOWER(?) ORDER BY LOWER(nombre) LIMIT 30",
            (like,),
        ).fetchall()
    else:
        estandar = db.execute(
            "SELECT nombre, icono, categoria, unidad FROM historial_articulos "
            "ORDER BY LOWER(nombre) LIMIT 30",
        ).fetchall()

    from ..servicios.stock import hogar_actual_con_permiso

    personalizados = []
    hogar_id = hogar_actual_con_permiso(db, session)
    if hogar_id:
        # Los articulos visibles son los de TODOS los miembros del hogar: el
        # propietario (que no tiene por que tener fila en permisos_hogar, ahi
        # esta implicito) mas los invitados con permiso. Filtrar solo por
        # permisos_hogar dejaba al propietario sin ver su propio catalogo.
        #
        # La subconsulta va escrita entera en cada literal, sin interpolar: un
        # f-string aqui no metia ningun valor del usuario (todo va por bind
        # params) pero bandit lo marca como B608 y la puerta security-python
        # de CI falla con cualquier hallazgo de severidad media.
        if query:
            personalizados = db.execute(
                "SELECT DISTINCT nombre, icono, categoria, unidad FROM articulos_personalizados ap "
                "WHERE ap.usuario_propietario_id IN ("
                "    SELECT usuario_propietario_id FROM hogares WHERE id = ? "
                "    UNION SELECT usuario_id FROM permisos_hogar WHERE hogar_id = ?) "
                "AND LOWER(ap.nombre) LIKE LOWER(?) "
                "ORDER BY LOWER(ap.nombre) LIMIT 30",
                (hogar_id, hogar_id, like),
            ).fetchall()
        else:
            personalizados = db.execute(
                "SELECT DISTINCT nombre, icono, categoria, unidad FROM articulos_personalizados ap "
                "WHERE ap.usuario_propietario_id IN ("
                "    SELECT usuario_propietario_id FROM hogares WHERE id = ? "
                "    UNION SELECT usuario_id FROM permisos_hogar WHERE hogar_id = ?) "
                "ORDER BY LOWER(ap.nombre) LIMIT 30",
                (hogar_id, hogar_id),
            ).fetchall()

    resultado = (
        [{**dict(fila), "origen": "estandar"} for fila in estandar]
        + [{**dict(fila), "origen": "personalizado"} for fila in personalizados]
    )
    return APIResponse.success(resultado)
