"""Rutas para gestionar listas de compra (modelo Bring!)."""
from flask import Blueprint, jsonify, request, session

from ..db import ahora, get_db

bp = Blueprint("listas", __name__, url_prefix="/api/listas")


def _usuario_tiene_permiso(db, lista_id, usuario_id, nivel_requerido=None):
    """
    Verifica si un usuario tiene acceso a una lista.

    Retorna:
        - 'propietario' si es el propietario
        - 'editar' si tiene permiso de edición
        - 'ver' si tiene permiso de solo lectura
        - None si no tiene acceso
    """
    lista = db.execute("SELECT usuario_propietario_id FROM listas WHERE id = ?", (lista_id,)).fetchone()
    if not lista:
        return None

    # Propietario tiene acceso total
    if lista["usuario_propietario_id"] == usuario_id:
        return "propietario"

    # Verificar permisos explícitos
    permiso = db.execute(
        "SELECT nivel FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
    ).fetchone()

    if permiso:
        nivel = permiso["nivel"]
        # Validar nivel requerido si se especifica
        if nivel_requerido and nivel_requerido != "ver" and permiso["nivel"] == "ver":
            return None
        return nivel

    return None


def _lista_a_dict(row, usuario_id=None, include_detalles=False):
    """Convierte una fila de lista a dict JSON."""
    try:
        color = row["color"]
    except (KeyError, IndexError):
        color = "#B5551A"

    data = {
        "id": row["id"],
        "nombre": row["nombre"],
        "descripcion": row["descripcion"],
        "icono": row["icono"],
        "color": color,
        "privada": bool(row["privada"]),
        "usuario_propietario_id": row["usuario_propietario_id"],
        "fecha_creacion": row["fecha_creacion"],
        "fecha_actualizacion": row["fecha_actualizacion"],
    }

    if usuario_id and include_detalles:
        # Determinar el rol del usuario actual en esta lista
        if row["usuario_propietario_id"] == usuario_id:
            data["mi_rol"] = "propietario"
        else:
            permiso = row.get("nivel")
            data["mi_rol"] = permiso or "ninguno"

    return data


@bp.route("", methods=["GET"])
def listar_listas():
    """Lista las listas del usuario: propias + compartidas."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()

    # Listas propias
    propias = db.execute(
        "SELECT * FROM listas WHERE usuario_propietario_id = ? ORDER BY fecha_actualizacion DESC",
        (usuario_id,),
    ).fetchall()

    # Listas compartidas (con LEFT JOIN para obtener el nivel)
    compartidas = db.execute(
        """
        SELECT l.*, pl.nivel
        FROM listas l
        JOIN permisos_lista pl ON l.id = pl.lista_id
        WHERE pl.usuario_id = ? AND l.usuario_propietario_id != ?
        ORDER BY l.fecha_actualizacion DESC
        """,
        (usuario_id, usuario_id),
    ).fetchall()

    return jsonify({
        "propias": [_lista_a_dict(l, usuario_id, include_detalles=True) for l in propias],
        "compartidas": [_lista_a_dict(l, usuario_id, include_detalles=True) for l in compartidas],
    })


@bp.route("", methods=["POST"])
def crear_lista():
    """Crea una nueva lista (privada por defecto)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        return jsonify({"error": "El nombre de la lista es obligatorio"}), 400

    if len(nombre) > 100:
        return jsonify({"error": "El nombre no puede exceder 100 caracteres"}), 400

    db = get_db()
    descripcion = (datos.get("descripcion") or "").strip()[:500] or None
    icono = (datos.get("icono") or "📋").strip()[:10]
    color = (datos.get("color") or "#B5551A").strip()[:7]
    privada = datos.get("privada", True)

    cur = db.execute(
        """
        INSERT INTO listas
        (nombre, descripcion, usuario_propietario_id, privada, icono, color, fecha_creacion, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (nombre, descripcion, usuario_id, int(privada), icono, color, ahora(), ahora()),
    )
    db.commit()

    lista = db.execute("SELECT * FROM listas WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_lista_a_dict(lista, usuario_id, include_detalles=True)), 201


@bp.route("/<int:lista_id>", methods=["GET"])
def obtener_lista(lista_id):
    """Obtiene detalles de una lista (solo si tienes acceso)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    # Verificar permisos
    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id)
    if not permiso:
        return jsonify({"error": "No tienes acceso a esta lista"}), 403

    data = _lista_a_dict(lista, usuario_id, include_detalles=True)

    # Contar artículos
    count = db.execute(
        "SELECT COUNT(*) as total FROM articulos_lista WHERE lista_id = ?", (lista_id,)
    ).fetchone()
    data["total_articulos"] = count["total"]

    return jsonify(data)


