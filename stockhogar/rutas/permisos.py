"""Rutas para gestionar permisos y compartir listas."""
import secrets

from flask import Blueprint, request, session
from datetime import datetime, timedelta

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..translator import traducir
from ..utils import Validator
from ..servicios.email_service import EmailService

bp = Blueprint("permisos", __name__, url_prefix="/api/listas")


@bp.route("/buscar-usuarios", methods=["GET"])
@requerir_sesion
@manejo_errores
def buscar_usuarios():
    """Buscar usuarios para compartir listas."""
    usuario_id = session.get("usuario_id")
    query = request.args.get("q", "").strip()

    if not query or len(query) < 2:
        return APIResponse.error("err_min_2_caracteres", 400)

    db = get_db()

    # Buscar usuarios por nombre_usuario o email
    usuarios = db.execute(
        """SELECT id, nombre_usuario, email
           FROM usuarios
           WHERE (nombre_usuario LIKE ? OR email LIKE ?)
           AND id != ?
           LIMIT 10""",
        (f"%{query}%", f"%{query}%", usuario_id)
    ).fetchall()

    return APIResponse.success({
        "usuarios": [
            {
                "id": u["id"],
                "nombre_usuario": u["nombre_usuario"],
                "email": u["email"]
            } for u in usuarios
        ]
    })


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

    # Obtener email o nombre de usuario destino (acepta "usuario" como alias)
    email_destino = (datos.get("email") or "").strip()
    nombre_usuario_destino = (datos.get("nombre_usuario") or datos.get("usuario") or "").strip()
    nivel = Validator.string_opcional(datos.get("nivel"), "editar", 10)

    if nivel not in ["ver", "editar"]:
        return APIResponse.error("err_nivel_invalido", 400)

    # Si es por nombre de usuario
    if nombre_usuario_destino:
        usuario_destino = db.execute(
            "SELECT id FROM usuarios WHERE nombre_usuario = ?",
            (nombre_usuario_destino,)
        ).fetchone()

        if not usuario_destino:
            return APIResponse.error("err_usuario_no_encontrado", 404)

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
        # token_urlsafe(24) da ~32 caracteres / 192 bits de entropia: el codigo
        # es un bearer token (quien lo tenga entra), no debe ser adivinable.
        codigo = secrets.token_urlsafe(24)
        fecha_expiracion = (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds")

        try:
            # Obtener nombre del remitente (propietario de la lista)
            propietario = db.execute(
                "SELECT nombre_usuario FROM usuarios WHERE id = ?",
                (usuario_id,)
            ).fetchone()
            nombre_remitente = propietario["nombre_usuario"] if propietario else "Un usuario"

            # Obtener nombre de la lista
            lista = db.execute(
                "SELECT nombre FROM listas WHERE id = ?",
                (lista_id,)
            ).fetchone()
            nombre_lista = lista["nombre"] if lista else "Una lista"

            # Crear invitación en BD
            db.execute(
                """INSERT INTO invitaciones_lista
                   (lista_id, email_destino, nivel, codigo_invitacion, fecha_creacion, fecha_expiracion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (lista_id, email_destino, nivel, codigo, ahora(), fecha_expiracion)
            )
            db.commit()

            # Enviar email de invitación
            email_enviado = EmailService.enviar_invitacion_lista(
                email_destino=email_destino,
                nombre_lista=nombre_lista,
                nombre_remitente=nombre_remitente,
                codigo_invitacion=codigo,
                nivel=nivel
            )

            return APIResponse.success({
                "mensaje": "Invitación enviada" if email_enviado else "Invitación creada (email no enviado)",
                "codigo": codigo,
                "email_enviado": email_enviado
            })
        except Exception as e:
            return APIResponse.error(str(e), 400)

    return APIResponse.error("err_falta_email_o_usuario", 400)


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
        return APIResponse.error("err_nivel_invalido", 400)

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


@bp.route("/aceptar-invitacion/<codigo>", methods=["POST"])
@requerir_sesion
@manejo_errores
def aceptar_invitacion(codigo):
    """Aceptar una invitación de lista compartida."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    # Buscar invitación
    invitacion = db.execute(
        "SELECT * FROM invitaciones_lista WHERE codigo_invitacion = ?",
        (codigo,)
    ).fetchone()

    if not invitacion:
        return APIResponse.error("err_invitacion_no_encontrada", 404)

    # Verificar que no ha sido usada
    if invitacion["usado"]:
        return APIResponse.error("err_invitacion_usada", 400)

    # Verificar que no ha expirado
    fecha_expiracion = datetime.fromisoformat(invitacion["fecha_expiracion"])
    if datetime.now() > fecha_expiracion:
        return APIResponse.error("err_invitacion_expirada", 400)

    try:
        # Agregar permiso
        db.execute(
            """INSERT OR REPLACE INTO permisos_lista
               (lista_id, usuario_id, nivel, fecha_otorgado)
               VALUES (?, ?, ?, ?)""",
            (invitacion["lista_id"], usuario_id, invitacion["nivel"], ahora())
        )

        # Marcar invitación como usada
        db.execute(
            """UPDATE invitaciones_lista
               SET usado = 1, usuario_aceptacion_id = ?, fecha_aceptacion = ?
               WHERE id = ?""",
            (usuario_id, ahora(), invitacion["id"])
        )

        db.commit()

        return APIResponse.success({"mensaje": "¡Invitación aceptada!", "lista_id": invitacion["lista_id"]})
    except Exception as e:
        return APIResponse.error(traducir("err_aceptar_invitacion_generico").replace("{error}", str(e)), 400)
