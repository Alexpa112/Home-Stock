"""Lista de la compra: listar, anadir o sumar, editar y borrar articulos."""
from .blueprint import bp, logger
from flask import session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json, texto_json
from ...config import DIAS_AVISO_DEFECTO
from ...db import ahora, get_db
from ...servicios.stock import hogar_actual_con_permiso
from ...utils import Validator, DataConverter
from ..inventario.categorias import normalizar_categoria
from ..inventario.historial import buscar_historial, recordar_articulo
from ..hogar.hogares import _usuario_tiene_permiso


LIMITE_COMPLETADOS = 12


CAMPOS_EDITABLES = {"nombre", "cantidad", "unidad", "categoria", "icono", "sub_descripcion", "dias_aviso"}


# Campos que describen el artículo estándar en sí (no la cantidad puntual en
# esta lista): si se editan mientras el ítem apunta a un artículo del
# catálogo estándar, el ítem se "bifurca" a un artículo personalizado propio
# del hogar en vez de tocar el catálogo global compartido.
CAMPOS_PERSONALIZAN = {"nombre", "categoria", "icono", "unidad", "sub_descripcion", "dias_aviso"}


def resolver_hogar_id(db, session):
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
    hogar_id = resolver_hogar_id(db, session)

    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id)
    if not permiso:
        return APIResponse.no_permitido()

    pendientes = db.execute(
        "SELECT * FROM articulos_compra WHERE activo = 1 AND hogar_id = ? "
        "ORDER BY categoria, LOWER(nombre)",
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


def traducir_en_segundo_plano(articulo_id, nombre, sub_descripcion, traducir_nombre, traducir_descripcion):
    """Traduce el nombre/descripcion de un articulo personalizado y guarda el resultado, en un
    hilo con su PROPIA conexion. Traducir es lento (inferencia neuronal o descarga de modelos)
    y hacerlo dentro de la peticion, con la transaccion de escritura abierta, mantenia la BD
    bloqueada: varios usuarios anadiendo articulos a la vez recibian 'database is locked' (500)."""
    import sqlite3
    import threading

    def trabajo():
        try:
            from stockhogar.config import DB_PATH
            from stockhogar.servicios.traduccion.traductor_auto import TraductorAutomatico
            textos = []
            if traducir_nombre and nombre:
                textos.append(("nombre", nombre))
            if traducir_descripcion and sub_descripcion:
                textos.append(("descripcion", sub_descripcion))
            traducidos = [(tipo, texto, TraductorAutomatico.traducir_a_todos_idiomas(texto)) for tipo, texto in textos]
            conexion = sqlite3.connect(DB_PATH, timeout=30)
            try:
                conexion.execute("PRAGMA busy_timeout = 30000")
                for tipo, original, por_idioma in traducidos:
                    for idioma, texto in (por_idioma or {}).items():
                        if idioma == "es" or not texto:
                            continue
                        conexion.execute(
                            "DELETE FROM traducciones_productos WHERE articulo_personalizado_id = ? AND tipo = ? AND idioma = ?",
                            (articulo_id, tipo, idioma),
                        )
                        conexion.execute(
                            "INSERT INTO traducciones_productos "
                            "(articulo_personalizado_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (articulo_id, tipo, idioma, original, texto, ahora()),
                        )
                conexion.commit()
            finally:
                conexion.close()
        except Exception:
            logger.exception("Error traduciendo articulo %s", articulo_id)

    threading.Thread(target=trabajo, daemon=True).start()


def anadir_o_sumar_articulo(
    db, hogar_id, nombre, cantidad=1, categoria=None, icono=None, unidad=None,
    sub_descripcion=None, dias_aviso=None, codigo_barras=None,
):
    """Añade un artículo a la lista de un hogar, o suma cantidad/reactiva si
    ya existe (misma lógica que POST /api/articulos). Extraída para poder
    reutilizarla al añadir varios ingredientes de una receta de golpe
    (P-06), sin duplicar la resolución de historial/artículo personalizado.
    Hace su propio commit por artículo: pensada para bucles fuera de
    request/response HTTP donde no hace falta atomicidad entre artículos."""
    nombre = (nombre or "").strip()
    cantidad_sumar = Validator.entero_minimo(cantidad or 1, "cantidad")

    # Si ya está en la lista activa, sumar cantidad
    existente = db.execute(
        "SELECT * FROM articulos_compra WHERE LOWER(nombre) = LOWER(?) AND activo = 1 AND hogar_id = ?",
        (nombre, hogar_id),
    ).fetchone()
    if existente:
        db.execute(
            "UPDATE articulos_compra SET cantidad = cantidad + ?, fecha_actualizacion = ? WHERE id = ?",
            (cantidad_sumar, ahora(), existente["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (existente["id"],)).fetchone()
        return DataConverter.articulo_lista_to_dict(fila)

    # Si hay uno completado, reutilizarlo
    completado = db.execute(
        "SELECT * FROM articulos_compra WHERE LOWER(nombre) = LOWER(?) AND activo = 0 AND hogar_id = ?",
        (nombre, hogar_id),
    ).fetchone()
    if completado:
        db.execute(
            "UPDATE articulos_compra SET activo = 1, cantidad = ?, fecha_completado = NULL, fecha_actualizacion = ? WHERE id = ?",
            (cantidad_sumar, ahora(), completado["id"]),
        )
        db.commit()
        fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (completado["id"],)).fetchone()
        return DataConverter.articulo_lista_to_dict(fila)

    # Buscar en historial estándar
    recuerdo = buscar_historial(db, nombre)
    categoria = normalizar_categoria(db, categoria or (recuerdo["categoria"] if recuerdo else None))
    icono = (icono or "").strip() or (recuerdo["icono"] if recuerdo else None)
    unidad = (unidad or "").strip() or (recuerdo["unidad"] if recuerdo else "ud")
    sub_descripcion = (sub_descripcion or "").strip() or (
        recuerdo["sub_descripcion"] if recuerdo else None
    )
    dias_aviso = Validator.entero_minimo(dias_aviso or (recuerdo["dias_aviso"] if recuerdo else DIAS_AVISO_DEFECTO), "días de aviso", 0, 365)
    codigo_barras = (codigo_barras or "").strip() or None

    # ===== LÓGICA NUEVA: Artículos Personalizados =====
    # Si el artículo NO está en historial estándar → crearlo en articulos_personalizados
    articulo_personalizado_id = None
    traducir_pendiente = None
    if not recuerdo:
        # Buscar/crear en articulos_personalizados, aislado por el propietario
        # de la lista (cada hogar tiene su propio catálogo personalizado, ver
        # migración en db/esquema/catalogo.py sobre usuario_propietario_id).
        propietario = db.execute(
            "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)
        ).fetchone()
        propietario_id = propietario["usuario_propietario_id"]

        articulo_personal = db.execute(
            "SELECT id FROM articulos_personalizados WHERE LOWER(nombre) = LOWER(?) AND usuario_propietario_id = ?",
            (nombre, propietario_id)
        ).fetchone()

        if articulo_personal:
            articulo_personalizado_id = articulo_personal["id"]
        else:
            # Crear nuevo artículo personalizado
            cur = db.execute(
                """INSERT INTO articulos_personalizados
                   (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, fecha_creacion, fecha_actualizacion, usuario_propietario_id, hogar_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), ahora(), propietario_id, hogar_id)
            )
            articulo_personalizado_id = cur.fetchone()["id"]

            traducir_pendiente = (articulo_personalizado_id, nombre, sub_descripcion, True, bool(sub_descripcion))

    # Crear artículo en lista. El id se lee INMEDIATAMENTE con RETURNING (no
    # con .lastrowid, que no existe en Postgres): un cursor con RETURNING
    # queda con la fila pendiente de consumir, y SQLite no permite ni otra
    # `execute()` ni `commit()` en la misma conexión hasta leerla.
    cur = db.execute(
        """INSERT INTO articulos_compra
           (hogar_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, dias_aviso, origen, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (hogar_id, articulo_personalizado_id, nombre, unidad, categoria, icono, cantidad_sumar, sub_descripcion, dias_aviso, 'manual', ahora(), ahora())
    )
    nuevo_id = cur.fetchone()["id"]

    # Recordar para historial si tiene icono (o si se acaba de escanear un
    # código de barras nuevo: así el catálogo lo reconoce la próxima vez).
    if (icono or codigo_barras) and (recuerdo or codigo_barras):
        recordar_articulo(
            db, nombre, icono or "h-archive-box", categoria, unidad, sub_descripcion, dias_aviso=dias_aviso,
            codigo_barras=codigo_barras,
        )

    db.commit()
    if traducir_pendiente:
        traducir_en_segundo_plano(*traducir_pendiente)  # DESPUES del commit: sin tener la BD bloqueada
    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (nuevo_id,)).fetchone()
    return DataConverter.articulo_lista_to_dict(fila)


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def anadir_articulo():
    """Añade un artículo a una lista (requiere permiso 'editar')."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    # str(): un {"nombre": 5} pasaba el `or ""` (5 es truthy) y reventaba el
    # .strip() con AttributeError -> 500 en vez de 400.
    nombre = str(datos.get("nombre") or "").strip()

    if not nombre:
        return APIResponse.error("err_nombre_obligatorio", 400)

    db = get_db()
    # Igual que en listar_articulos: si el hogar_id que manda el cliente
    # (guardado en localStorage) no coincide con la lista activa real de la
    # sesión, se ignora y se usa la de sesión, para que el artículo quede
    # siempre en la misma lista que el stock que lo disparó.
    hogar_id = resolver_hogar_id(db, session)

    if not hogar_id:
        return APIResponse.error("err_no_hay_hogar_activo", 400)

    # Validar permisos
    permiso = _usuario_tiene_permiso(db, hogar_id, usuario_id, nivel_requerido="editar")
    if not permiso or (permiso != "propietario" and permiso != "editar"):
        return APIResponse.no_permitido()

    articulo = anadir_o_sumar_articulo(
        db, hogar_id, nombre,
        cantidad=datos.get("cantidad") or 1,
        categoria=texto_json(datos, "categoria"),
        icono=texto_json(datos, "icono"),
        unidad=texto_json(datos, "unidad"),
        sub_descripcion=texto_json(datos, "sub_descripcion"),
        dias_aviso=datos.get("dias_aviso"),
        codigo_barras=texto_json(datos, "codigo_barras"),
    )
    return APIResponse.success(articulo, 201)


@bp.route("/<int:item_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_articulo(item_id):
    """Marcar comprado/pendiente requiere permiso 'comprar'; cambiar nombre,
    cantidad u otros campos del artículo en sí requiere 'editar' (P-08)."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    fila = db.execute("SELECT * FROM articulos_compra WHERE id = ?", (item_id,)).fetchone()

    if fila is None:
        return APIResponse.no_encontrado("recurso_articulo")

    datos = cuerpo_json()
    if not datos:
        return APIResponse.validacion("err_nada_que_actualizar")

    nivel_minimo = "editar" if (CAMPOS_EDITABLES & datos.keys()) else "comprar"
    permiso = _usuario_tiene_permiso(db, fila["hogar_id"], usuario_id, nivel_requerido=nivel_minimo)
    if not permiso:
        return APIResponse.no_permitido("err_sin_permiso_editar_hogar")

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
        nombre = str(datos.get("nombre") or actual["nombre"] or "").strip() or actual["nombre"]
        if "cantidad" in datos:
            cantidad = Validator.entero_minimo(datos.get("cantidad") or 1, "cantidad")
        else:
            cantidad = actual["cantidad"]
        unidad = str(datos.get("unidad") or actual["unidad"] or "").strip() or actual["unidad"]
        categoria = normalizar_categoria(db, datos.get("categoria", actual["categoria"]))
        icono = str(datos.get("icono", actual["icono"]) or "").strip() or None
        sub_descripcion = str(datos.get("sub_descripcion", actual["sub_descripcion"]) or "").strip() or None
        dias_aviso = Validator.entero_minimo(
            Validator.con_defecto(datos, "dias_aviso", actual.get("dias_aviso") or DIAS_AVISO_DEFECTO),
            "días de aviso", 0, 365
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
                "SELECT id FROM articulos_personalizados WHERE LOWER(nombre) = LOWER(?) AND usuario_propietario_id = ?",
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
                       (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, fecha_creacion, fecha_actualizacion, usuario_propietario_id, hogar_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                    (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), ahora(), propietario_id, fila["hogar_id"]),
                )
                articulo_personalizado_id = cur.fetchone()["id"]

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
