"""Rutas del inventario de productos (stock)."""
from flask import Blueprint, request

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from ..utils import Validator, DataConverter, ValidationError
from .categorias import normalizar_categoria
from .espacios import obtener_espacio_actual
from .historial import buscar_historial, recordar_articulo
from ..servicios.traductor_auto import TraductorAutomatico

bp = Blueprint("productos", __name__, url_prefix="/api/productos")


def revisar_stock_bajo(db, producto_id, lista_id=None):
    """Mantiene la lista de la compra en sincronia con el stock del producto."""
    try:
        from flask import session

        fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if fila is None:
            return

        # Obtener datos básicos sin usar row_to_dict para evitar problemas con parsing de fechas
        cantidad = fila["cantidad"]
        stock_minimo = fila["stock_minimo"]
        nombre = fila["nombre"]
        unidad = fila["unidad"]
        categoria = fila["categoria"]
        icono = fila["icono"]

        # Si no se proporciona lista_id, obtenerla de la sesión
        if lista_id is None:
            lista_id = session.get("lista_actual_id")

        # Si aún no hay lista_id, usar la primera lista del usuario
        if lista_id is None:
            usuario_id = session.get("usuario_id")
            if usuario_id:
                lista = db.execute(
                    "SELECT id FROM listas WHERE usuario_propietario_id = ? LIMIT 1",
                    (usuario_id,)
                ).fetchone()
                if lista:
                    lista_id = lista["id"]

        if lista_id is None:
            return  # No hay lista, no se puede agregar artículos

        pendiente = db.execute(
            "SELECT id FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND activo = 1 AND lista_id = ?",
            (producto_id, lista_id),
        ).fetchone()

        # CAMBIO CRÍTICO: Aviso cuando cantidad <= stock_minimo (igual O menor)
        if cantidad <= stock_minimo:
            if pendiente is None:
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[revisar_stock_bajo] Error: {type(e).__name__}: {e}", exc_info=True)


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
    # Siempre guardar en historial para sincronización stock ↔ catálogo
    recordar_articulo(db, nombre, icono or "📦", categoria, unidad, cantidad_defecto=cantidad)
    revisar_stock_bajo(db, cur.lastrowid)
    return cur.lastrowid


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_productos():
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    filas = db.execute(
        "SELECT * FROM productos WHERE espacio_id = ? ORDER BY categoria, nombre COLLATE NOCASE",
        (espacio_id,),
    ).fetchall()
    return APIResponse.success([DataConverter.producto_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_producto():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 80)
    categoria = Validator.string_opcional(datos.get("categoria"), "Otros", 50)
    cantidad = Validator.entero_no_negativo(datos.get("cantidad", 0), "cantidad")
    stock_minimo = Validator.entero_no_negativo(datos.get("stock_minimo", 1), "stock mínimo")
    dias_aviso = int(datos.get("dias_aviso", DIAS_AVISO_DEFECTO))
    unidad = Validator.string_opcional(datos.get("unidad"), "ud", 20)
    icono = Validator.string_opcional(datos.get("icono"), None, 10)

    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    producto_id = crear_producto_nuevo(
        db, nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, espacio_id
    )
    db.commit()
    fila = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    return APIResponse.success(DataConverter.producto_to_dict(fila), 201)


@bp.route("/<int:producto_id>/traducciones/<idioma>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_traducciones_producto(producto_id, idioma):
    """
    Obtiene las traducciones almacenadas de un producto para un idioma.

    Devuelve nombre, descripción y otros campos traducidos.
    """
    db = get_db()
    espacio_id = obtener_espacio_actual(db)

    # Verificar que el producto pertenece al usuario
    producto = db.execute(
        "SELECT * FROM productos WHERE id = ? AND espacio_id = ?",
        (producto_id, espacio_id)
    ).fetchone()

    if not producto:
        return APIResponse.no_encontrado("Producto")

    # Obtener traducciones
    traducciones = db.execute(
        """SELECT tipo, texto_traducido FROM traducciones_productos
           WHERE producto_id = ? AND idioma = ?""",
        (producto_id, idioma)
    ).fetchall()

    resultado = {}
    for tipo, texto in traducciones:
        resultado[tipo] = texto

    return APIResponse.success(resultado)


@bp.route("/traducir", methods=["POST"])
@requerir_sesion
@manejo_errores
def traducir_producto_auto():
    """
    Traduce automáticamente un nombre/descripción a todos los idiomas.

    Usado cuando se crea un nuevo producto/artículo.
    Almacena las traducciones en la BD para reutilización.
    """
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_opcional(datos.get("nombre"), "", 80)
    descripcion = Validator.string_opcional(datos.get("descripcion"), "", 200)
    producto_id = datos.get("producto_id")  # Opcional
    articulo_id = datos.get("articulo_id")  # Opcional

    # Traducir a todos los idiomas
    traducciones_nombre = TraductorAutomatico.traducir_a_todos_idiomas(nombre) if nombre else {}
    traducciones_desc = TraductorAutomatico.traducir_a_todos_idiomas(descripcion) if descripcion else {}

    # Almacenar en BD si se proporciona ID
    if producto_id or articulo_id:
        db = get_db()
        for idioma in traducciones_nombre:
            if idioma != "es":  # No guardar original
                try:
                    db.execute(
                        """INSERT OR REPLACE INTO traducciones_productos
                           (producto_id, articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (producto_id, articulo_id, "nombre", idioma, nombre, traducciones_nombre[idioma], ahora())
                    )
                except Exception as e:
                    print(f"Error almacenando traducción: {e}")

        for idioma in traducciones_desc:
            if idioma != "es" and descripcion:
                try:
                    db.execute(
                        """INSERT OR REPLACE INTO traducciones_productos
                           (producto_id, articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (producto_id, articulo_id, "descripcion", idioma, descripcion, traducciones_desc[idioma], ahora())
                    )
                except Exception as e:
                    print(f"Error almacenando traducción: {e}")

        db.commit()

    return APIResponse.success({
        "nombre": traducciones_nombre,
        "descripcion": traducciones_desc
    })


@bp.route("/<int:producto_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_producto(producto_id):
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    fila = db.execute(
        "SELECT * FROM productos WHERE id = ? AND espacio_id = ?", (producto_id, espacio_id)
    ).fetchone()
    if not fila:
        return APIResponse.no_encontrado("Producto")

    datos = request.get_json(force=True) or {}
    actual = DataConverter.producto_to_dict(fila)

    if "delta" in datos:
        delta = int(datos.get("delta", 0))
        sumar_stock(db, producto_id, delta)
    else:
        nombre = Validator.string_opcional(datos.get("nombre"), actual["nombre"], 80)
        categoria = datos.get("categoria") or actual["categoria"]
        if categoria != normalizar_categoria(db, categoria):
            categoria = actual["categoria"]
        cantidad = Validator.entero_no_negativo(datos.get("cantidad", actual["cantidad"]), "cantidad")
        stock_minimo = Validator.entero_no_negativo(
            datos.get("stock_minimo", actual["stock_minimo"]), "stock mínimo"
        )
        dias_aviso = int(datos.get("dias_aviso", actual["dias_aviso"]))
        unidad = Validator.string_opcional(datos.get("unidad"), actual["unidad"], 20)
        icono = Validator.string_opcional(datos.get("icono"), actual.get("icono"), 10)

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
    return APIResponse.success(DataConverter.producto_to_dict(fila))


@bp.route("/<int:producto_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_producto(producto_id):
    db = get_db()
    espacio_id = obtener_espacio_actual(db)
    db.execute("DELETE FROM lista_compra WHERE producto_id = ? AND origen = 'auto'", (producto_id,))
    db.execute("DELETE FROM productos WHERE id = ? AND espacio_id = ?", (producto_id, espacio_id))
    db.commit()
    return APIResponse.success()
