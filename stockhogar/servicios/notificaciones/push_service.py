"""Notificaciones push del navegador (P-01): claves VAPID, envio y limpieza
de suscripciones caducadas.

Las claves VAPID (identifican al SERVIDOR ante los servicios push de cada
navegador, no al usuario) se generan una sola vez y se guardan en
data/vapid_private_key.pem, mismo patron que stockhogar/nucleo/seguridad.py con la
clave de firma de sesiones: si el fichero se pierde, las suscripciones ya
guardadas dejan de aceptarse (el navegador las verifica contra la clave
publica que tenia al suscribirse) y los usuarios tendrian que reactivar las
notificaciones, pero no se pierde ningun dato de usuario.
"""
import base64
import json
import logging
import os

from cryptography.hazmat.primitives import serialization

try:
    from py_vapid import Vapid
    _VAPID_DISPONIBLE = True
except ImportError:
    _VAPID_DISPONIBLE = False
    Vapid = None

try:
    from pywebpush import WebPushException, webpush
    _WEBPUSH_DISPONIBLE = True
except ImportError:
    _WEBPUSH_DISPONIBLE = False
    WebPushException = Exception
    def webpush(*args, **kwargs):  # Dummy para tests cuando pywebpush no está disponible
        raise WebPushException("pywebpush no disponible")

from ...nucleo import cifrado
from ...config import DATA_DIR, EMAIL_CONTACTO_LEGAL

logger = logging.getLogger(__name__)

_VAPID_KEY_PATH = DATA_DIR / "vapid_private_key.pem"


# Servicios push reales de los navegadores. El endpoint lo manda el cliente y el
# servidor le hace un POST: sin esta lista se podia apuntar a http://127.0.0.1:... o a
# cualquier host interno (SSRF).
_DOMINIOS_PUSH = (
    "fcm.googleapis.com", "android.googleapis.com", "push.apple.com",
    "notify.windows.com", "push.services.mozilla.com", "push.api.mozilla.com",
)


def endpoint_push_permitido(endpoint: str) -> bool:
    from urllib.parse import urlparse
    if not isinstance(endpoint, str) or len(endpoint) > 1000:
        return False
    try:
        partes = urlparse(endpoint)
        host = (partes.hostname or "").lower()
    except ValueError:
        return False
    if partes.scheme != "https" or partes.port not in (None, 443) or partes.username or partes.password:
        return False
    return any(host == d or host.endswith("." + d) for d in _DOMINIOS_PUSH)


def _crear_clave_vapid():
    """Genera el par de claves y lo escribe con O_EXCL y permisos 0600 desde
    el primer byte.

    No se delega en Vapid.save_key (que abre el fichero en modo "wb"): con
    varios workers de gunicorn arrancando a la vez, dos podrian generar claves
    distintas y el ultimo en escribir dejaria invalidas las suscripciones que
    el otro ya hubiera entregado al navegador. Con O_EXCL solo uno crea el
    fichero; el que pierde la carrera recibe FileExistsError y lee la clave
    del ganador. Ademas evita la ventana en la que la clave privada existiria
    con permisos 0644.
    """
    vapid = Vapid()
    vapid.generate_keys()
    try:
        descriptor = os.open(_VAPID_KEY_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return  # Otro worker la creo primero: se usa la suya.
    with os.fdopen(descriptor, "wb") as fichero:
        fichero.write(vapid.private_pem())


def _cargar_o_crear_vapid():
    """Devuelve la Vapid del despliegue, creando la clave la primera vez.

    Antes solo se cargaba `if _VAPID_KEY_PATH.exists()`, y como nada generaba
    el fichero, `_vapid` quedaba en None para siempre: la clave publica que
    pide el navegador se servia vacia y activar las notificaciones era
    imposible en cualquier despliegue nuevo.
    """
    if not _VAPID_KEY_PATH.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _crear_clave_vapid()
    return Vapid.from_file(str(_VAPID_KEY_PATH))


_vapid = None
if _VAPID_DISPONIBLE:
    try:
        _vapid = _cargar_o_crear_vapid()
    except Exception as e:
        logger.warning("No se pudo cargar ni generar la clave VAPID: %s", e)


def clave_publica_vapid() -> str:
    """Clave publica VAPID en base64url sin padding, formato que espera
    PushManager.subscribe({applicationServerKey: ...}) en el navegador."""
    if not _vapid:
        return ""
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
    if not _WEBPUSH_DISPONIBLE or not _vapid:
        logger.warning("Push no disponible, descartando push a %s", suscripcion["id"])
        return False
    if not endpoint_push_permitido(suscripcion["endpoint"]):
        logger.warning("Suscripcion push %s con endpoint no permitido: descartada", suscripcion["id"])
        return False
    try:
        webpush(
            subscription_info={
                "endpoint": suscripcion["endpoint"],
                "keys": {"p256dh": cifrado.descifrar_texto(suscripcion["p256dh"]), "auth": cifrado.descifrar_texto(suscripcion["auth"])},
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
