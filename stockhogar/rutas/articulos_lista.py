"""Rutas de artículos en listas (antes lista_compra)."""
import logging
from flask import Blueprint, request, session, jsonify

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..servicios.stock import lista_actual_con_permiso
from ..utils import Validator, DataConverter
from .categorias import normalizar_categoria
from .historial import buscar_historial, recordar_articulo
from .listas import _usuario_tiene_permiso

bp = Blueprint("articulos_lista", __name__, url_prefix="/api/articulos")
logger = logging.getLogger(__name__)

LIMITE_COMPLETADOS = 12
CAMPOS_EDITABLES = {"nombre", "cantidad", "unidad", "categoria", "icono", "sub_descripcion"}


def _resolver_lista_id(db, session):
    """Resuelve la lista a usar: SIEMPRE la lista activa de la sesión (la
    misma que usa /api/productos para el stock), nunca el 'lista_id' que
    manda el cliente (localStorage en el navegador). Ambos valores se
    guardan por separado y pueden desincronizarse (p. ej. tras cambiar de
    lista con una petición en segundo plano en curso); si se confiara en el
    del cliente, el stock y la lista de la compra podrían mostrar listas
    distintas y un artículo añadido automáticamente por bajada de stock
    parecería no añadirse nunca."""
    return lista_actual_con_permiso(db, session)


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_articulos():
    """Lista artículos de la lista activa (o de lista_id si se indica y hay permiso)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    lista_id = _resolver_lista_id(db, session)

    if not lista_id:
        return APIResponse.error("No hay una lista activa", 400)

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
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        return APIResponse.error("El nombre es obligatorio", 400)

    db = get_db()
    # Igual que en listar_articulos: si el lista_id que manda el cliente
    # (guardado en localStorage) no coincide con la lista activa real de la
    # sesión, se ignora y se usa la de sesión, para que el artículo quede
    # siempre en la misma lista que el stock que lo disparó.
    lista_id = _resolver_lista_id(db, session)

    if not lista_id:
        return APIResponse.error("No hay una lista activa", 400)

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

    from .espacios import obtener_espacio_actual
    espacio_id = obtener_espacio_actual(db)

    # Buscar en historial estándar
    recuerdo = buscar_historial(db, nombre, espacio_id)
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
                                logger.error(f"Error almacenando traducción: {e}")
            except Exception as e:
                logger.error(f"Error traduciendo artículo: {e}")

    # Crear artículo en lista
    cur = db.execute(
        """INSERT INTO articulos_lista
           (lista_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, origen, fecha_creacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lista_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad_sumar, sub_descripcion, 'manual', ahora())
    )

    # Recordar para historial si tiene icono
    if icono and recuerdo:
        recordar_articulo(db, espacio_id, nombre, icono, categoria, unidad, sub_descripcion)

    db.commit()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (cur.lastrowid,)).fetchone()
    return APIResponse.success(DataConverter.articulo_lista_to_dict(fila), 201)


