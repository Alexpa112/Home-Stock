"""Lógica de negocio de stock por lista: creación de productos, sumas de
cantidad y sincronización automática con la lista de la compra.

Extraído de rutas/productos.py para separar las rutas HTTP (CRUD) de la
lógica de dominio, que también reutiliza rutas/tickets.py al confirmar un
ticket escaneado.
"""
import logging

from ..db import ahora
from ..config import DIAS_AVISO_DEFECTO
from ..rutas.categorias import normalizar_categoria
from ..rutas.historial import buscar_historial, recordar_articulo
from ..rutas.listas import _usuario_tiene_permiso

logger = logging.getLogger(__name__)


def lista_actual_con_permiso(db, session, nivel_requerido=None):
    """Devuelve el lista_id activo del usuario si tiene permiso, o None."""
    usuario_id = session.get("usuario_id")
    lista_id = session.get("lista_actual_id")
    if not lista_id:
        if not usuario_id:
            return None
        lista = db.execute(
            "SELECT id FROM listas WHERE usuario_propietario_id = ? "
            "ORDER BY fecha_actualizacion DESC LIMIT 1",
            (usuario_id,)
        ).fetchone()
        if not lista:
            return None
        lista_id = lista["id"]

    if not _usuario_tiene_permiso(db, lista_id, usuario_id, nivel_requerido):
        return None
    return lista_id


def _resolver_lista_id_por_defecto(db, session):
    """Obtiene la lista_id de sesión o, si no hay, la primera lista del usuario."""
    lista_id = session.get("lista_actual_id")
    if lista_id:
        return lista_id

    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None

    lista = db.execute(
        "SELECT id FROM listas WHERE usuario_propietario_id = ? "
        "ORDER BY fecha_actualizacion DESC LIMIT 1",
        (usuario_id,)
    ).fetchone()
    return lista["id"] if lista else None


def revisar_stock_bajo(db, producto_id, lista_id=None):
    """Mantiene la lista de la compra en sincronia con el stock del producto (por lista)."""
    try:
        from flask import session

        if lista_id is None:
            lista_id = _resolver_lista_id_por_defecto(db, session)

        if lista_id is None:
            return  # No hay lista, no se puede agregar artículos

        fila = db.execute(
            """SELECT p.nombre, p.unidad, p.categoria, p.icono, sl.cantidad, sl.stock_minimo
               FROM productos p JOIN stock_lista sl ON p.id = sl.producto_id AND sl.lista_id = ?
               WHERE p.id = ?""",
            (lista_id, producto_id),
        ).fetchone()
        if fila is None:
            return

        cantidad = fila["cantidad"]
        stock_minimo = fila["stock_minimo"]
        nombre = fila["nombre"]
        unidad = fila["unidad"]
        categoria = fila["categoria"]
        icono = fila["icono"]

        pendiente = db.execute(
            "SELECT id FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1 AND lista_id = ?",
            (producto_id, lista_id),
        ).fetchone()

        # CAMBIO CRÍTICO: Aviso cuando cantidad <= stock_minimo (igual O menor)
        if cantidad <= stock_minimo:
            if pendiente is None:
                # Si ya existe una fila completada (comprada) para este producto, reactivarla
                # en vez de crear una nueva: evita duplicados entre "pendientes" y "comprados".
                completado = db.execute(
                    "SELECT id FROM articulos_lista WHERE producto_id = ? AND activo = 0 AND lista_id = ?",
                    (producto_id, lista_id),
                ).fetchone()
                if completado is not None:
                    db.execute(
                        "UPDATE articulos_lista SET activo = 1, origen = 'auto', nombre = ?, unidad = ?, "
                        "categoria = ?, icono = ?, fecha_completado = NULL WHERE id = ?",
                        (nombre, unidad, categoria, icono, completado["id"]),
                    )
                else:
                    db.execute(
                        "INSERT INTO articulos_lista "
                        "(lista_id, producto_id, nombre, unidad, categoria, icono, origen, fecha_creacion) "
                        "VALUES (?, ?, ?, ?, ?, ?, 'auto', ?)",
                        (lista_id, producto_id, nombre, unidad, categoria, icono, ahora()),
                    )
        elif pendiente is not None:
            # Se ha vuelto a subir el stock: lo damos por comprado en vez de borrarlo
            db.execute(
                "UPDATE articulos_lista SET activo = 0, fecha_completado = ? WHERE id = ?",
                (ahora(), pendiente["id"]),
            )
    except Exception as e:
        # Loguear el error pero no interrumpir el flujo
        # (este es un proceso de sincronización que debe ser tolerante a fallos)
        logger.error(f"[revisar_stock_bajo] Error: {type(e).__name__}: {e}", exc_info=True)


