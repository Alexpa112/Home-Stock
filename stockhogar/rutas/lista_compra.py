"""Rutas de artículos en listas (antes lista_compra)."""
from flask import Blueprint, request, session, jsonify

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..utils import Validator, DataConverter
from .categorias import normalizar_categoria
from .historial import buscar_historial, recordar_articulo
from .listas import _usuario_tiene_permiso

bp = Blueprint("lista_compra", __name__, url_prefix="/api/articulos")

LIMITE_COMPLETADOS = 12
CAMPOS_EDITABLES = {"nombre", "cantidad", "unidad", "categoria", "icono", "sub_descripcion"}


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_articulos():
    """Lista artículos de una lista (requiere query param lista_id)."""
    usuario_id = session.get("usuario_id")
    lista_id = request.args.get("lista_id", type=int)

    if not lista_id:
        return APIResponse.error("Parámetro lista_id es obligatorio", 400)

    db = get_db()
    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    pendientes = db.execute(
        "SELECT * FROM articulos_lista WHERE activo = 1 AND lista_id = ? "
        "ORDER BY categoria, nombre COLLATE NOCASE",
        (lista_id,),
    ).fetchall()
    completados = db.execute(
        "SELECT * FROM articulos_lista WHERE activo = 0 AND lista_id = ? "
        "ORDER BY fecha_completado DESC LIMIT ?",
        (lista_id, LIMITE_COMPLETADOS),
    ).fetchall()

    return APIResponse.success({
        "pendientes": [DataConverter.articulo_lista_to_dict(f) for f in pendientes],
        "completados": [DataConverter.articulo_lista_to_dict(f) for f in completados],
    })


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def anadir_articulo():
    """Añade un artículo a una lista (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    lista_id = datos.get("lista_id", type=int)
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        return APIResponse.error("El nombre es obligatorio", 400)

    if not lista_id:
        return APIResponse.error("lista_id es obligatorio", 400)

    db = get_db()

    # Validar permisos
    permiso = _usuario_tiene_permiso(db, lista_id, usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    cantidad_sumar = max(1, int(datos.get("cantidad") or 1))

    # Si ya está en la lista activa, sumar cantidad
    existente = db.execute(
        "SELECT * FROM articulos_lista WHERE nombre = ? COLLATE NOCASE AND activo = 1 AND lista_id = ?",
        (nombre, lista_id),
    ).fetchone()
    if existente:
        db.execute(
            "UPDATE articulos_lista SET cantidad = cantidad + ? WHERE id = ?",
            (cantidad_sumar, existente["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (existente["id"],)).fetchone()
        return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))

    # Si hay uno completado, reutilizarlo
    completado = db.execute(
        "SELECT * FROM articulos_lista WHERE nombre = ? COLLATE NOCASE AND activo = 0 AND lista_id = ?",
        (nombre, lista_id),
    ).fetchone()
    if completado:
        db.execute(
            "UPDATE articulos_lista SET activo = 1, cantidad = ?, fecha_completado = NULL WHERE id = ?",
            (cantidad_sumar, completado["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (completado["id"],)).fetchone()
        return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))

    # Buscar en historial estándar
    recuerdo = buscar_historial(db, nombre)
    categoria = normalizar_categoria(db, datos.get("categoria") or (recuerdo["categoria"] if recuerdo else None))
    icono = (datos.get("icono") or "").strip() or (recuerdo["icono"] if recuerdo else None)
    unidad = (datos.get("unidad") or "").strip() or (recuerdo["unidad"] if recuerdo else "ud")
    sub_descripcion = (datos.get("sub_descripcion") or "").strip() or (
        recuerdo["sub_descripcion"] if recuerdo else None
    )

    # ===== LÓGICA NUEVA: Artículos Personalizados =====
    # Si el artículo NO está en historial estándar → crearlo en articulos_personalizados
    articulo_personalizado_id = None
    if not recuerdo:
        from .espacios import obtener_espacio_actual
        espacio_id = obtener_espacio_actual(db)

        # Buscar/crear en articulos_personalizados
        articulo_personal = db.execute(
            "SELECT id FROM articulos_personalizados WHERE nombre = ? COLLATE NOCASE AND espacio_id = ?",
            (nombre, espacio_id)
        ).fetchone()

        if articulo_personal:
            articulo_personalizado_id = articulo_personal["id"]
        else:
            # Crear nuevo artículo personalizado
            cur = db.execute(
                """INSERT INTO articulos_personalizados
                   (espacio_id, nombre, categoria, icono, unidad, sub_descripcion, fecha_creacion, fecha_actualizacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (espacio_id, nombre, categoria, icono, unidad, sub_descripcion, ahora(), ahora())
            )
            articulo_personalizado_id = cur.lastrowid

            # Traducir automáticamente el artículo personalizado
            try:
                from stockhogar.servicios.traductor_auto import TraductorAutomatico
                traducciones = {
                    'nombre': TraductorAutomatico.traducir_a_todos_idiomas(nombre),
                    'descripcion': TraductorAutomatico.traducir_a_todos_idiomas(sub_descripcion) if sub_descripcion else {}
                }
                # Almacenar traducciones
                for tipo in ['nombre', 'descripcion']:
                    if not traducciones[tipo]:
                        continue
                    for idioma, texto in traducciones[tipo].items():
                        if idioma != 'es' and texto:  # No guardar original
                            original = nombre if tipo == 'nombre' else sub_descripcion
                            try:
                                db.execute(
                                    """INSERT OR REPLACE INTO traducciones_productos
                                       (articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (articulo_personalizado_id, tipo, idioma, original, texto, ahora())
                                )
                            except Exception as e:
                                print(f"Error almacenando traducción: {e}")
            except Exception as e:
                print(f"Error traduciendo artículo: {e}")

    # Crear artículo en lista
    cur = db.execute(
        """INSERT INTO articulos_lista
           (lista_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, origen, fecha_creacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lista_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad_sumar, sub_descripcion, 'manual', ahora())
    )

    # Recordar para historial si tiene icono
    if icono and recuerdo:
        recordar_articulo(db, nombre, icono, categoria, unidad, sub_descripcion)

    db.commit()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.articulo_lista_to_dict(fila), 201)


