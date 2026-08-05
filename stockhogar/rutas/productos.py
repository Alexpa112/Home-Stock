"""Rutas del inventario de productos (stock)."""
import logging
import threading
from flask import Blueprint, current_app, g, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from ..utils import Validator, DataConverter, ValidationError
from ..servicios.stock import (
    hogar_actual_con_permiso,
    revisar_stock_bajo,
    sumar_stock,
    crear_producto_nuevo,
    registrar_movimiento,
)
from .categorias import normalizar_categoria
from .historial import recordar_articulo
from .hogares import _usuario_tiene_permiso
from ..servicios.traductor_auto import TraductorAutomatico

bp = Blueprint("productos", __name__, url_prefix="/api/productos")
logger = logging.getLogger(__name__)


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_productos():
    db = get_db()

    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        # Sin lista activa o sin permiso: no se muestra stock de nadie más
        return APIResponse.success([])

    # El stock es el que hay en stock_hogar para ESTA lista (no el catálogo global).
    # sl.cantidad/sl.stock_minimo se seleccionan DESPUÉS que p.cantidad/p.stock_minimo
    # para que, con nombres de columna repetidos, prevalezcan los valores de la lista.
    filas = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM stock_hogar sl
           JOIN productos p ON p.id = sl.producto_id
           WHERE sl.hogar_id = ?
           ORDER BY p.categoria, LOWER(p.nombre)""",
        (hogar_id,),
    ).fetchall()

    return APIResponse.success([DataConverter.producto_to_dict(f) for f in filas])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_producto():
    datos = request.get_json(force=True) or {}
    nombre = Validator.string_requerido(datos.get("nombre"), "nombre", 80)
    categoria = Validator.string_opcional(datos.get("categoria"), "Otros", 50)
    cantidad = Validator.entero_no_negativo(Validator.con_defecto(datos, "cantidad", 0), "cantidad")
    stock_minimo = Validator.entero_no_negativo(Validator.con_defecto(datos, "stock_minimo", 1), "stock mínimo")
    dias_aviso = int(Validator.con_defecto(datos, "dias_aviso", DIAS_AVISO_DEFECTO))
    unidad = Validator.string_opcional(datos.get("unidad"), "ud", 20)
    icono = Validator.string_opcional(datos.get("icono"), None, 30)

    db = get_db()

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    producto_id = crear_producto_nuevo(
        db, nombre, categoria, cantidad, unidad, stock_minimo, dias_aviso, icono, hogar_id
    )
    db.commit()
    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_hogar sl ON p.id = sl.producto_id AND sl.hogar_id = ?
           WHERE p.id = ?""",
        (hogar_id, producto_id),
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

    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.no_permitido()

    producto = db.execute(
        """SELECT p.id FROM productos p
           JOIN stock_hogar sl ON sl.producto_id = p.id AND sl.hogar_id = ?
           WHERE p.id = ?""",
        (hogar_id, producto_id),
    ).fetchone()

    if not producto:
        return APIResponse.no_encontrado("recurso_producto")

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