@bp.route("/<int:lista_id>", methods=["PUT", "PATCH"])
def actualizar_lista(lista_id):
    """Actualiza una lista (solo el propietario)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    # Solo el propietario puede editar
    if lista["usuario_propietario_id"] != usuario_id:
        return jsonify({"error": "Solo el propietario puede editar la lista"}), 403

    datos = request.get_json(force=True) or {}

    nombre = datos.get("nombre")
    descripcion = datos.get("descripcion")
    icono = datos.get("icono")
    color = datos.get("color")
    privada = datos.get("privada")

    actualizaciones = {}
    parametros = []

    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            return jsonify({"error": "El nombre no puede estar vacío"}), 400
        if len(nombre) > 100:
            return jsonify({"error": "El nombre no puede exceder 100 caracteres"}), 400
        actualizaciones["nombre"] = "?"
        parametros.append(nombre)

    if descripcion is not None:
        descripcion = descripcion.strip()[:500] or None
        actualizaciones["descripcion"] = "?"
        parametros.append(descripcion)

    if icono is not None:
        icono = icono.strip()[:10]
        actualizaciones["icono"] = "?"
        parametros.append(icono)

    if color is not None:
        color = color.strip()[:7]
        actualizaciones["color"] = "?"
        parametros.append(color)

    if privada is not None:
        actualizaciones["privada"] = "?"
        parametros.append(int(privada))

    if not actualizaciones:
        return jsonify({"error": "No hay nada que actualizar"}), 400

    # Siempre actualizar fecha_actualizacion
    actualizaciones["fecha_actualizacion"] = "?"
    parametros.append(ahora())
    parametros.append(lista_id)

    campos = ", ".join(f"{k} = {v}" for k, v in actualizaciones.items())
    db.execute(f"UPDATE listas SET {campos} WHERE id = ?", parametros)
    db.commit()

    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()
    return jsonify(_lista_a_dict(lista, usuario_id, include_detalles=True))


@bp.route("/<int:lista_id>", methods=["DELETE"])
def eliminar_lista(lista_id):
    """Elimina una lista (solo el propietario, cascade de artículos)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    if lista["usuario_propietario_id"] != usuario_id:
        return jsonify({"error": "Solo el propietario puede eliminar la lista"}), 403

    # DELETE CASCADE se encarga de limpiar articulos_lista y permisos_lista
    db.execute("DELETE FROM listas WHERE id = ?", (lista_id,))
    db.commit()

    return "", 204


@bp.route("/<int:lista_id>/seleccionar", methods=["POST"])
def seleccionar_lista(lista_id):
    """Selecciona una lista como la actual del usuario."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    # Verificar que el usuario tiene acceso
    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id)
    if not permiso:
        return jsonify({"error": "No tienes acceso a esta lista"}), 403

    # Guardar la lista actual en sesión
    session["lista_actual_id"] = lista_id
    session.modified = True

    return jsonify({"exito": True, "lista_id": lista_id}), 200


@bp.route("/<int:lista_id>/salir", methods=["POST"])
def salir_lista(lista_id):
    """Sale de una lista compartida (solo para listas compartidas)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    # No se puede salir de lista propia
    if lista["usuario_propietario_id"] == usuario_id:
        return jsonify({"error": "No puedes salir de tu propia lista"}), 403

    # Eliminar el permiso
    db.execute(
        "DELETE FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
    )
    db.commit()

    return "", 204


