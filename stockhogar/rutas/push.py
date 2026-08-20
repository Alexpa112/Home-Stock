"""Rutas de notificaciones push del navegador (P-01)."""
from flask import Blueprint, session

from ..api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ..db import ahora, get_db
from ..servicios.push_service import clave_publica_vapid

bp = Blueprint("push", __name__, url_prefix="/api/push")


@bp.route("/vapid-clave-publica", methods=["GET"])
@requerir_sesion
@manejo_errores
def vapid_clave_publica():
    return APIResponse.success({"clave_publica": clave_publica_vapid()})


@bp.route("/suscribir", methods=["POST"])
@requerir_sesion
@manejo_errores
def suscribir():
    """Guarda (o actualiza, si el navegador reenvia el mismo endpoint con
    claves nuevas) la suscripcion push del dispositivo actual."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    endpoint = (datos.get("endpoint") or "").strip()
    claves = datos.get("keys") or {}
    p256dh = (claves.get("p256dh") or "").strip()
    auth = (claves.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth:
        return APIResponse.validacion("err_suscripcion_push_invalida")

    db = get_db()
    db.execute(
        "INSERT INTO push_subscriptions (usuario_id, endpoint, p256dh, auth, fecha_creacion) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(endpoint) DO UPDATE SET usuario_id = excluded.usuario_id, "
        "p256dh = excluded.p256dh, auth = excluded.auth",
        (usuario_id, endpoint, p256dh, auth, ahora()),
    )
    db.commit()
    return APIResponse.success({"suscrito": True})


@bp.route("/desuscribir", methods=["POST"])
@requerir_sesion
@manejo_errores
def desuscribir():
    datos = cuerpo_json()
    endpoint = (datos.get("endpoint") or "").strip()
    if not endpoint:
        return APIResponse.validacion("err_suscripcion_push_invalida")

    db = get_db()
    # Solo el propio usuario puede borrar su suscripcion: el WHERE incluye
    # usuario_id ademas de endpoint, aunque endpoint ya sea UNIQUE, para no
    # depender solo de que el cliente no mande un endpoint ajeno.
    db.execute(
        "DELETE FROM push_subscriptions WHERE endpoint = ? AND usuario_id = ?",
        (endpoint, session.get("usuario_id")),
    )
    db.commit()
    return APIResponse.success({"desuscrito": True})