def _traducir_y_guardar_en_segundo_plano(app, nombre, descripcion, producto_id, articulo_id):
    """Traduce a todos los idiomas y graba en BD, en un hilo aparte.

    Cada idioma es 1-2 inferencias neuronales de Argos Translate (hasta 8
    en total para nombre+descripcion): ejecutado dentro del ciclo
    request-response, esto ocupaba un worker/hilo de gunicorn entero durante
    esa traduccion (cientos de ms a varios segundos en una Raspberry Pi),
    dejando sin atender el resto de peticiones del hogar (listar productos,
    marcar un articulo comprado...) mientras tanto. El cliente nunca lee la
    respuesta de este endpoint (ver app.js: fetch(...).catch(...), sin
    .then()), asi que no hay perdida funcional en no esperarla.
    """
    with app.app_context():
        try:
            db = get_db()
            traducciones_nombre = TraductorAutomatico.traducir_a_todos_idiomas(nombre) if nombre else {}
            traducciones_desc = TraductorAutomatico.traducir_a_todos_idiomas(descripcion) if descripcion else {}

            for idioma in traducciones_nombre:
                if idioma != "es":  # No guardar original
                    try:
                        db.execute(
                            """INSERT INTO traducciones_productos
                               (producto_id, articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?, ?)
                               ON CONFLICT(producto_id, articulo_id, tipo, idioma) DO UPDATE SET
                                   texto_original = excluded.texto_original,
                                   texto_traducido = excluded.texto_traducido,
                                   fecha_creacion = excluded.fecha_creacion""",
                            (producto_id, articulo_id, "nombre", idioma, nombre, traducciones_nombre[idioma], ahora())
                        )
                    except Exception as e:
                        logger.error(f"Error almacenando traducción: {e}")

            for idioma in traducciones_desc:
                if idioma != "es" and descripcion:
                    try:
                        db.execute(
                            """INSERT INTO traducciones_productos
                               (producto_id, articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?, ?)
                               ON CONFLICT(producto_id, articulo_id, tipo, idioma) DO UPDATE SET
                                   texto_original = excluded.texto_original,
                                   texto_traducido = excluded.texto_traducido,
                                   fecha_creacion = excluded.fecha_creacion""",
                            (producto_id, articulo_id, "descripcion", idioma, descripcion, traducciones_desc[idioma], ahora())
                        )
                    except Exception as e:
                        logger.error(f"Error almacenando traducción: {e}")

            db.commit()
        except Exception:
            logger.exception("Error en traduccion automatica en segundo plano")


@bp.route("/traducir", methods=["POST"])
@requerir_sesion
@manejo_errores
def traducir_producto_auto():
    """
    Encola la traducción automática de un nombre/descripción a todos los
    idiomas y la guarda en BD para reutilización, en segundo plano (ver
    _traducir_y_guardar_en_segundo_plano). Usado al crear un nuevo
    producto/artículo.
    """
    # El frontend dispara esta petición en segundo plano sin esperarla
    # (ver app.js). Esta ruta no toca la sesión, así que pedimos a
    # SessionInterfaceOmitible que no la reenvíe (ver stockhogar/__init__.py)
    # para no pisar con una cookie desactualizada la lista activa si el
    # usuario cambia de lista mientras el hilo en segundo plano sigue vivo.
    g._omitir_refresco_sesion = True

    datos = request.get_json(force=True) or {}
    nombre = Validator.string_opcional(datos.get("nombre"), "", 80)
    descripcion = Validator.string_opcional(datos.get("descripcion"), "", 200)
    producto_id = datos.get("producto_id")  # Opcional
    articulo_id = datos.get("articulo_id")  # Opcional

    if producto_id or articulo_id:
        db = get_db()
        usuario_id = session.get("usuario_id")

        # Comprobar que el producto_id/articulo_id pertenece a una lista a la
        # que el usuario tiene acceso: sin esto, cualquier usuario autenticado
        # podia pasar el ID de un producto/articulo de OTRO hogar (los IDs son
        # autoincrementales y facilmente enumerables) y sobrescribir sus
        # traducciones via INSERT OR REPLACE.
        acceso_valido = False
        if producto_id:
            lista_del_producto = db.execute(
                "SELECT hogar_id FROM stock_hogar WHERE producto_id = ?", (producto_id,)
            ).fetchall()
            acceso_valido = any(
                _usuario_tiene_permiso(db, fila["hogar_id"], usuario_id) for fila in lista_del_producto
            )
        elif articulo_id:
            fila_articulo = db.execute(
                "SELECT hogar_id FROM articulos_compra WHERE id = ?", (articulo_id,)
            ).fetchone()
            acceso_valido = bool(
                fila_articulo and _usuario_tiene_permiso(db, fila_articulo["hogar_id"], usuario_id)
            )

        if not acceso_valido:
            return APIResponse.no_permitido()

    app = current_app._get_current_object()
    threading.Thread(
        target=_traducir_y_guardar_en_segundo_plano,
        args=(app, nombre, descripcion, producto_id, articulo_id),
        daemon=True,
    ).start()

    return APIResponse.success({"encolado": True})


