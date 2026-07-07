"""Rutas de la lista de la compra."""
from flask import Blueprint, jsonify, request

from ..db import ahora, get_db
from .categorias import normalizar_categoria
from .espacios import obtener_espacio_actual
from .historial import buscar_historial, recordar_articulo

bp = Blueprint("lista_compra", __name__, url_prefix="/api/lista-compra")

# Cuantos articulos completados recientemente se muestran como "sugerencias"
# para volver a añadirlos con un toque (al estilo "utilizados recientemente").
LIMITE_COMPLETADOS = 12

CAMPOS_EDITABLES = {"nombre", "cantidad", "unidad", "categoria", "icono", "sub_descripcion"}


def compra_a_dict(row):
    return {
        "id": row["id"],
        "producto_id": row["producto_id"],
        "nombre": row["nombre"],
        "unidad": row["unidad"],
        "categoria": row["categoria"],
        "icono": row["icono"] if "icono" in row.keys() else None,
        "cantidad": row["cantidad"] if "cantidad" in row.keys() else 1,
        "sub_descripcion": row["sub_descripcion"] if "sub_descripcion" in row.keys() else None,
        "origen": row["origen"],
        "activo": bool(row["activo"]),
    }


@bp.route("", methods=["GET"])
def listar_lista_compra():
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    pendientes = db.execute(
        "SELECT * FROM lista_compra WHERE activo = 1 AND espacio_id = ? "
        "ORDER BY categoria, nombre COLLATE NOCASE",
        (espacio_id,),
    ).fetchall()
    completados = db.execute(
        "SELECT * FROM lista_compra WHERE activo = 0 AND espacio_id = ? "
        "ORDER BY fecha_completado DESC LIMIT ?",
        (espacio_id, LIMITE_COMPLETADOS),
    ).fetchall()
    return jsonify({
        "pendientes": [compra_a_dict(f) for f in pendientes],
        "completados": [compra_a_dict(f) for f in completados],
    })


@bp.route("", methods=["POST"])
def anadir_lista_compra():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    cantidad_sumar = max(1, int(datos.get("cantidad") or 1))

    # Si ya esta en la lista activa, un "añadir" repetido simplemente suma
    # cantidad en vez de crear una fila duplicada (asi el toque rapido del
    # catalogo funciona como cabria esperar).
    existente = db.execute(
        "SELECT * FROM lista_compra WHERE nombre = ? COLLATE NOCASE AND activo = 1 AND espacio_id = ?",
        (nombre, espacio_id),
    ).fetchone()
    if existente:
        db.execute(
            "UPDATE lista_compra SET cantidad = cantidad + ? WHERE id = ?",
            (cantidad_sumar, existente["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM lista_compra WHERE id = ?", (existente["id"],)).fetchone()
        return jsonify(compra_a_dict(fila))

    recuerdo = buscar_historial(db, nombre)
    categoria = normalizar_categoria(db, datos.get("categoria") or (recuerdo["categoria"] if recuerdo else None))
    icono = (datos.get("icono") or "").strip() or (recuerdo["icono"] if recuerdo else None)
    unidad = (datos.get("unidad") or "").strip() or (recuerdo["unidad"] if recuerdo else "ud")
    sub_descripcion = (datos.get("sub_descripcion") or "").strip() or (
        recuerdo["sub_descripcion"] if recuerdo else None
    )

    cur = db.execute(
        "INSERT INTO lista_compra "
        "(nombre, unidad, categoria, icono, cantidad, sub_descripcion, espacio_id, origen) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'manual')",
        (nombre, unidad, categoria, icono, cantidad_sumar, sub_descripcion, espacio_id),
    )
    if icono:
        recordar_articulo(db, nombre, icono, categoria, unidad, sub_descripcion)
    db.commit()
    fila = db.execute("SELECT * FROM lista_compra WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(compra_a_dict(fila)), 201


@bp.route("/<int:item_id>", methods=["PATCH"])
def actualizar_lista_compra(item_id):
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    fila = db.execute(
        "SELECT * FROM lista_compra WHERE id = ? AND espacio_id = ?", (item_id, espacio_id)
    ).fetchone()
    if fila is None:
        return jsonify({"error": "No encontrado"}), 404

    datos = request.get_json(force=True) or {}
    if not datos:
        return jsonify({"error": "No hay nada que actualizar"}), 400

    if "activo" in datos:
        if datos["activo"]:
            db.execute(
                "UPDATE lista_compra SET activo = 1, fecha_completado = NULL WHERE id = ?",
                (item_id,),
            )
        else:
            db.execute(
                "UPDATE lista_compra SET activo = 0, fecha_completado = ? WHERE id = ?",
                (ahora(), item_id),
            )

    if CAMPOS_EDITABLES & datos.keys():
        actual = compra_a_dict(fila)
        nombre = (datos.get("nombre") or actual["nombre"]).strip() or actual["nombre"]
        cantidad = max(1, int(datos.get("cantidad", actual["cantidad"]) or 1))
        unidad = (datos.get("unidad") or actual["unidad"]).strip() or actual["unidad"]
        categoria = normalizar_categoria(db, datos.get("categoria", actual["categoria"]))
        icono = (datos.get("icono", actual["icono"]) or "").strip() or None
        sub_descripcion = (datos.get("sub_descripcion", actual["sub_descripcion"]) or "").strip() or None

        db.execute(
            "UPDATE lista_compra SET nombre=?, cantidad=?, unidad=?, categoria=?, icono=?, "
            "sub_descripcion=? WHERE id=?",
            (nombre, cantidad, unidad, categoria, icono, sub_descripcion, item_id),
        )
        if icono:
            recordar_articulo(db, nombre, icono, categoria, unidad, sub_descripcion)

    db.commit()
    fila = db.execute("SELECT * FROM lista_compra WHERE id = ?", (item_id,)).fetchone()
    return jsonify(compra_a_dict(fila))


@bp.route("/<int:item_id>", methods=["DELETE"])
def borrar_lista_compra(item_id):
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    db.execute("DELETE FROM lista_compra WHERE id = ? AND espacio_id = ?", (item_id, espacio_id))
    db.commit()
    return "", 204
