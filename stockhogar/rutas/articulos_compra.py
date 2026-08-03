"""Rutas de artículos en la lista de la compra de un hogar (antes lista_compra)."""
import logging
from flask import Blueprint, request, session, jsonify

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import DIAS_AVISO_DEFECTO
from ..db import ahora, get_db
from ..servicios.stock import hogar_actual_con_permiso
from ..utils import Validator, DataConverter
from .categorias import normalizar_categoria
from .historial import buscar_historial, recordar_articulo
from .hogares import _usuario_tiene_permiso

bp = Blueprint("articulos_compra", __name__, url_prefix="/api/articulos")
logger = logging.getLogger(__name__)

LIMITE_COMPLETADOS = 12
CAMPOS_EDITABLES = {"nombre", "cantidad", "unidad", "categoria", "icono", "sub_descripcion", "dias_aviso"}
# Campos que describen el artículo estándar en sí (no la cantidad puntual en
# esta lista): si se editan mientras el ítem apunta a un artículo del
# catálogo estándar, el ítem se "bifurca" a un artículo personalizado propio
# del hogar en vez de tocar el catálogo global compartido.
CAMPOS_PERSONALIZAN = {"nombre", "categoria", "icono", "unidad", "sub_descripcion", "dias_aviso"}


def _resolver_hogar_id(db, session):
    """Resuelve la lista a usar: SIEMPRE la lista activa de la sesión (la
    misma que usa /api/productos para el stock), nunca el 'hogar_id' que
    manda el cliente (localStorage en el navegador). Ambos valores se
    guardan por separado y pueden desincronizarse (p. ej. tras cambiar de
    lista con una petición en segundo plano en curso); si se confiara en el
    del cliente, el stock y la lista de la compra podrían mostrar hogares
    distintos y un artículo añadido automáticamente por bajada de stock
    parecería no añadirse nunca."""
    return hogar_actual_con_permiso(db, session)


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_articulos():
    """Lista artículos de la lista activa (o de hogar_id si se indica y hay permiso)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    hogar_id = _resolver_hogar_id(db, session)

    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    pendientes = db.execute(
        "SELECT * FROM articulos_compra WHERE activo = 1 AND hogar_id = ? "
        "ORDER BY categoria, nombre COLLATE NOCASE",
        (hogar_id,),
    ).fetchall()
    completados = db.execute(
        "SELECT * FROM articulos_compra WHERE activo = 0 AND hogar_id = ? "
        "ORDER BY fecha_completado DESC LIMIT ?",
        (hogar_id, LIMITE_COMPLETADOS),
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
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        return APIResponse.error("err_nombre_obligatorio", 400)

    db = get_db()
    # Igual que en listar_articulos: si el hogar_id que manda el cliente
    # (guardado en localStorage) no coincide con la lista activa real de la
    # sesión, se ignora y se usa la de sesión, para que el artículo quede
    # siempre en la misma lista que el stock que lo disparó.
    hogar_id = _resolver_hogar_id(db, session)

    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    # Validar permisos
    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    cantidad_sumar = Validator.entero_minimo(datos.get("cantidad") or 1, "cantidad")

    # Si ya está en la lista activa, sumar cantidad
    existente = db.execute(
        "SELECT * FROM articulos_compra WHERE nombre = ? COLLATE NOCASE AND activo = 1 AND hogar_id = ?",
        (nombre, hogar_id),
    ).fetchone()
    if existente:
        db.execute(
            "UPDATE articulos_compra SET cantidad = cantidad + ?, fecha_actualizacion = ? WHERE id = ?",
            (cantidad_sumar, ahora(), existente["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (existente["id"],)).fetchone()
        return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))

    # Si hay uno completado, reutilizarlo
    completado = db.execute(
        "SELECT * FROM articulos_compra WHERE nombre = ? COLLATE NOCASE AND activo = 0 AND hogar_id = ?",
        (nombre, hogar_id),
    ).fetchone()
    if completado:
        db.execute(
            "UPDATE articulos_compra SET activo = 1, cantidad = ?, fecha_completado = NULL, fecha_actualizacion = ? WHERE id = ?",
            (cantidad_sumar, ahora(), completado["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (completado["id"],)).fetchone()
        return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))

    # Buscar en historial estándar
    recuerdo = buscar_historial(db, nombre)
    categoria = normalizar_categoria(db, datos.get("categoria") or (recuerdo["categoria"] if recuerdo else None))
    icono = (datos.get("icono") or "").strip() or (recuerdo["icono"] if recuerdo else None)
    unidad = (datos.get("unidad") or "").strip() or (recuerdo["unidad"] if recuerdo else "ud")
    sub_descripcion = (datos.get("sub_descripcion") or "").strip() or (
        recuerdo["sub_descripcion"] if recuerdo else None
    )
    dias_aviso = int(datos.get("dias_aviso") or (recuerdo["dias_aviso"] if recuerdo else DIAS_AVISO_DEFECTO))

    # ===== LÓGICA NUEVA: Artículos Personalizados =====
    # Si el artículo NO está en historial estándar → crearlo en articulos_personalizados
    articulo_personalizado_id = None
    if not recuerdo:
        # Buscar/crear en articulos_personalizados, aislado por el propietario
        # de la lista (cada hogar tiene su propio catálogo personalizado, ver
        # migración en db.py sobre usuario_propietario_id).
        propietario = db.execute(
            "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)
        ).fetchone()
        propietario_id = propietario["usuario_propietario_id"]

        articulo_personal = db.execute(
            "SELECT id FROM articulos_personalizados WHERE nombre = ? COLLATE NOCASE AND usuario_propietario_id = ?",
            (nombre, propietario_id)
        ).fetchone()

        if articulo_personal:
            articulo_personalizado_id = articulo_personal["id"]
        else:
            # Crear nuevo artículo personalizado
            cur = db.execute(
                """INSERT INTO articulos_personalizados
                   (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, fecha_creacion, fecha_actualizacion, usuario_propietario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), ahora(), propietario_id)
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
                                    """DELETE FROM traducciones_productos
                                       WHERE articulo_personalizado_id = ? AND tipo = ? AND idioma = ?""",
                                    (articulo_personalizado_id, tipo, idioma)
                                )
                                db.execute(
                                    """INSERT INTO traducciones_productos
                                       (articulo_personalizado_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (articulo_personalizado_id, tipo, idioma, original, texto, ahora())
                                )
                            except Exception as e:
                                logger.error(f"Error almacenando traducción: {e}")
            except Exception as e:
                logger.error(f"Error traduciendo artículo: {e}")

    # Crear artículo en lista
    cur = db.execute(
        """INSERT INTO articulos_compra
           (hogar_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, dias_aviso, origen, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (hogar_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad_sumar, sub_descripcion, dias_aviso, 'manual', ahora(), ahora())
    )

    # Recordar para historial si tiene icono
    if icono and recuerdo:
        recordar_articulo(db, nombre, icono, categoria, unidad, sub_descripcion, dias_aviso=dias_aviso)

    db.commit()
    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.articulo_lista_to_dict(fila), 201)


