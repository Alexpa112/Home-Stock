"""Rutas para gestionar hogares de compra (modelo Bring!)."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..utils import Validator, DataConverter

bp = Blueprint("hogares", __name__, url_prefix="/api/hogares")


def _usuario_tiene_permiso(db, hogar_id, usuario_id, nivel_requerido=None):
    """Verifica si usuario tiene acceso a lista. Retorna: 'propietario'|'editar'|'ver'|None"""
    lista = db.execute("SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)).fetchone()
    if not lista:
        return None

    if lista["usuario_propietario_id"] == usuario_id:
        return "propietario"

    permiso = db.execute(
        "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
        (hogar_id, usuario_id),
    ).fetchone()

    if permiso:
        nivel = permiso["nivel"]
        if nivel_requerido and nivel_requerido != "ver" and nivel == "ver":
            return None
        return nivel

    return None


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_listas():
    """Lista hogares del usuario: propias + compartidas."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    propias = db.execute(
        """SELECT l.*, u.nombre_usuario AS actualizado_por_nombre FROM hogares l
           LEFT JOIN usuarios u ON u.id = l.actualizado_por_usuario_id
           WHERE l.usuario_propietario_id = ? ORDER BY l.fecha_actualizacion DESC""",
        (usuario_id,),
    ).fetchall()

    compartidas = db.execute(
        """SELECT l.*, pl.nivel, u.nombre_usuario AS actualizado_por_nombre FROM hogares l
           JOIN permisos_hogar pl ON l.id = pl.hogar_id
           LEFT JOIN usuarios u ON u.id = l.actualizado_por_usuario_id
           WHERE pl.usuario_id = ? AND l.usuario_propietario_id != ?
           ORDER BY l.fecha_actualizacion DESC""",
        (usuario_id, usuario_id),
    ).fetchall()

    return APIResponse.success({
        "propias": [DataConverter.lista_to_dict(l, usuario_id, include_detalles=True) for l in propias],
        "compartidas": [DataConverter.lista_to_dict(l, usuario_id, include_detalles=True) for l in compartidas],
        "hogar_actual_id": session.get("hogar_actual_id"),
    })


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_lista():
    """Crea una nueva lista (privada por defecto)."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 100)
    descripcion = Validator.string_opcional(datos.get("descripcion"), None, 500)
    icono = Validator.string_opcional(datos.get("icono"), "h-clipboard-document-list", 30)
    color = Validator.color_hex(datos.get("color"), "#B5551A")
    simbolo_moneda = Validator.string_opcional(datos.get("simbolo_moneda"), "€", 5)
    privada = datos.get("privada", True)

    db = get_db()
    cur = db.execute(
        """INSERT INTO hogares
           (nombre, descripcion, usuario_propietario_id, privada, icono, color, simbolo_moneda, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nombre, descripcion, usuario_id, int(privada), icono, color, simbolo_moneda, ahora(), ahora()),
    )
    nueva_lista_id = cur.lastrowid

    # Cada lista nace sin stock: el usuario añade sus propios productos
    # (antes se poblaba con TODOS los productos de TODAS las hogares/usuarios,
    # lo que hacía que el stock pareciera compartido globalmente).
    db.commit()

    # La lista recién creada pasa a ser la lista activa del usuario
    session["hogar_actual_id"] = nueva_lista_id
    session.modified = True

    lista = db.execute("SELECT * FROM hogares WHERE id = ?", (nueva_lista_id,)).fetchone()
    return APIResponse.success(DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True), 201)


@bp.route("/<int:hogar_id>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_lista(hogar_id):
    """Obtiene detalles de una lista (requiere acceso)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute(
        """SELECT l.*, u.nombre_usuario AS actualizado_por_nombre FROM hogares l
           LEFT JOIN usuarios u ON u.id = l.actualizado_por_usuario_id
           WHERE l.id = ?""",
        (hogar_id,),
    ).fetchone()

    if not lista:
        return APIResponse.no_encontrado("recurso_hogar")

    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    data = DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True)
    count = db.execute("SELECT COUNT(*) as total FROM articulos_compra WHERE hogar_id = ?", (hogar_id,)).fetchone()
    data["total_articulos"] = count["total"]
    return APIResponse.success(data)


@bp.route("/<int:hogar_id>", methods=["PUT", "PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_lista(hogar_id):
    """Actualiza una lista (solo el propietario)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM hogares WHERE id = ?", (hogar_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("recurso_hogar")

    if lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    actualizaciones = {}
    parametros = []

    if "nombre" in datos:
        nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 100)
        actualizaciones["nombre"] = "?"
        parametros.append(nombre)

    if "descripcion" in datos:
        descripcion = Validator.string_opcional(datos.get("descripcion"), None, 500)
        actualizaciones["descripcion"] = "?"
        parametros.append(descripcion)

    if "icono" in datos:
        icono = Validator.string_opcional(datos.get("icono"), "h-clipboard-document-list", 30)
        actualizaciones["icono"] = "?"
        parametros.append(icono)

    if "color" in datos:
        color = Validator.color_hex(datos.get("color"), "#B5551A")
        actualizaciones["color"] = "?"
        parametros.append(color)

    if "simbolo_moneda" in datos:
        simbolo_moneda = Validator.string_opcional(datos.get("simbolo_moneda"), "€", 5)
        actualizaciones["simbolo_moneda"] = "?"
        parametros.append(simbolo_moneda)

    if "privada" in datos:
        actualizaciones["privada"] = "?"
        parametros.append(int(datos.get("privada", True)))

    if not actualizaciones:
        return APIResponse.error("err_nada_que_actualizar", 400)

    # Solo nombre/icono/color son visibles para el resto de miembros como
    # "estilo" del hogar; registrar el autor para poder avisarles sin
    # atribuir a nadie un cambio que no sea de apariencia (ej. privada).
    if {"nombre", "icono", "color"} & actualizaciones.keys():
        actualizaciones["actualizado_por_usuario_id"] = "?"
        parametros.append(usuario_id)

    actualizaciones["fecha_actualizacion"] = "?"
    parametros.append(ahora())
    parametros.append(hogar_id)

    campos = ", ".join(f"{k} = {v}" for k, v in actualizaciones.items())
    db.execute(f"UPDATE hogares SET {campos} WHERE id = ?", parametros)
    db.commit()

    lista = db.execute(
        """SELECT l.*, u.nombre_usuario AS actualizado_por_nombre FROM hogares l
           LEFT JOIN usuarios u ON u.id = l.actualizado_por_usuario_id
           WHERE l.id = ?""",
        (hogar_id,),
    ).fetchone()
    return APIResponse.success(DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True))