@bp.route("/<int:producto_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_producto(producto_id):
    db = get_db()

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_hogar sl ON p.id = sl.producto_id AND sl.hogar_id = ?
           WHERE p.id = ?""",
        (hogar_id, producto_id),
    ).fetchone()
    if not fila:
        return APIResponse.no_encontrado("recurso_producto")

    datos = request.get_json(force=True) or {}
    actual = DataConverter.producto_to_dict(fila)

    if "delta" in datos:
        try:
            delta = int(datos.get("delta", 0))
        except (TypeError, ValueError) as e:
            raise ValidationError("delta debe ser un número entero") from e
        sumar_stock(db, producto_id, delta, hogar_id)
    else:
        nombre = Validator.string_opcional(datos.get("nombre"), actual["nombre"], 80)
        categoria = datos.get("categoria") or actual["categoria"]
        if categoria != normalizar_categoria(db, categoria):
            categoria = actual["categoria"]
        cantidad = Validator.entero_no_negativo(
            Validator.con_defecto(datos, "cantidad", actual["cantidad"]), "cantidad"
        )
        stock_minimo = Validator.entero_no_negativo(
            Validator.con_defecto(datos, "stock_minimo", actual["stock_minimo"]), "stock mínimo"
        )
        dias_aviso = int(Validator.con_defecto(datos, "dias_aviso", actual["dias_aviso"]))
        unidad = Validator.string_opcional(datos.get("unidad"), actual["unidad"], 20)
        icono = Validator.string_opcional(datos.get("icono"), actual.get("icono"), 30)

        # nombre/categoria/unidad/icono son datos de catálogo compartidos entre hogares;
        # cantidad/stock_minimo son propios de ESTA lista y solo se guardan en stock_hogar.
        db.execute(
            "UPDATE productos SET nombre=?, categoria=?, unidad=?, "
            "dias_aviso=?, icono=?, fecha_actualizacion=? WHERE id=?",
            (nombre, categoria, unidad, dias_aviso, icono, ahora(), producto_id),
        )

        db.execute(
            """UPDATE stock_hogar SET cantidad=?, stock_minimo=?, fecha_actualizacion=?
               WHERE hogar_id=? AND producto_id=?""",
            (cantidad, stock_minimo, ahora(), hogar_id, producto_id)
        )

        if cantidad != actual["cantidad"]:
            registrar_movimiento(db, producto_id, hogar_id, cantidad - actual["cantidad"], cantidad, origen="edicion")

        if icono:
            recordar_articulo(db, nombre, icono, categoria, unidad, cantidad_defecto=cantidad)
        revisar_stock_bajo(db, producto_id, hogar_id)

    db.commit()
    fila = db.execute(
        """SELECT p.id, p.nombre, p.categoria, p.icono, p.unidad,
                  p.fecha_creacion, p.fecha_actualizacion, p.dias_aviso,
                  sl.cantidad, sl.stock_minimo
           FROM productos p JOIN stock_hogar sl ON p.id = sl.producto_id AND sl.hogar_id = ?
           WHERE p.id = ?""",
        (hogar_id, producto_id),
    ).fetchone()
    return APIResponse.success(DataConverter.producto_to_dict(fila))


@bp.route("/<int:producto_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_producto(producto_id):
    db = get_db()

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    en_lista = db.execute(
        "SELECT 1 FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?",
        (hogar_id, producto_id),
    ).fetchone()
    if not en_lista:
        return APIResponse.no_encontrado("recurso_producto")

    # Solo se quita de ESTA lista: el producto/catálogo puede seguir en otras hogares
    db.execute(
        "DELETE FROM articulos_compra WHERE producto_id = ? AND origen = 'auto' AND hogar_id = ?",
        (producto_id, hogar_id),
    )
    db.execute(
        "DELETE FROM stock_hogar WHERE hogar_id = ? AND producto_id = ?",
        (hogar_id, producto_id),
    )

    # Si ninguna otra lista usa ya este producto, limpiar el catálogo global
    otras = db.execute(
        "SELECT 1 FROM stock_hogar WHERE producto_id = ?", (producto_id,)
    ).fetchone()
    if not otras:
        db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))

    db.commit()
    return APIResponse.success()
