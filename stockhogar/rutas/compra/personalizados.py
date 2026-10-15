"""Catalogo de articulos personalizados de cada hogar: listar, traducciones, editar y borrar."""
from .blueprint import bp
from .lista import traducir_en_segundo_plano
from flask import session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...db import ahora, get_db
from ...servicios.stock import hogar_actual_con_permiso
from ...utils import Validator
from ..inventario.categorias import normalizar_categoria
from ..hogar.hogares import _usuario_tiene_permiso


def usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido=None):
    """Un artículo personalizado pertenece al catálogo privado de un hogar
    (articulos_personalizados.usuario_propietario_id = hogares.usuario_propietario_id
    del hogar dueño del catálogo), así que basta con comprobar que el usuario
    tiene el nivel de permiso requerido en alguna hogar de ese mismo dueño.
    OJO: no basta con mirar articulos_compra, porque un artículo del catálogo
    puede no estar referenciado por ningún artículo activo/completado de
    ninguna lista (p.ej. tras eliminarlo de la lista) y aun así seguir
    perteneciendo legítimamente al hogar."""
    articulo = db.execute(
        "SELECT usuario_propietario_id, hogar_id FROM articulos_personalizados WHERE id = ?",
        (articulo_id,)
    ).fetchone()
    if not articulo:
        return False
    if articulo["hogar_id"]:
        # Creado en un hogar concreto: solo sus miembros (no los de otros hogares del dueño).
        return bool(_usuario_tiene_permiso(db, articulo["hogar_id"], usuario_id, nivel_requerido=nivel_requerido))
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
        "WHERE usuario_propietario_id = ? AND (hogar_id IS NULL OR hogar_id = ?) ORDER BY LOWER(nombre)",
        (propietario["usuario_propietario_id"], hogar_id),
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

    if not usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id):
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

    if not usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido="editar"):
        return APIResponse.no_permitido()

    datos = cuerpo_json()
    if not datos:
        return APIResponse.error("err_nada_que_actualizar", 400)

    # Actualizar campos permitidos
    nombre = str(datos.get("nombre") or articulo["nombre"] or "").strip()
    categoria = normalizar_categoria(db, datos.get("categoria") or articulo["categoria"])
    icono = str(datos.get("icono") or articulo["icono"] or "").strip() or None
    unidad = str(datos.get("unidad") or articulo["unidad"] or "").strip()
    sub_descripcion = str(datos.get("sub_descripcion") or articulo["sub_descripcion"] or "").strip() or None
    dias_aviso = Validator.entero_minimo(
        Validator.con_defecto(datos, "dias_aviso", articulo["dias_aviso"]),
        "días de aviso", 0, 365,
    )

    # articulos_personalizados tiene UNIQUE(nombre, usuario_propietario_id), asi
    # que renombrar un articulo al nombre de otro que ya tiene el usuario
    # (p. ej. "Leche desnatada" -> "Leche") lanzaba IntegrityError y salia como
    # 500 sin explicar nada. Se comprueba antes y se responde 400.
    if nombre.lower() != (articulo["nombre"] or "").lower():
        ya_existe = db.execute(
            "SELECT 1 FROM articulos_personalizados "
            "WHERE LOWER(nombre) = LOWER(?) AND usuario_propietario_id = ? AND id != ?",
            (nombre, articulo["usuario_propietario_id"], articulo_id),
        ).fetchone()
        if ya_existe:
            return APIResponse.error("err_articulo_personalizado_duplicado", 400)

    db.execute(
        """UPDATE articulos_personalizados
           SET nombre=?, categoria=?, icono=?, unidad=?, sub_descripcion=?, dias_aviso=?, fecha_actualizacion=?
           WHERE id=?""",
        (nombre, categoria, icono, unidad, sub_descripcion, dias_aviso, ahora(), articulo_id)
    )

    # Si cambio el nombre o la descripcion se actualizan las traducciones, pero DESPUES del
    # commit y en segundo plano: traducir (red/CPU, segundos) con la escritura abierta
    # bloqueaba la BD a todos los demas usuarios.
    cambio_nombre = nombre != articulo["nombre"]
    cambio_desc = bool(sub_descripcion) and sub_descripcion != articulo["sub_descripcion"]

    db.commit()
    if cambio_nombre or cambio_desc:
        traducir_en_segundo_plano(articulo_id, nombre, sub_descripcion, cambio_nombre, cambio_desc)
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

    if not usuario_puede_acceder_articulo_personalizado(db, articulo_id, usuario_id, nivel_requerido="editar"):
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
