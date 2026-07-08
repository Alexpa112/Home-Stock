"""Rutas para gestionar permisos y compartir listas."""
from flask import Blueprint, request, session
from uuid import uuid4
from datetime import datetime, timedelta

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..utils import Validator

bp = Blueprint("permisos", __name__, url_prefix="/api/listas")


@bp.route("/<int:lista_id>/miembros", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_miembros(lista_id):
    """Obtener lista de usuarios con acceso a una lista."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    # Verificar que el usuario es el propietario
    lista = db.execute(
        "SELECT usuario_propietario_id FROM listas WHERE id = ?",
        (lista_id,)
    ).fetchone()

    if not lista or lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    # Obtener propietario
    propietario = db.execute(
        "SELECT id, nombre_usuario FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    # Obtener miembros con permisos
    miembros_datos = db.execute(
        """SELECT u.id, u.nombre_usuario, u.email, p.nivel, p.fecha_otorgado
           FROM usuarios u
           JOIN permisos_lista p ON u.id = p.usuario_id
           WHERE p.lista_id = ?
           ORDER BY p.fecha_otorgado DESC""",
        (lista_id,)
    ).fetchall()

    miembros = [
        {
            "id": m["id"],
            "nombre_usuario": m["nombre_usuario"],
            "email": m["email"],
            "nivel": m["nivel"],
            "fecha_otorgado": m["fecha_otorgado"]
        } for m in miembros_datos
    ]

    return APIResponse.success({
        "propietario": {
            "id": propietario["id"],
            "nombre_usuario": propietario["nombre_usuario"],
            "nivel": "propietario"
        },
        "miembros": miembros
    })


@bp.route("/<int:lista_id>/compartir", methods=["POST"])
@requerir_sesion
@manejo_errores
def compartir_lista(lista_id):
    """Compartir lista con otro usuario o por email."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    datos = request.get_json(force=True) or {}

    # Verificar que el usuario es el propietario
    lista = db.execute(
        "SELECT usuario_propietario_id FROM listas WHERE id = ?",
        (lista_id,)
    ).fetchone()

    if not lista or lista["usuario_propietario_id"] != usuario_id:
        return APIResponse.no_permitido()

    # Obtener email o nombre de usuario destino
    email_destino = (datos.get("email") or "").strip()
    nombre_usuario_destino = (datos.get("nombre_usuario") or "").strip()
    nivel = Validator.string_opcional(datos.get("nivel"), "editar", 10)

    if nivel not in ["ver", "editar"]:
        return APIResponse.error("Nivel debe ser 'ver' o 'editar'", 400)

    # Si es por nombre de usuario
    if nombre_usuario_destino:
        usuario_destino = db.execute(
            "SELECT id FROM usuarios WHERE nombre_usuario = ?",
            (nombre_usuario_destino,)
        ).fetchone()

        if not usuario_destino:
            return APIResponse.error("Usuario no encontrado", 404)

        # Agregar permiso
        try:
            db.execute(
                """INSERT OR REPLACE INTO permisos_lista
                   (lista_id, usuario_id, nivel, fecha_otorgado)
                   VALUES (?, ?, ?, ?)""",
                (lista_id, usuario_destino["id"], nivel, ahora())
            )
            db.commit()
            return APIResponse.success({"mensaje": "Lista compartida correctamente"})
        except Exception as e:
            return APIResponse.error(str(e), 400)

    # Si es por email, crear invitación
    elif email_destino:
        codigo = str(uuid4())[:12]
        fecha_expiracion = (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds")

        try:
            db.execute(
                """INSERT INTO invitaciones_lista
                   (lista_id, email_destino, nivel, codigo_invitacion, fecha_creacion, fecha_expiracion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (lista_id, email_destino, nivel, codigo, ahora(), fecha_expiracion)
            )
            db.commit()

            # TODO: Enviar email con enlace de invitación
            # enlace = f"{URL_BASE}/aceptar-invitacion/{codigo}"

            return APIResponse.success({
                "mensaje": "Invitación enviada",
                "codigo": codigo
            })
        except Exception as e:
            return APIResponse.error(str(e), 400)

    return APIResponse.error("Debe proporcionar email o nombre de usuario", 400)


@bp.route("/<int:lista_id>/permisos/<int:usuario_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_permiso(lista_id, usuario_id):
    """Actualizar nivel de permiso de un usuario."""
    usuario_actual_id = session.get("usuario_id")
    db = get_db()
    datos = request.get_json(force=True) or {}

    # Verificar propietario
    lista = db.execute(
        "SELECT usuario_propietario_id FROM listas WHERE id = ?",
        (lista_id,)
    ).fetchone()

    if not lista or lista["usuario_propietario_id"] != usuario_actual_id:
        return APIResponse.no_permitido()

    nivel = Validator.string_opcional(datos.get("nivel"), "editar", 10)
    if nivel not in ["ver", "editar"]:
        return APIResponse.error("Nivel debe ser 'ver' o 'editar'", 400)

    db.execute(
        "UPDATE permisos_lista SET nivel = ? WHERE lista_id = ? AND usuario_id = ?",
        (nivel, lista_id, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Permiso actualizado"})


@bp.route("/<int:lista_id>/permisos/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def revocar_acceso(lista_id, usuario_id):
    """Revocar acceso de un usuario a una lista."""
    usuario_actual_id = session.get("usuario_id")
    db = get_db()

    # Verificar propietario
    lista = db.execute(
        "SELECT usuario_propietario_id FROM listas WHERE id = ?",
        (lista_id,)
    ).fetchone()

    if not lista or lista["usuario_propietario_id"] != usuario_actual_id:
        return APIResponse.no_permitido()

    db.execute(
        "DELETE FROM permisos_lista WHERE lista_id = ? AND usuario_id = ?",
        (lista_id, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Acceso revocado"})