@bp.route("/<int:hogar_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_lista(hogar_id):
    """Elimina una lista (solo el propietario, cascade de artículos)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM hogares WHERE id = ?", (hogar_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("recurso_hogar")

    if lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    db.execute("DELETE FROM hogares WHERE id = ?", (hogar_id,))
    db.commit()

    # Si era la lista activa, limpiarla de sesion (mismo motivo que en
    # salir_lista): si no, el usuario se queda "viendo" una lista que ya
    # no existe hasta que seleccione otra a mano.
    if session.get("hogar_actual_id") == hogar_id:
        session.pop("hogar_actual_id", None)
        session.modified = True

    return APIResponse.success()


@bp.route("/<int:hogar_id>/seleccionar", methods=["POST"])
@requerir_sesion
@manejo_errores
def seleccionar_lista(hogar_id):
    """Selecciona una lista como la actual del usuario."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM hogares WHERE id = ?", (hogar_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("recurso_hogar")

    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    session["hogar_actual_id"] = hogar_id
    session.modified = True
    return APIResponse.success({"exito": True, "hogar_id": hogar_id})


@bp.route("/<int:hogar_id>/salir", methods=["POST"])
@requerir_sesion
@manejo_errores
def salir_lista(hogar_id):
    """Sale de una lista compartida (solo para hogares compartidas)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM hogares WHERE id = ?", (hogar_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("recurso_hogar")

    if lista["usuario_propietario_id"] == usuario_id:
        return APIResponse.error("err_no_salir_propio_hogar", 403)

    db.execute(
        "DELETE FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
        (hogar_id, usuario_id),
    )
    db.commit()

    # Si era la lista activa, limpiarla de sesion: sin esto, el usuario
    # seguiria "viendo" (intentando usar) una lista de la que acaba de salir
    # hasta que seleccione otra a mano.
    if session.get("hogar_actual_id") == hogar_id:
        session.pop("hogar_actual_id", None)
        session.modified = True

    return APIResponse.success()


@bp.route("/version", methods=["GET"])
@requerir_sesion
@manejo_errores
def version_hogar_actual():
    """Marca de versión barata del hogar activo: un cambio en cualquiera de
    sus tablas (stock, lista de la compra, productos) hace que este valor
    cambie. Pensado para que el cliente haga polling contra esto antes de
    recargar los datos completos, y así no pisar ediciones en curso ni gastar
    ancho de banda cuando nadie ha tocado nada."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    hogar_id = session.get("hogar_actual_id")

    if not hogar_id:
        return APIResponse.success({"hogar_id": None, "version": None})

    if not _usuario_tiene_permiso(db, hogar_id, usuario_id):
        return APIResponse.no_permitido()

    fila = db.execute(
        """SELECT
               (SELECT COUNT(*) FROM stock_hogar WHERE hogar_id = ?) AS n_stock,
               (SELECT MAX(fecha_actualizacion) FROM stock_hogar WHERE hogar_id = ?) AS max_stock,
               (SELECT COUNT(*) FROM articulos_compra WHERE hogar_id = ?) AS n_articulos,
               (SELECT MAX(fecha_actualizacion) FROM articulos_compra WHERE hogar_id = ?) AS max_articulos
        """,
        (hogar_id, hogar_id, hogar_id, hogar_id),
    ).fetchone()

    version = "|".join(str(v) for v in (
        fila["n_stock"], fila["max_stock"], fila["n_articulos"], fila["max_articulos"],
    ))
    return APIResponse.success({"hogar_id": hogar_id, "version": version})


@bp.route("/<int:hogar_id>/miembros-basico", methods=["GET"])
@requerir_sesion
@manejo_errores
def miembros_basico(hogar_id):
    """Lista básica (id + nombre) de los miembros del hogar, accesible a
    cualquiera con acceso (a diferencia de /miembros en rutas/permisos.py,
    que reserva la gestión de permisos al propietario). Pensado para
    selectores de participantes en funcionalidades como gastos compartidos."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    if not _usuario_tiene_permiso(db, hogar_id, usuario_id):
        return APIResponse.no_permitido()

    filas = db.execute(
        "SELECT id, COALESCE(nombre, nombre_usuario) AS nombre_usuario FROM usuarios "
        "WHERE id = (SELECT usuario_propietario_id FROM hogares WHERE id = ?) "
        "OR id IN (SELECT usuario_id FROM permisos_hogar WHERE hogar_id = ?)",
        (hogar_id, hogar_id),
    ).fetchall()
    return APIResponse.success([{"id": f["id"], "nombre_usuario": f["nombre_usuario"]} for f in filas])


# Nota: compartir/miembros/permisos de lista se gestionan en rutas/permisos.py
# (incluye compartir por usuario, por email con invitación, y aceptar invitación).