@bp.route("/<int:item_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_articulo(item_id):
    """Actualiza un artículo (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return APIResponse.no_encontrado("recurso_articulo")

    # Validar permisos sobre la lista
    permiso = _usuario_tiene_permiso(db, fila["hogar_id"], usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido("err_sin_permiso_editar_hogar")

    datos = request.get_json(force=True) or {}
    if not datos:
        return APIResponse.validacion("err_nada_que_actualizar")

    if "activo" in datos:
        if datos["activo"]:
            db.execute(
                "UPDATE articulos_compra SET activo = 1, fecha_completado = NULL, fecha_actualizacion = ? WHERE id = ?",
                (ahora(), item_id),
            )
        else:
            db.execute(
                "UPDATE articulos_compra SET activo = 0, fecha_completado = ?, fecha_actualizacion = ? WHERE id = ?",
                (ahora(), ahora(), item_id),
            )

    if CAMPOS_EDITABLES & datos.keys():
        actual = DataConverter.articulo_lista_to_dict(fila)
        nombre = (datos.get("nombre") or actual["nombre"]).strip() or actual["nombre"]
        if "cantidad" in datos:
            cantidad = Validator.entero_minimo(datos.get("cantidad") or 1, "cantidad")
        else:
            cantidad = actual["cantidad"]
        unidad = (datos.get("unidad") or actual["unidad"]).strip() or actual["unidad"]
        categoria = normalizar_categoria(db, datos.get("categoria", actual["categoria"]))
        icono = (datos.get("icono", actual["icono"]) or "").strip() or None
        sub_descripcion = (datos.get("sub_descripcion", actual["sub_descripcion"]) or "").strip() or None
        dias_aviso = int(
            Validator.con_defecto(datos, "dias_aviso", actual.get("dias_aviso") or DIAS_AVISO_DEFECTO)
        )

        # Si el ítem aún apunta al catálogo estándar (sin articulo_personalizado_id)
        # y se está tocando algún campo que describe el artículo en sí, se
        # bifurca a un artículo personalizado propio del hogar en vez de
        # sobrescribir el catálogo compartido por todas las hogares.
        articulo_personalizado_id = actual["articulo_personalizado_id"]
        if articulo_personalizado_id is None and (CAMPOS_PERSONALIZAN & datos.keys()):
            propietario = db.execute(
                "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (fila["hogar_id"],)
            ).fetchone()
            propietario_id = propietario["usuario_propietario_id"]

            existente_personal = db.execute(
                "SELECT id FROM articulos_personalizados WHERE nombre = ? COLLATE NOCASE AND usuario_propietario_id = ?",
                (nombre, propietario_id),
            ).fetchone()
            if existente_personal:
                articulo_personalizado_id = existente_personal["id"]
                db.execute(
                    "UPDATE articulos_personalizados SET categoria=?, icono=?, unidad=?, sub_descripcion=?, "
                    "dias_aviso=?, fecha_actualizacion=? WHERE id=?",
                    (categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), articulo_personalizado_id),
                )
            else:
                cur = db.execute(
                    """INSERT INTO articulos_personalizados
                       (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, fecha_creacion, fecha_actualizacion, usuario_propietario_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), ahora(), propietario_id),
                )
                articulo_personalizado_id = cur.lastrowid

            db.execute(
                "UPDATE articulos_compra SET nombre=?, cantidad=?, unidad=?, categoria=?, icono=?, "
                "sub_descripcion=?, dias_aviso=?, articulo_personalizado_id=?, fecha_actualizacion=? WHERE id=?",
                (nombre, cantidad, unidad, categoria, icono, sub_descripcion, dias_aviso, articulo_personalizado_id, ahora(), item_id),
            )
        elif articulo_personalizado_id is not None and (CAMPOS_PERSONALIZAN & datos.keys()):
            # Ya es personalizado: se edita directamente su catálogo privado.
            db.execute(
                "UPDATE articulos_personalizados SET nombre=?, categoria=?, icono=?, unidad=?, "
                "sub_descripcion=?, dias_aviso=?, fecha_actualizacion=? WHERE id=?",
                (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), articulo_personalizado_id),
            )
            db.execute(
                "UPDATE articulos_compra SET nombre=?, cantidad=?, unidad=?, categoria=?, icono=?, "
                "sub_descripcion=?, dias_aviso=?, fecha_actualizacion=? WHERE id=?",
                (nombre, cantidad, unidad, categoria, icono, sub_descripcion, dias_aviso, ahora(), item_id),
            )
        else:
            db.execute(
                "UPDATE articulos_compra SET nombre=?, cantidad=?, unidad=?, categoria=?, icono=?, "
                "sub_descripcion=?, dias_aviso=?, fecha_actualizacion=? WHERE id=?",
                (nombre, cantidad, unidad, categoria, icono, sub_descripcion, dias_aviso, ahora(), item_id),
            )

    db.commit()
    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (item_id,)).fetchone()
    return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))


