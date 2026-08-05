"""Rutas para gestionar permisos y compartir hogares."""
import secrets

from flask import Blueprint, request, session
from datetime import datetime, timedelta

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..autorizacion import requerir_hogar
from ..config import APP_URL, LIMITE_INVITACIONES_DIARIO_POR_HOGAR
from ..db import ahora, get_db
from ..red import ip_cliente
from ..servicios import auditoria
from ..utils import Validator
from ..servicios.email_service import EmailService

bp = Blueprint("permisos", __name__, url_prefix="/api/hogares")


@bp.route("/buscar-usuarios", methods=["GET"])
@requerir_sesion
@manejo_errores
def buscar_usuarios():
    """Buscar usuarios para compartir hogares."""
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


@bp.route("/<int:hogar_id>/miembros", methods=["GET"])
@requerir_sesion
@requerir_hogar("propietario")
@manejo_errores
def obtener_miembros(hogar_id):
    """Obtener lista de usuarios con acceso a una lista."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    # Obtener propietario
    propietario = db.execute(
        "SELECT id, nombre_usuario FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    # Obtener miembros con permisos
    miembros_datos = db.execute(
        """SELECT u.id, u.nombre_usuario, u.email, p.nivel, p.fecha_otorgado
           FROM usuarios u
           JOIN permisos_hogar p ON u.id = p.usuario_id
           WHERE p.hogar_id = ?
           ORDER BY p.fecha_otorgado DESC""",
        (hogar_id,)
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


@bp.route("/<int:hogar_id>/compartir", methods=["POST"])
@requerir_sesion
@requerir_hogar("propietario")
@manejo_errores
def compartir_lista(hogar_id):
    """Compartir lista con otro usuario o por email."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    datos = request.get_json(force=True) or {}

    # Obtener email o nombre de usuario destino (acepta "usuario" como alias)
    email_destino = (datos.get("email") or "").strip()
    nombre_usuario_destino = (datos.get("nombre_usuario") or datos.get("usuario") or "").strip()
    nivel = Validator.string_opcional(datos.get("nivel"), "editar", 10)

    if nivel not in ["ver", "editar"]:
        return APIResponse.error("err_nivel_invalido", 400)

    # Cuota de invitaciones por hogar y dia (S-21): cubre ambos caminos (por
    # nombre de usuario y por email), ya que las dos crean una fila en
    # invitaciones_hogar. Protege contra un hogar comprometido usado para
    # espamear invitaciones.
    inicio_de_hoy = datetime.now().date().isoformat()
    invitaciones_hoy = db.execute(
        "SELECT COUNT(*) AS n FROM invitaciones_hogar WHERE hogar_id = ? AND fecha_creacion >= ?",
        (hogar_id, inicio_de_hoy),
    ).fetchone()["n"]
    if invitaciones_hoy >= LIMITE_INVITACIONES_DIARIO_POR_HOGAR:
        return APIResponse.error("err_limite_invitaciones_diario", 429)

    # Si es por nombre de usuario: se crea una invitacion pendiente igual que
    # con email (S-10), en vez de dar acceso INMEDIATO sin que el destinatario
    # acepte nada. Se responde con el MISMO mensaje exista o no ese usuario,
    # para no permitir enumerar nombres de usuario registrados probando uno
    # a uno; solo si existe de verdad se crea la fila en invitaciones_hogar.
    if nombre_usuario_destino:
        respuesta_generica = APIResponse.success({"mensaje": "mensaje_compartir_generico"})

        usuario_destino = db.execute(
            "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)",
            (nombre_usuario_destino,)
        ).fetchone()

        if not usuario_destino:
            return respuesta_generica

        if usuario_destino["id"] == usuario_id:
            return respuesta_generica

        codigo = secrets.token_urlsafe(24)
        fecha_expiracion = (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds")
        db.execute(
            """INSERT INTO invitaciones_hogar
               (hogar_id, email_destino, usuario_destino_id, nivel, codigo_invitacion, fecha_creacion, fecha_expiracion)
               VALUES (?, '', ?, ?, ?, ?, ?)""",
            (hogar_id, usuario_destino["id"], nivel, codigo, ahora(), fecha_expiracion)
        )
        auditoria.registrar(db, "compartir_hogar", usuario_id=usuario_id, ip=ip_cliente(), hogar_id=hogar_id, via="usuario")
        db.commit()
        return respuesta_generica

    # Si es por email, crear invitación
    elif email_destino:
        # token_urlsafe(24) da ~32 caracteres / 192 bits de entropia: el codigo
        # es un bearer token (quien lo tenga entra), no debe ser adivinable.
        codigo = secrets.token_urlsafe(24)
        fecha_expiracion = (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds")

        # Obtener nombre del remitente (propietario de la lista)
        propietario = db.execute(
            "SELECT nombre_usuario FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        nombre_remitente = propietario["nombre_usuario"] if propietario else "Un usuario"

        # Obtener nombre de la lista
        lista = db.execute(
            "SELECT nombre FROM hogares WHERE id = ?",
            (hogar_id,)
        ).fetchone()
        nombre_lista = lista["nombre"] if lista else "Una lista"

        # Crear invitación en BD
        db.execute(
            """INSERT INTO invitaciones_hogar
               (hogar_id, email_destino, nivel, codigo_invitacion, fecha_creacion, fecha_expiracion)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (hogar_id, email_destino, nivel, codigo, ahora(), fecha_expiracion)
        )
        auditoria.registrar(db, "compartir_hogar", usuario_id=usuario_id, ip=ip_cliente(), hogar_id=hogar_id, via="email")
        db.commit()

        # Enviar email de invitación. Cualquier fallo inesperado (BD o envio)
        # lo captura el @manejo_errores del endpoint con un 500 generico, en
        # vez de devolver el texto crudo de la excepcion al cliente.
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

    return APIResponse.error("err_falta_email_o_usuario", 400)


@bp.route("/<int:hogar_id>/permisos/<int:usuario_id>", methods=["PATCH"])
@requerir_sesion
@requerir_hogar("propietario")
@manejo_errores
def actualizar_permiso(hogar_id, usuario_id):
    """Actualizar nivel de permiso de un usuario."""
    usuario_actual_id = session.get("usuario_id")
    db = get_db()
    datos = request.get_json(force=True) or {}

    if usuario_id == usuario_actual_id:
        # El propietario no tiene fila en permisos_hogar (su acceso viene de
        # ser el dueño, no de un permiso); sin este aviso el UPDATE de abajo
        # no afecta a ninguna fila y la peticion "tiene exito" sin haber
        # cambiado nada, dando una falsa sensacion de que se aplico.
        return APIResponse.error("err_no_cambiar_permiso_propietario", 400)

    nivel = Validator.string_opcional(datos.get("nivel"), "editar", 10)
    if nivel not in ["ver", "editar"]:
        return APIResponse.error("err_nivel_invalido", 400)

    db.execute(
        "UPDATE permisos_hogar SET nivel = ? WHERE hogar_id = ? AND usuario_id = ?",
        (nivel, hogar_id, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Permiso actualizado"})


@bp.route("/<int:hogar_id>/permisos/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@requerir_hogar("propietario")
@manejo_errores
def revocar_acceso(hogar_id, usuario_id):
    """Revocar acceso de un usuario a una lista."""
    usuario_actual_id = session.get("usuario_id")
    db = get_db()

    if usuario_id == usuario_actual_id:
        return APIResponse.error("err_no_revocar_acceso_propietario", 400)

    db.execute(
        "DELETE FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
        (hogar_id, usuario_id)
    )
    db.commit()

    return APIResponse.success({"mensaje": "Acceso revocado"})


@bp.route("/<int:hogar_id>/enlace-compartible", methods=["POST"])
@requerir_sesion
@requerir_hogar("propietario")
@manejo_errores
def generar_enlace_compartible(hogar_id):
    """Generar un enlace compartible para una lista."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    lista = db.execute(
        "SELECT nombre FROM hogares WHERE id = ?",
        (hogar_id,)
    ).fetchone()

    # Generar código
    codigo = secrets.token_urlsafe(24)
    fecha_expiracion = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")

    # Guardar invitación (sin email destino = enlace público)
    db.execute(
        """INSERT INTO invitaciones_hogar
           (hogar_id, email_destino, nivel, codigo_invitacion, fecha_creacion, fecha_expiracion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (hogar_id, "", "editar", codigo, ahora(), fecha_expiracion)
    )
    db.commit()

    # Construir URL del enlace (APP_URL, no request.host_url: detras de
    # proxy/Docker el host de la peticion no es el dominio publico)
    url_base = APP_URL.rstrip("/")
    url_compartible = f"{url_base}/aceptar-invitacion/{codigo}"

    return APIResponse.success({
        "codigo": codigo,
        "url": url_compartible,
        "nombre_lista": lista["nombre"]
    })


@bp.route("/aceptar-invitacion/<codigo>", methods=["POST"])
@requerir_sesion
@manejo_errores
def aceptar_invitacion(codigo):
    """Aceptar una invitación de lista compartida."""
    usuario_id = session.get("usuario_id")
    db = get_db()

    # Buscar invitación
    invitacion = db.execute(
        "SELECT * FROM invitaciones_hogar WHERE codigo_invitacion = ?",
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

    # Si la invitacion iba dirigida a un usuario concreto (compartir por
    # nombre de usuario, S-10), solo ese usuario puede aceptarla - evita que
    # el codigo, si se filtrase, lo use cualquiera en nombre de otro.
    destino_id = invitacion["usuario_destino_id"]
    if destino_id is not None and destino_id != usuario_id:
        return APIResponse.no_permitido()

    # Agregar permiso. Cualquier fallo inesperado lo captura el
    # @manejo_errores del endpoint con un 500 generico, en vez de devolver el
    # texto crudo de la excepcion al cliente.
    db.execute(
        """INSERT INTO permisos_hogar
           (hogar_id, usuario_id, nivel, fecha_otorgado)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(hogar_id, usuario_id) DO UPDATE SET
               nivel = excluded.nivel, fecha_otorgado = excluded.fecha_otorgado""",
        (invitacion["hogar_id"], usuario_id, invitacion["nivel"], ahora())
    )

    # Marcar invitación como usada
    db.execute(
        """UPDATE invitaciones_hogar
           SET usado = 1, usuario_aceptacion_id = ?, fecha_aceptacion = ?
           WHERE id = ?""",
        (usuario_id, ahora(), invitacion["id"])
    )

    db.commit()

    session["hogar_actual_id"] = invitacion["hogar_id"]

    return APIResponse.success({"mensaje": "¡Invitación aceptada!", "hogar_id": invitacion["hogar_id"]})


@bp.route("/invitaciones-pendientes", methods=["GET"])
@requerir_sesion
@manejo_errores
def invitaciones_pendientes():
    """Invitaciones a hogares dirigidas al usuario autenticado (S-10): las
    creadas al compartir por nombre de usuario, aun no aceptadas/rechazadas
    ni caducadas."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    filas = db.execute(
        """SELECT i.id, i.codigo_invitacion, i.nivel, i.fecha_expiracion,
                  h.nombre AS nombre_hogar, u.nombre_usuario AS nombre_propietario
           FROM invitaciones_hogar i
           JOIN hogares h ON h.id = i.hogar_id
           JOIN usuarios u ON u.id = h.usuario_propietario_id
           WHERE i.usuario_destino_id = ? AND i.usado = 0 AND i.fecha_expiracion >= ?
           ORDER BY i.fecha_creacion DESC""",
        (usuario_id, ahora()),
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])


@bp.route("/invitaciones-pendientes/<codigo>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def rechazar_invitacion(codigo):
    """Rechaza (marca como usada, sin conceder permiso) una invitación
    dirigida al usuario autenticado."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    invitacion = db.execute(
        "SELECT id FROM invitaciones_hogar WHERE codigo_invitacion = ? AND usuario_destino_id = ? AND usado = 0",
        (codigo, usuario_id),
    ).fetchone()
    if not invitacion:
        return APIResponse.no_encontrado("recurso_invitacion")

    db.execute("UPDATE invitaciones_hogar SET usado = 1 WHERE id = ?", (invitacion["id"],))
    db.commit()
    return APIResponse.success({"mensaje": "invitacion_rechazada_ok"})
