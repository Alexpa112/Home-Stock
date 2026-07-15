"""Rutas del inventario de productos (stock)."""
import logging
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from ..utils import Validator, DataConverter, ValidationError
from ..servicios.stock import (
    lista_actual_con_permiso,
    revisar_stock_bajo,
    sumar_stock,
    crear_producto_nuevo,
    registrar_movimiento,
)
from .categorias import normalizar_categoria
from .espacios import obtener_espacio_actual
from .historial import recordar_articulo
from ..servicios.traductor_auto import TraductorAutomatico

bp = Blueprint("productos", __name__, url_prefix="/api/productos")
logger = logging.getLogger(__name__)


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_productos():
    db = get_db()

    lista_id = lista_actual_con_permiso(db, session)
    if not lista_id:
        # Sin lista activa o sin permiso: no se muestra stock de nadie más
        return APIResponse.success([])

    # El stock es el que hay en stock_lista para ESTA lista (no el catálogo global).
    # sl.cantidad/sl.stock_minimo se seleccionan DESPUÉS que p.cantidad/p.stock_minimo
    # para que, con nombres de columna repetidos, prevalezcan los valores de la lista.
    filas = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad, p.espacio_id,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM stock_lista sl
           JOIN productos p ON p.id = sl.producto_id
           WHERE sl.lista_id = ?
           ORDER BY p.categoria, p.nombre COLLATE NOCASE""",
        (lista_id,),
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
    icono = Validator.string_opcional(datos.get("icono"), None, 30)

    db = get_db()
    espacio_id = obtener_espacio_actual(db)

    lista_id = lista_actual_con_permiso(db, session, nivel_requerido="editar")
    if not lista_id:
        return APIResponse.no_permitido()

    producto_id = crear_producto_nuevo(
        db, nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, espacio_id, lista_id
    )
    db.commit()
    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad, p.espacio_id,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_lista sl ON p.id = sl.producto_id AND sl.lista_id = ?
           WHERE p.id = ?""",
        (lista_id, producto_id),
    ).fetchone()
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
                    logger.error(f"Error almacenando traducción: {e}")

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
                    logger.error(f"Error almacenando traducción: {e}")

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

    lista_id = lista_actual_con_permiso(db, session, nivel_requerido="editar")
    if not lista_id:
        return APIResponse.no_permitido()

    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad, p.espacio_id,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_lista sl ON p.id = sl.producto_id AND sl.lista_id = ?
           WHERE p.id = ?""",
        (lista_id, producto_id),
    ).fetchone()
    if not fila:
        return APIResponse.no_encontrado("Producto")

    datos = request.get_json(force=True) or {}
    actual = DataConverter.producto_to_dict(fila)

    if "delta" in datos:
        try:
            delta = int(datos.get("delta", 0))
        except (TypeError, ValueError) as e:
            raise ValidationError("delta debe ser un número entero") from e
        sumar_stock(db, producto_id, delta, lista_id)
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
        icono = Validator.string_opcional(datos.get("icono"), actual.get("icono"), 30)

        # nombre/categoria/unidad/icono son datos de catálogo compartidos entre listas;
        # cantidad/stock_minimo son propios de ESTA lista y solo se guardan en stock_lista.
        db.execute(
            "UPDATE productos SET nombre=?, categoria=?, unidad=?, "
            "dias_aviso=?, icono=?, fecha_actualizacion=? WHERE id=?",
            (nombre, categoria, unidad, dias_aviso, icono, ahora(), producto_id),
        )

        db.execute(
            """UPDATE stock_lista SET cantidad=?, stock_minimo=?, fecha_actualizacion=?
               WHERE lista_id=? AND producto_id=?""",
            (cantidad, stock_minimo, ahora(), lista_id, producto_id)
        )

        if cantidad != actual["cantidad"]:
            registrar_movimiento(db, producto_id, lista_id, cantidad - actual["cantidad"], cantidad, origen="edicion")

        if icono:
            recordar_articulo(db, actual["espacio_id"], nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
        revisar_stock_bajo(db, producto_id, lista_id)

    db.commit()
    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad, p.espacio_id,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_lista sl ON p.id = sl.producto_id AND sl.lista_id = ?
           WHERE p.id = ?""",
        (lista_id, producto_id),
    ).fetchone()
    return APIResponse.success(DataConverter.producto_to_dict(fila))


@bp.route("/<int:producto_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_producto(producto_id):
    db = get_db()

    lista_id = lista_actual_con_permiso(db, session, nivel_requerido="editar")
    if not lista_id:
        return APIResponse.no_permitido()

    en_lista = db.execute(
        "SELECT 1 FROM stock_lista WHERE lista_id = ? AND producto_id = ?",
        (lista_id, producto_id),
    ).fetchone()
    if not en_lista:
        return APIResponse.no_encontrado("Producto")

    # Solo se quita de ESTA lista: el producto/catálogo puede seguir en otras listas
    db.execute(
        "DELETE FROM articulos_lista WHERE producto_id = ? AND origen = 'auto' AND lista_id = ?",
        (producto_id, lista_id),
    )
    db.execute(
        "DELETE FROM stock_lista WHERE lista_id = ? AND producto_id = ?",
        (lista_id, producto_id),
    )

    # Si ninguna otra lista usa ya este producto, limpiar el catálogo global
    otras = db.execute(
        "SELECT 1 FROM stock_lista WHERE producto_id = ?", (producto_id,)
    ).fetchone()
    if not otras:
        db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))

    db.commit()
    return APIResponse.success()