@bp.route("/<int:item_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_articulo(item_id):
    """Actualiza un artículo (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return APIResponse.no_encontrado("Artículo")

    # Validar permisos sobre la lista
    permiso = _usuario_tiene_permiso(db, fila["lista_id"], usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido("No tienes permisos para editar esta lista")

    datos = request.get_json(force=True) or {}
    if not datos:
        return APIResponse.validacion("No hay nada que actualizar")

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
            from .espacios import obtener_espacio_actual
            recordar_articulo(db, obtener_espacio_actual(db), nombre, icono, categoria, unidad, sub_descripcion)

    db.commit()
    fila = db.execute("SELECT * FROM articulos_lista WHERE id = ?", (item_id,)).fetchone()
    return APIResponse.success(DataConverter.articulo_lista_to_dict(fila))


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


# ===== ENDPOINTS PARA ARTÍCULOS PERSONALIZADOS =====

@bp.route("/personalizados/<int:articulo_id>/traducciones/<idioma>", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_traducciones_articulo_personalizado(articulo_id, idioma):
    """Obtiene traducciones almacenadas de un artículo personalizado."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    from .espacios import obtener_espacio_actual
    espacio_id = obtener_espacio_actual(db)

    # Verificar que el artículo pertenece al usuario
    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ? AND espacio_id = ?",
        (articulo_id, espacio_id)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("Artículo personalizado")

    # Obtener traducciones
    traducciones = db.execute(
        """SELECT tipo, texto_traducido FROM traducciones_productos
           WHERE articulo_id = ? AND idioma = ?""",
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

    from .espacios import obtener_espacio_actual
    espacio_id = obtener_espacio_actual(db)

    # Verificar que el artículo pertenece al usuario
    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ? AND espacio_id = ?",
        (articulo_id, espacio_id)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("Artículo personalizado")

    datos = request.get_json(force=True) or {}
    if not datos:
        return APIResponse.error("No hay nada que actualizar", 400)

    # Actualizar campos permitidos
    nombre = (datos.get("nombre") or articulo["nombre"]).strip()
    categoria = normalizar_categoria(db, datos.get("categoria") or articulo["categoria"])
    icono = (datos.get("icono") or articulo["icono"] or "").strip() or None
    unidad = (datos.get("unidad") or articulo["unidad"]).strip()
    sub_descripcion = (datos.get("sub_descripcion") or articulo["sub_descripcion"] or "").strip() or None

    db.execute(
        """UPDATE articulos_personalizados
           SET nombre=?, categoria=?, icono=?, unidad=?, sub_descripcion=?, fecha_actualizacion=?
           WHERE id=?""",
        (nombre, categoria, icono, unidad, sub_descripcion, ahora(), articulo_id)
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
                            """INSERT OR REPLACE INTO traducciones_productos
                               (articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (articulo_id, "nombre", idioma, nombre, texto, ahora())
                        )

            # Actualizar traducciones de la descripción
            if sub_descripcion and sub_descripcion != articulo["sub_descripcion"]:
                traducciones = TraductorAutomatico.traducir_a_todos_idiomas(sub_descripcion)
                for idioma, texto in traducciones.items():
                    if idioma != "es" and texto:
                        db.execute(
                            """INSERT OR REPLACE INTO traducciones_productos
                               (articulo_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
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
        "fecha_actualizacion": fila["fecha_actualizacion"]
    })


@bp.route("/personalizados/<int:articulo_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_articulo_personalizado(articulo_id):
    """Elimina un artículo personalizado."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    from .espacios import obtener_espacio_actual
    espacio_id = obtener_espacio_actual(db)

    # Verificar que el artículo pertenece al usuario
    articulo = db.execute(
        "SELECT * FROM articulos_personalizados WHERE id = ? AND espacio_id = ?",
        (articulo_id, espacio_id)
    ).fetchone()

    if not articulo:
        return APIResponse.no_encontrado("Artículo personalizado")

    # Verificar que no está en uso en artículos activos
    en_uso = db.execute(
        "SELECT COUNT(*) as count FROM articulos_lista WHERE articulo_personalizado_id = ? AND activo = 1",
        (articulo_id,)
    ).fetchone()

    if en_uso["count"] > 0:
        return APIResponse.error(
            "No se puede eliminar: artículo está en uso en listas activas",
            400
        )

    # Eliminar traducciones asociadas
    db.execute("DELETE FROM traducciones_productos WHERE articulo_id = ?", (articulo_id,))

    # Eliminar artículos completados de listas
    db.execute("DELETE FROM articulos_lista WHERE articulo_personalizado_id = ?", (articulo_id,))

    # Eliminar artículo personalizado
    db.execute("DELETE FROM articulos_personalizados WHERE id = ?", (articulo_id,))

    db.commit()
    return APIResponse.success(None, 204)