@bp.route("/<int:item_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_articulo(item_id):
    """Elimina un artículo (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return APIResponse.no_encontrado("recurso_articulo")

    # Validar permisos sobre la lista
    permiso = _usuario_tiene_permiso(db, fila["hogar_id"], usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    db.execute("DELETE FROM articulos_compra WHERE id = ?", (item_id,))
    db.commit()
    return APIResponse.success(None, 204)


# ===== ENDPOINTS PARA ARTÍCULOS PERSONALIZADOS =====

def _usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido=None):
    """Un artículo personalizado pertenece al catálogo privado de un hogar
    (articulos_personalizados.usuario_propietario_id = hogares.usuario_propietario_id
    del hogar dueño del catálogo), así que basta con comprobar que el usuario
    tiene el nivel de permiso requerido en alguna hogar de ese mismo dueño.
    OJO: no basta con mirar articulos_compra, porque un artículo del catálogo
    puede no estar referenciado por ningún artículo activo/completado de
    ninguna lista (p.ej. tras eliminarlo de la lista) y aun así seguir
    perteneciendo legítimamente al hogar."""
    articulo = db.execute(
        "SELECT usuario_propietario_id FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()
    if not articulo:
        return False
    hogares_ids = db.execute(
        "SELECT id FROM hogares WHERE usuario_propietario_id = ?",
        (articulo["usuario_propietario_id"],)
    ).fetchall()
    return any(
        _usuario_tiene_permiso(db, fila["id"], usuario_id, nivel_requerido=nivel_requerido)
        for fila in hogares_ids
    )


@bp.route("/personalizados", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_articulos_personalizados():
    """Catálogo de artículos personalizados del hogar activo (aislado por
    usuario_propietario_id), con su id, para poder editarlos/eliminarlos."""
    db = get_db()

    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    propietario = db.execute(
        "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)
    ).fetchone()
    if not propietario:
        return APIResponse.success([])

    filas = db.execute(
        "SELECT id, nombre, icono, categoria, unidad, dias_aviso FROM articulos_personalizados "
        "WHERE usuario_propietario_id = ? ORDER BY nombre COLLATE NOCASE",
        (propietario["usuario_propietario_id"],),
    ).fetchall()
    return APIResponse.success([dict(fila) for fila in filas])


@bp.route("/personalizados/<int:articulo_id>/traducciones/<idioma>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_traducciones_articulo_personalizado(articulo_id, idioma):
    """Obtiene traducciones almacenadas de un artículo personalizado."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("recurso_articulo_personalizado")

    if not _usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id):
        return APIResponse.no_permitido()

    # Obtener traducciones
    traducciones = db.execute(
        """SELECT tipo, texto_traducido FROM traducciones_productos
           WHERE articulo_personalizado_id = ? AND idioma = ?""",
        (articulo_id, idioma)
    ).fetchall()

    resultado = {}
    for tipo, texto in traducciones:
        resultado[tipo] = texto

    return APIResponse.success(resultado)


