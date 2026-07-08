"""Rutas del inventario de productos (stock)."""
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from .categorias import normalizar_categoria
from .espacios import obtener_espacio_actual
from .historial import buscar_historial, recordar_articulo

bp = Blueprint("productos", __name__, url_prefix="/api/productos")


def _parsear_entero_no_negativo(valor, nombre_campo):
    try:
        numero = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"La {nombre_campo} debe ser un número entero") from exc
    if numero < 0:
        raise ValueError(f"La {nombre_campo} no puede ser negativa")
    return numero


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
        "espacio_id": row["espacio_id"] if "espacio_id" in row.keys() and row["espacio_id"] is not None else None,
        "fecha_creacion": row["fecha_creacion"] if "fecha_creacion" in row.keys() else None,
        "fecha_actualizacion": fecha_actualizacion,
        "dias_aviso": dias_aviso,
        "revisar_caducidad": revisar_caducidad,
    }


def revisar_stock_bajo(db, producto_id):
    """Mantiene la lista de la compra en sincronia con el stock del producto."""
    try:
        fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if fila is None:
            return

        # Obtener datos básicos sin usar row_to_dict para evitar problemas con parsing de fechas
        cantidad = fila["cantidad"]
        stock_minimo = fila["stock_minimo"]
        espacio_id = fila["espacio_id"]
        nombre = fila["nombre"]
        unidad = fila["unidad"]
        categoria = fila["categoria"]
        icono = fila["icono"]

        # Si no tiene espacio_id, usar el primero disponible
        if espacio_id is None:
            primero = db.execute("SELECT id FROM espacios ORDER BY id LIMIT 1").fetchone()
            espacio_id = primero["id"] if primero else 1

        pendiente = db.execute(
            "SELECT id FROM lista_compra WHERE producto_id = ? AND origen = 'auto' AND activo = 1",
            (producto_id,),
        ).fetchone()

        if cantidad < stock_minimo:
            if pendiente is None:
                db.execute(
                    "INSERT INTO lista_compra "
                    "(producto_id, nombre, unidad, categoria, icono, espacio_id, origen) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'auto')",
                    (producto_id, nombre, unidad, categoria, icono, espacio_id),
                )
        elif pendiente is not None:
            # Se ha vuelto a subir el stock: lo damos por comprado en vez de borrarlo
            db.execute(
                "UPDATE lista_compra SET activo = 0, fecha_completado = ? WHERE id = ?",
                (ahora(), pendiente["id"]),
            )
    except Exception as e:
        print(f"[revisar_stock_bajo] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # No lanzar excepción, solo loguear el error
        pass


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
    db, nombre, categoria, cantidad, unidad, stock_minimo=1, dias_aviso=DIAS_AVISO_DEFECTO,
    icono=None, espacio_id=None,
):
    categoria = normalizar_categoria(db, categoria)
    if not icono:
        recuerdo = buscar_historial(db, nombre)
        if recuerdo:
            icono = recuerdo["icono"]
    if espacio_id is None:
        espacio_id = obtener_espacio_actual(db)
    cur = db.execute(
        "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, "
        "fecha_creacion, fecha_actualizacion, dias_aviso, icono, espacio_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nombre, categoria, cantidad, unidad, stock_minimo, ahora(), ahora(), dias_aviso, icono, espacio_id),
    )
    if icono:
        recordar_articulo(db, nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
    revisar_stock_bajo(db, cur.lastrowid)
    return cur.lastrowid


@bp.route("", methods=["GET"])
def listar_productos():
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    filas = db.execute(
        "SELECT * FROM productos WHERE espacio_id = ? ORDER BY categoria, nombre COLLATE NOCASE",
        (espacio_id,),
    ).fetchall()
    return jsonify([row_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
def crear_producto():
    datos = request.get_json(force=True) or {}
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400

    categoria = datos.get("categoria") or "Otros"
    try:
        cantidad = _parsear_entero_no_negativo(datos.get("cantidad", 0), "cantidad")
        stock_minimo = _parsear_entero_no_negativo(datos.get("stock_minimo", 1), "stock mínimo")
        dias_aviso = int(datos.get("dias_aviso", DIAS_AVISO_DEFECTO))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    unidad = (datos.get("unidad") or "ud").strip() or "ud"
    icono = (datos.get("icono") or "").strip() or None

    try:
        db = get_db()
        espacio_id = obtener_espacio_actual(db)
        producto_id = crear_producto_nuevo(
            db, nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, espacio_id
        )
        db.commit()
        fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        return jsonify(row_to_dict(fila)), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:producto_id>", methods=["PATCH"])
def actualizar_producto(producto_id):
    try:
        print(f"[PATCH] producto_id={producto_id}")
        db = get_db()
        espacio_id = obtener_espacio_actual(db)
        print(f"[PATCH] espacio_id={espacio_id}")
        fila = db.execute(
            "SELECT * FROM productos WHERE id = ? AND espacio_id = ?", (producto_id, espacio_id)
        ).fetchone()
        if fila is None:
            print(f"[PATCH] Producto {producto_id} no encontrado en espacio {espacio_id}")
            return jsonify({"error": "Producto no encontrado"}), 404

        datos = request.get_json(force=True) or {}
        print(f"[PATCH] datos={datos}")
        actual = row_to_dict(fila)

        if "delta" in datos:
            try:
                delta = int(datos.get("delta", 0))
                print(f"[PATCH] Sumando stock: delta={delta}")
                sumar_stock(db, producto_id, delta)
            except (ValueError, TypeError) as e:
                print(f"[PATCH] Error parseando delta: {e}")
                return jsonify({"error": f"Delta inválido: {e}"}), 400
        else:
            nombre = (datos.get("nombre") or actual["nombre"]).strip()
            categoria = datos.get("categoria") or actual["categoria"]
            if categoria != normalizar_categoria(db, categoria):
                categoria = actual["categoria"]
            try:
                cantidad = _parsear_entero_no_negativo(datos.get("cantidad", actual["cantidad"]), "cantidad")
                stock_minimo = _parsear_entero_no_negativo(
                    datos.get("stock_minimo", actual["stock_minimo"]), "stock mínimo"
                )
                dias_aviso = int(datos.get("dias_aviso", actual["dias_aviso"]))
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            unidad = (datos.get("unidad") or actual["unidad"]).strip() or actual["unidad"]
            icono = (datos.get("icono", actual["icono"]) or "").strip() or None
            db.execute(
                "UPDATE productos SET nombre=?, categoria=?, cantidad=?, unidad=?, stock_minimo=?, "
                "dias_aviso=?, icono=?, fecha_actualizacion=? WHERE id=?",
                (nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, ahora(), producto_id),
            )
            if icono:
                recordar_articulo(db, nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
            revisar_stock_bajo(db, producto_id)

        print(f"[PATCH] Commiting...")
        db.commit()
        fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        print(f"[PATCH] Devolviendo producto actualizado")
        return jsonify(row_to_dict(fila))
    except Exception as e:
        print(f"[PATCH] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error actualizando: {str(e)}"}), 500


@bp.route("/<int:producto_id>", methods=["DELETE"])
def borrar_producto(producto_id):
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    db.execute("DELETE FROM lista_compra WHERE producto_id = ? AND origen = 'auto'", (producto_id,))
    db.execute("DELETE FROM productos WHERE id = ? AND espacio_id = ?", (producto_id, espacio_id))
    db.commit()
    return "", 204