@bp.route("/<int:item_id>", methods=["PATCH"])
def actualizar_articulo(item_id):
    """Actualiza un artículo (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "No autorizado"}), 401

    db = get_db()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return jsonify({"error": "No encontrado"}), 404

    # Validar permisos sobre la lista
    permiso = _usuario_tiene_permiso(db, fila["lista_id"], usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return jsonify({"error": "No tienes permisos para editar esta lista"}), 403

    datos = request.get_json(force=True) or {}
    if not datos:
        return jsonify({"error": "No hay nada que actualizar"}), 400

    if "activo" in datos:
        if datos["activo"]:
            db.execute(
                "UPDATE articulos_lista SET activo = 1, fecha_completado = NULL WHERE id = ?",
                (item_id,),
            )
        else:
            db.execute(
                "UPDATE articulos_lista SET activo = 0, fecha_completado = ? WHERE id = ?",
                (ahora(), item_id),
            )

    if CAMPOS_EDITABLES & datos.keys():
        actual = DataConverter.articulo_lista_to_dict(fila)
        nombre = (datos.get("nombre") or actual["nombre"]).strip() or actual["nombre"]
        cantidad = max(1, int(datos.get("cantidad", actual["cantidad"]) or 1))
        unidad = (datos.get("unidad") or actual["unidad"]).strip() or actual["unidad"]
        categoria = normalizar_categoria(db, datos.get("categoria", actual["categoria"]))
        icono = (datos.get("icono", actual["icono"]) or "").strip() or None
        sub_descripcion = (datos.get("sub_descripcion", actual["sub_descripcion"]) or "").strip() or None

        db.execute(
            "UPDATE articulos_lista SET nombre=?, cantidad=?, unidad=?, categoria=?, icono=?, "
            "sub_descripcion=? WHERE id=?",
            (nombre, cantidad, unidad, categoria, icono, sub_descripcion, item_id),
        )
        if icono:
            recordar_articulo(db, nombre, icono, categoria, unidad, sub_descripcion)

    db.commit()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (item_id,)).fetchone()
    return jsonify(DataConverter.articulo_lista_to_dict(fila))


@bp.route("/<int:item_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_articulo(item_id):
    """Elimina un artículo (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return APIResponse.error("Artículo no encontrado", 404)

    # Validar permisos sobre la lista
    permiso = _usuario_tiene_permiso(db, fila["lista_id"], usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    db.execute("DELETE FROM articulos_lista WHERE id = ?", (item_id,))
    db.commit()
    return APIResponse.success(None, 204)