@bp.route("/personalizados/<int:articulo_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_articulo_personalizado(articulo_id):
    """Actualiza un artículo personalizado."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("recurso_articulo_personalizado")

    if not _usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido="editar"):
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    if not datos:
        return APIResponse.error("err_nada_que_actualizar", 400)

    # Actualizar campos permitidos
    nombre = (datos.get("nombre") or articulo["nombre"]).strip()
    categoria = normalizar_categoria(db, datos.get("categoria") or articulo["categoria"])
    icono = (datos.get("icono") or articulo["icono"] or "").strip() or None
    unidad = (datos.get("unidad") or articulo["unidad"]).strip()
    sub_descripcion = (datos.get("sub_descripcion") or articulo["sub_descripcion"] or "").strip() or None
    dias_aviso = int(Validator.con_defecto(datos, "dias_aviso", articulo["dias_aviso"]))

    db.execute(
        """UPDATE articulos_personalizados
           SET nombre=?, categoria=?, icono=?, unidad=?, sub_descripcion=?, dias_aviso=?, fecha_actualizacion=?
           WHERE id=?""",
        (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), articulo_id)
    )

    # Si cambió el nombre o descripción, actualizar traducciones
    if nombre != articulo["nombre"] or sub_descripcion != articulo["sub_descripcion"]:
        try:
            from stockhogar.servicios.traductor_auto import TraductorAutomatico

            # Actualizar traducciones del nombre
            if nombre != articulo["nombre"]:
                traducciones = TraductorAutomatico.traducir_a_todos_idiomas(nombre)
                for idioma, texto in traducciones.items():
                    if idioma != "es" and texto:
                        db.execute(
                            """DELETE FROM traducciones_productos
                               WHERE articulo_personalizado_id = ? AND tipo = ? AND idioma = ?""",
                            (articulo_id, "nombre", idioma)
                        )
                        db.execute(
                            """INSERT INTO traducciones_productos
                               (articulo_personalizado_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (articulo_id, "nombre", idioma, nombre, texto, ahora())
                        )

            # Actualizar traducciones de la descripción
            if sub_descripcion and sub_descripcion != articulo["sub_descripcion"]:
                traducciones = TraductorAutomatico.traducir_a_todos_idiomas(sub_descripcion)
                for idioma, texto in traducciones.items():
                    if idioma != "es" and texto:
                        db.execute(
                            """DELETE FROM traducciones_productos
                               WHERE articulo_personalizado_id = ? AND tipo = ? AND idioma = ?""",
                            (articulo_id, "descripcion", idioma)
                        )
                        db.execute(
                            """INSERT INTO traducciones_productos
                               (articulo_personalizado_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (articulo_id, "descripcion", idioma, sub_descripcion, texto, ahora())
                        )
        except Exception as e:
            logger.error(f"Error al traducir cambios: {e}")

    db.commit()
    fila = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()

    return APIResponse.success({
        "id": fila["id"],
        "nombre": fila["nombre"],
        "categoria": fila["categoria"],
        "icono": fila["icono"],
        "unidad": fila["unidad"],
        "sub_descripcion": fila["sub_descripcion"],
        "dias_aviso": fila["dias_aviso"],
        "fecha_actualizacion": fila["fecha_actualizacion"]
    })


@bp.route("/personalizados/<int:articulo_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_articulo_personalizado(articulo_id):
    """Elimina un artículo personalizado."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("recurso_articulo_personalizado")

    if not _usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido="editar"):
        return APIResponse.no_permitido()

    # Verificar que no está en uso en artículos activos
    en_uso = db.execute(
        "SELECT COUNT(*) as count FROM articulos_compra WHERE articulo_personalizado_id = ? AND activo = 1",
        (articulo_id,)
    ).fetchone()

    if en_uso["count"] > 0:
        return APIResponse.error(
            "No se puede eliminar: artículo está en uso en la lista de la compra",
            400
        )

    # Eliminar traducciones asociadas
    db.execute("DELETE FROM traducciones_productos WHERE articulo_personalizado_id = ?", (articulo_id,))

    # Eliminar artículos completados de la lista de la compra
    db.execute("DELETE FROM articulos_compra WHERE articulo_personalizado_id = ?", (articulo_id,))

    # Eliminar artículo personalizado
    db.execute("DELETE FROM articulos_personalizados WHERE id = ?", (articulo_id,))

    db.commit()
    return APIResponse.success(None, 204)