def registrar_movimiento(db, producto_id, lista_id, delta, cantidad_resultante, origen="ajuste"):
    """Audita un cambio de cantidad de stock para poder consultar el historial
    de un producto y graficar consumo por periodo (ver rutas/historial.py)."""
    if delta == 0:
        return
    from flask import session
    usuario_id = session.get("usuario_id")
    db.execute(
        """INSERT INTO movimientos_stock
           (producto_id, lista_id, usuario_id, delta, cantidad_resultante, origen, fecha)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (producto_id, lista_id, usuario_id, delta, cantidad_resultante, origen, ahora()),
    )


def sumar_stock(db, producto_id, cantidad_a_sumar, lista_id=None):
    """Suma unidades al stock de un producto DENTRO de una lista concreta."""
    from flask import session

    if lista_id is None:
        lista_id = _resolver_lista_id_por_defecto(db, session)

    if not lista_id:
        return

    actual = db.execute(
        "SELECT cantidad FROM stock_lista WHERE lista_id = ? AND producto_id = ?",
        (lista_id, producto_id),
    ).fetchone()
    if actual is None:
        return

    # Suma atómica en SQL (no leer-calcular-escribir) para evitar perder
    # incrementos si dos peticiones concurrentes tocan el mismo producto.
    db.execute(
        """UPDATE stock_lista SET cantidad = MAX(0, cantidad + ?), fecha_actualizacion = ?
           WHERE lista_id = ? AND producto_id = ?""",
        (cantidad_a_sumar, ahora(), lista_id, producto_id)
    )

    nueva_cantidad = max(0, actual["cantidad"] + cantidad_a_sumar)
    registrar_movimiento(db, producto_id, lista_id, nueva_cantidad - actual["cantidad"], nueva_cantidad)

    revisar_stock_bajo(db, producto_id, lista_id)


def crear_producto_nuevo(
    db, nombre, categoria, cantidad, unidad, stock_minimo=1, dias_aviso=DIAS_AVISO_DEFECTO,
    icono=None, lista_id=None,
):
    """Crea producto en catálogo y registra stock en stock_lista."""
    from flask import session

    categoria = normalizar_categoria(db, categoria)
    if not icono:
        recuerdo = buscar_historial(db, nombre)
        if recuerdo:
            icono = recuerdo["icono"]

    if lista_id is None:
        lista_id = _resolver_lista_id_por_defecto(db, session)

    cur = db.execute(
        "INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, "
        "fecha_creacion, fecha_actualizacion, dias_aviso, icono) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nombre, categoria, cantidad, unidad, stock_minimo, ahora(), ahora(), dias_aviso, icono),
    )
    producto_id = cur.lastrowid

    # El stock del producto solo pertenece a la lista en la que se crea, no a todas
    if lista_id:
        try:
            db.execute(
                """INSERT OR IGNORE INTO stock_lista
                   (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (lista_id, producto_id, cantidad, stock_minimo, ahora(), ahora())
            )
        except Exception as e:
            logger.debug(f"[crear_producto_nuevo] Error en stock_lista: {e}")

    # Guardar en el catálogo compartido de artículos
    recordar_articulo(db, nombre, icono or "h-archive-box", categoria, unidad, cantidad_defecto=cantidad)
    revisar_stock_bajo(db, producto_id, lista_id)
    return producto_id
