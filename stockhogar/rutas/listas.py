"""Rutas para gestionar listas de compra (modelo Bring!)."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..utils import Validator, DataConverter

bp = Blueprint("listas", __name__, url_prefix="/api/listas")


def _usuario_tiene_permiso(db, lista_id, usuario_id, nivel_requerido=None):
    """Verifica si usuario tiene acceso a lista. Retorna: 'propietario'|'editar'|'ver'|None"""
    lista = db.execute("SELECT usuario_propietario_id FROM listas WHERE id = ?", (lista_id,)).fetchone()
    if not lista:
        return None

    if lista["usuario_propietario_id"] == usuario_id:
        return "propietario"

    permiso = db.execute(
        "SELECT nivel FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
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
    """Lista listas del usuario: propias + compartidas."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    propias = db.execute(
        "SELECT * FROM listas WHERE usuario_propietario_id = ? ORDER BY fecha_actualizacion DESC",
        (usuario_id,),
    ).fetchall()

    compartidas = db.execute(
        """SELECT l.*, pl.nivel FROM listas l
           JOIN permisos_lista pl ON l.id = pl.lista_id
           WHERE pl.usuario_id = ? AND l.usuario_propietario_id != ?
           ORDER BY l.fecha_actualizacion DESC""",
        (usuario_id, usuario_id),
    ).fetchall()

    return APIResponse.success({
        "propias": [DataConverter.lista_to_dict(l, usuario_id, include_detalles=True) for l in propias],
        "compartidas": [DataConverter.lista_to_dict(l, usuario_id, include_detalles=True) for l in compartidas],
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
    icono = Validator.string_opcional(datos.get("icono"), "📋", 10)
    color = Validator.string_opcional(datos.get("color"), "#B5551A", 7)
    privada = datos.get("privada", True)

    db = get_db()
    cur = db.execute(
        """INSERT INTO listas
           (nombre, descripcion, usuario_propietario_id, privada, icono, color, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (nombre, descripcion, usuario_id, int(privada), icono, color, ahora(), ahora()),
    )
    nueva_lista_id = cur.lastrowid

    # Cada lista nace sin stock: el usuario añade sus propios productos
    # (antes se poblaba con TODOS los productos de TODAS las listas/usuarios,
    # lo que hacía que el stock pareciera compartido globalmente).
    db.commit()

    # La lista recién creada pasa a ser la lista activa del usuario
    session["lista_actual_id"] = nueva_lista_id
    session.modified = True

    lista = db.execute("SELECT * FROM listas WHERE id = ?", (nueva_lista_id,)).fetchone()
    return APIResponse.success(DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True), 201)


@bp.route("/<int:lista_id>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_lista(lista_id):
    """Obtiene detalles de una lista (requiere acceso)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    data = DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True)
    count = db.execute("SELECT COUNT(*) as total FROM articulos_lista WHERE lista_id = ?", (lista_id,)).fetchone()
    data["total_articulos"] = count["total"]
    return APIResponse.success(data)


@bp.route("/<int:lista_id>", methods=["PUT", "PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_lista(lista_id):
    """Actualiza una lista (solo el propietario)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

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
        icono = Validator.string_opcional(datos.get("icono"), "📋", 10)
        actualizaciones["icono"] = "?"
        parametros.append(icono)

    if "color" in datos:
        color = Validator.string_opcional(datos.get("color"), "#B5551A", 7)
        actualizaciones["color"] = "?"
        parametros.append(color)

    if "privada" in datos:
        actualizaciones["privada"] = "?"
        parametros.append(int(datos.get("privada", True)))

    if not actualizaciones:
        return APIResponse.error("No hay nada que actualizar", 400)

    actualizaciones["fecha_actualizacion"] = "?"
    parametros.append(ahora())
    parametros.append(lista_id)

    campos = ", ".join(f"{k} = {v}" for k, v in actualizaciones.items())
    db.execute(f"UPDATE listas SET {campos} WHERE id = ?", parametros)
    db.commit()

    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()
    return APIResponse.success(DataConverter.lista_to_dict(lista, usuario_id, include_detalles=True))


@bp.route("/<int:lista_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_lista(lista_id):
    """Elimina una lista (solo el propietario, cascade de artículos)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    if lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    db.execute("DELETE FROM listas WHERE id = ?", (lista_id,))
    db.commit()
    return APIResponse.success()


@bp.route("/<int:lista_id>/seleccionar", methods=["POST"])
@requerir_sesion
@manejo_errores
def seleccionar_lista(lista_id):
    """Selecciona una lista como la actual del usuario."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    session["lista_actual_id"] = lista_id
    session.modified = True
    return APIResponse.success({"exito": True, "lista_id": lista_id})


@bp.route("/<int:lista_id>/salir", methods=["POST"])
@requerir_sesion
@manejo_errores
def salir_lista(lista_id):
    """Sale de una lista compartida (solo para listas compartidas)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    if lista["usuario_propietario_id"] == usuario_id:
        return APIResponse.error("No puedes salir de tu propia lista", 403)

    db.execute(
        "DELETE FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
    )
    db.commit()
    return APIResponse.success()


@bp.route("/<int:lista_id>/compartir", methods=["POST"])
@requerir_sesion
@manejo_errores
def compartir_lista(lista_id):
    """Comparte una lista con otro usuario (solo el propietario)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    if lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    nivel = (datos.get("nivel") or "ver").lower()

    if nivel not in ("ver", "editar"):
        return APIResponse.error("Nivel debe ser 'ver' o 'editar'", 400)

    usuario_destino = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()

    if not usuario_destino:
        return APIResponse.no_encontrado("Usuario")

    usuario_destino_id = usuario_destino["id"]

    if usuario_destino_id == usuario_id:
        return APIResponse.error("No puedes compartir la lista contigo mismo", 400)

    db.execute(
        """INSERT OR REPLACE INTO permisos_lista
           (lista_id, usuario_id, nivel, fecha_otorgado)
           VALUES (?, ?, ?, ?)""",
        (lista_id, usuario_destino_id, nivel, ahora()),
    )
    db.commit()

    return APIResponse.success({
        "mensaje": f"Lista compartida con {nombre_usuario}",
        "nivel": nivel,
        "usuario": nombre_usuario,
    }, 201)


@bp.route("/<int:lista_id>/permisos", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_permisos(lista_id):
    """Lista usuarios con acceso a la lista (solo el propietario)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    if lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    propietario = {
        "usuario_id": lista["usuario_propietario_id"],
        "nombre_usuario": db.execute(
            "SELECT nombre_usuario FROM usuarios WHERE id = ?", (lista["usuario_propietario_id"],)
        ).fetchone()["nombre_usuario"],
        "nivel": "propietario",
    }

    permisos = db.execute(
        """SELECT pl.usuario_id, u.nombre_usuario, pl.nivel, pl.fecha_otorgado
           FROM permisos_lista pl JOIN usuarios u ON pl.usuario_id = u.id
           WHERE pl.lista_id = ? ORDER BY u.nombre_usuario""",
        (lista_id,),
    ).fetchall()

    return APIResponse.success({
        "propietario": propietario,
        "compartida_con": [dict(p) for p in permisos],
    })


@bp.route("/<int:lista_id>/permisos/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def revocar_permiso(lista_id, usuario_id):
    """Revoca acceso a un usuario (solo propietario)."""
    propietario_id = session.get("usuario_id")
    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return APIResponse.no_encontrado("Lista")

    if lista["usuario_propietario_id"] != propietario_id:
        return APIResponse.no_permitido()

    if usuario_id == propietario_id:
        return APIResponse.error("El propietario no puede revocar su propio acceso", 400)

    db.execute(
        "DELETE FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
    )
    db.commit()
    return APIResponse.success()


@bp.route("/<int:lista_id>/permisos/<int:usuario_id>", methods=["PATCH"])
def cambiar_nivel_permiso(lista_id, usuario_id):
    """Cambia el nivel de permiso de un usuario (solo propietario)."""
    propietario_id = session.get("usuario_id")
    if not propietario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    if lista["usuario_propietario_id"] != propietario_id:
        return jsonify({"error": "Solo el propietario puede cambiar permisos"}), 403

    datos = request.get_json(force=True) or {}
    nivel = (datos.get("nivel") or "").lower()

    if nivel not in ("ver", "editar"):
        return jsonify({"error": "Nivel debe ser 'ver' o 'editar'"}), 400

    db.execute(
        "UPDATE permisos_lista SET nivel = ? WHERE lista_id = ? AND usuario_id = ?",
        (nivel, lista_id, usuario_id),
    )
    db.commit()

    return jsonify({"mensaje": "Permiso actualizado", "nivel": nivel}), 200