@bp.route("/<int:lista_id>/compartir", methods=["POST"])
def compartir_lista(lista_id):
    """
    Comparte una lista con otro usuario.
    Solo el propietario puede hacerlo.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    if lista["usuario_propietario_id"] != usuario_id:
        return jsonify({"error": "Solo el propietario puede compartir"}), 403

    datos = request.get_json(force=True) or {}
    nombre_usuario = (datos.get("usuario") or "").strip()
    nivel = (datos.get("nivel") or "ver").lower()

    if not nombre_usuario:
        return jsonify({"error": "El nombre de usuario es obligatorio"}), 400

    if nivel not in ("ver", "editar"):
        return jsonify({"error": "Nivel debe ser 'ver' o 'editar'"}), 400

    # Verificar que el usuario existe
    usuario_destino = db.execute(
        "SELECT id FROM usuarios WHERE nombre_usuario = ? COLLATE NOCASE", (nombre_usuario,)
    ).fetchone()

    if not usuario_destino:
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario_destino_id = usuario_destino["id"]

    if usuario_destino_id == usuario_id:
        return jsonify({"error": "No puedes compartir la lista contigo mismo"}), 400

    # Insertar o actualizar permiso
    try:
        db.execute(
            """
            INSERT OR REPLACE INTO permisos_lista
            (lista_id, usuario_id, nivel, fecha_otorgado)
            VALUES (?, ?, ?, ?)
            """,
            (lista_id, usuario_destino_id, nivel, ahora()),
        )
        db.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "mensaje": f"Lista compartida con {nombre_usuario}",
        "nivel": nivel,
        "usuario": nombre_usuario,
    }), 201


@bp.route("/<int:lista_id>/permisos", methods=["GET"])
def listar_permisos(lista_id):
    """Lista los usuarios con acceso a la lista y sus permisos."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    # Solo el propietario puede ver los permisos
    if lista["usuario_propietario_id"] != usuario_id:
        return jsonify({"error": "Solo el propietario puede ver los permisos"}), 403

    # Propietario
    propietario = {
        "usuario_id": lista["usuario_propietario_id"],
        "nombre_usuario": db.execute(
            "SELECT nombre_usuario FROM usuarios WHERE id = ?", (lista["usuario_propietario_id"],)
        ).fetchone()["nombre_usuario"],
        "nivel": "propietario",
    }

    # Usuarios con permisos explícitos
    permisos = db.execute(
        """
        SELECT pl.usuario_id, u.nombre_usuario, pl.nivel, pl.fecha_otorgado
        FROM permisos_lista pl
        JOIN usuarios u ON pl.usuario_id = u.id
        WHERE pl.lista_id = ?
        ORDER BY u.nombre_usuario
        """,
        (lista_id,),
    ).fetchall()

    return jsonify({
        "propietario": propietario,
        "compartida_con": [dict(p) for p in permisos],
    })


@bp.route("/<int:lista_id>/permisos/<int:usuario_id>", methods=["DELETE"])
def revocar_permiso(lista_id, usuario_id):
    """Revoca el acceso a un usuario (solo propietario)."""
    propietario_id = session.get("usuario_id")
    if not propietario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    lista = db.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()

    if not lista:
        return jsonify({"error": "Lista no encontrada"}), 404

    if lista["usuario_propietario_id"] != propietario_id:
        return jsonify({"error": "Solo el propietario puede revocar permisos"}), 403

    if usuario_id == propietario_id:
        return jsonify({"error": "El propietario no puede revocar su propio acceso"}), 400

    db.execute(
        "DELETE FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id),
    )
    db.commit()

    return "", 204


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
