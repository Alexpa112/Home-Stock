"""Notificaciones push del navegador (P-01): claves VAPID, envio y limpieza
de suscripciones caducadas.

Las claves VAPID (identifican al SERVIDOR ante los servicios push de cada
navegador, no al usuario) se generan una sola vez y se guardan en
data/vapid_private_key.pem, mismo patron que stockhogar/seguridad.py con la
clave de firma de sesiones: si el fichero se pierde, las suscripciones ya
guardadas dejan de aceptarse (el navegador las verifica contra la clave
publica que tenia al suscribirse) y los usuarios tendrian que reactivar las
notificaciones, pero no se pierde ningun dato de usuario.
"""
import base64
import json
import logging

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from ..config import DATA_DIR, EMAIL_CONTACTO_LEGAL

logger = logging.getLogger(__name__)

_VAPID_KEY_PATH = DATA_DIR / "vapid_private_key.pem"
_vapid = Vapid.from_file(str(_VAPID_KEY_PATH))
try:
    _VAPID_KEY_PATH.chmod(0o600)
except OSError:
    pass  # No disponible en todos los sistemas de ficheros (p.ej. algunos montajes en Windows).


def clave_publica_vapid() -> str:
    """Clave publica VAPID en base64url sin padding, formato que espera
    PushManager.subscribe({applicationServerKey: ...}) en el navegador."""
    pub_bytes = _vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")


def enviar_push(db, suscripcion, titulo, cuerpo, url=None) -> bool:
    """Envia una notificacion a una suscripcion (fila de push_subscriptions
    con endpoint/p256dh/auth). Si el servicio push confirma que la
    suscripcion ya no existe (404/410 - navegador desinstalado, permiso
    revocado...), la borra de la BD para no seguir intentando en vano."""
    try:
        webpush(
            subscription_info={
                "endpoint": suscripcion["endpoint"],
                "keys": {"p256dh": suscripcion["p256dh"], "auth": suscripcion["auth"]},
            },
            data=json.dumps({"titulo": titulo, "cuerpo": cuerpo, "url": url or "/dashboard"}),
            vapid_private_key=_vapid,
            vapid_claims={"sub": f"mailto:{EMAIL_CONTACTO_LEGAL}"},
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):
            db.execute("DELETE FROM push_subscriptions WHERE id = ?", (suscripcion["id"],))
            db.commit()
        else:
            logger.warning("Fallo enviando push a la suscripcion %s: %s", suscripcion["id"], e)
        return False


def enviar_push_a_usuario(db, usuario_id, titulo, cuerpo, url=None) -> int:
    """Envia la notificacion a TODAS las suscripciones del usuario (puede
    tener varios dispositivos). Devuelve cuantas se enviaron con exito."""
    suscripciones = db.execute(
        "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE usuario_id = ?", (usuario_id,)
    ).fetchall()
    return sum(1 for s in suscripciones if enviar_push(db, s, titulo, cuerpo, url))
