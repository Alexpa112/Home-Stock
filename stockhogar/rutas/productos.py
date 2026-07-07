"""Rutas del inventario de productos (stock)."""
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from .categorias import normalizar_categoria
from .historial import buscar_historial, recordar_articulo

bp = Blueprint("productos", __name__, url_prefix="/api/productos")


def row_to_dict(row):
    dias_aviso = row["dias_aviso"] if "dias_aviso" in row.keys() else DIAS_AVISO_DEFECTO
    fecha_actualizacion = row["fecha_actualizacion"] if "fecha_actualizacion" in row.keys() else None
    revisar_caducidad = False
    if dias_aviso and fecha_actualizacion:
        dias_transcurridos = (datetime.now() - datetime.fromisoformat(fecha_actualizacion)).days
        revisar_caducidad = dias_transcurridos >= dias_aviso

    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "categoria": row["categoria"],
        "icono": row["icono"] if "icono" in row.keys() else None,
        "cantidad": row["cantidad"],
        "unidad": row["unidad"],
        "stock_minimo": row["stock_minimo"],
        "fecha_creacion": row["fecha_creacion"] if "fecha_creacion" in row.keys() else None,
        "fecha_actualizacion": fecha_actualizacion,
        "dias_aviso": dias_aviso,
        "revisar_caducidad": revisar_caducidad,
    }


def revisar_stock_bajo(db, producto_id):
    """Mantiene la lista de la compra en sincronia con el stock del producto."""
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if fila is None:
        return
    producto = row_to_dict(fila)
    pendiente = db.execute(
        "SELECT id FROM lista_compra WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
        (producto_id,),
    ).fetchone()

    if producto["cantidad"] <= producto["stock_minimo"]:
        if pendiente is None:
            db.execute(
                "INSERT INTO lista_compra (producto_id, nombre, unidad, categoria, icono, origen) "
                "VALUES (?, ?, ?, ?, ?, 'auto')",
                (producto_id, producto["nombre"], producto["unidad"], producto["categoria"], producto["icono"]),
            )
    elif pendiente is not None:
        # Se ha vuelto a subir el stock: lo damos por comprado en vez de borrarlo,
        # asi aparece en "Comprados recientemente" de la lista de la compra.
        db.execute(
            "UPDATE lista_compra SET activo = 0, fecha_completado = ? WHERE id = ?",
            (ahora(), pendiente["id"]),
        )


def sumar_stock(db, producto_id, cantidad_a_sumar):
    """Suma unidades a un producto existente (usado por +/- y por la confirmacion de tickets)."""
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if fila is None:
        return
    nueva_cantidad = max(0, fila["cantidad"] + cantidad_a_sumar)
    db.execute(
        "UPDATE productos SET cantidad = ?, fecha_actualizacion = ? WHERE id = ?",
        (nueva_cantidad, ahora(), producto_id),
    )
    revisar_stock_bajo(db, producto_id)


def crear_producto_nuevo(
    db, nombre, categoria, cantidad, unidad, stock_minimo=1, dias_aviso=DIAS_AVISO_DEFECTO, icono=None
):
    categoria = normalizar_categoria(db, categoria)
    if not icono:
        recuerdo = buscar_historial(db, nombre)
        if recuerdo:
            icono = recuerdo["icono"]
    cur = db.execute(
        "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, "
        "fecha_creacion, fecha_actualizacion, dias_aviso, icono) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nombre, categoria, cantidad, unidad, stock_minimo, ahora(), ahora(), dias_aviso, icono),
    )
    if icono:
        recordar_articulo(db, nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
    revisar_stock_bajo(db, cur.lastrowid)
    return cur.lastrowid


@bp.route("", methods=["GET"])
def listar_productos():
    db = get_db()
    filas = db.execute(
        "SELECT * FROM productos ORDER BY categoria, nombre COLLATE NOCASE"
    ).fetchall()
    return jsonify([row_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
def crear_producto():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    categoria = datos.get("categoria") or "Otros"
    cantidad = int(datos.get("cantidad") or 0)
    unidad = (datos.get("unidad") or "ud").strip() or "ud"
    stock_minimo = int(datos.get("stock_minimo") or 1)
    dias_aviso = int(datos.get("dias_aviso", DIAS_AVISO_DEFECTO))
    icono = (datos.get("icono") or "").strip() or None

    db = get_db()
    producto_id = crear_producto_nuevo(db, nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono)
    db.commit()
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    return jsonify(row_to_dict(fila)), 201


@bp.route("/<int:producto_id>", methods=["PATCH"])
def actualizar_producto(producto_id):
    db = get_db()
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if fila is None:
        return jsonify({"error": "Producto no encontrado"}), 404

    datos = request.get_json(force=True) or {}
    actual = row_to_dict(fila)

    if "delta" in datos:
        sumar_stock(db, producto_id, int(datos["delta"]))
    else:
        nombre = (datos.get("nombre") or actual["nombre"]).strip()
        categoria = datos.get("categoria") or actual["categoria"]
        if categoria != normalizar_categoria(db, categoria):
            categoria = actual["categoria"]
        cantidad = int(datos.get("cantidad", actual["cantidad"]))
        unidad = (datos.get("unidad") or actual["unidad"]).strip() or actual["unidad"]
        stock_minimo = int(datos.get("stock_minimo", actual["stock_minimo"]))
        dias_aviso = int(datos.get("dias_aviso", actual["dias_aviso"]))
        icono = (datos.get("icono", actual["icono"]) or "").strip() or None
        db.execute(
            "UPDATE productos SET nombre=?, categoria=?, cantidad=?, unidad=?, stock_minimo=?, "
            "dias_aviso=?, icono=?, fecha_actualizacion=? WHERE id=?",
            (nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, ahora(), producto_id),
        )
        if icono:
            recordar_articulo(db, nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
        revisar_stock_bajo(db, producto_id)

    db.commit()
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    return jsonify(row_to_dict(fila))


@bp.route("/<int:producto_id>", methods=["DELETE"])
def borrar_producto(producto_id):
    db = get_db()
    db.execute("DELETE FROM lista_compra WHERE producto_id = ? AND origen = 'auto'", (producto_id,))
    db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    db.commit()
    return "", 204
