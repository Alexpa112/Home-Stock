"""
Clave de sesion de Flask, generada una vez y guardada en `data/secret.json`
(fuera del control de versiones). Si ese fichero se pierde, las sesiones
iniciadas quedan invalidadas, pero las contraseñas de los usuarios (que van
con hash, no cifradas) no se ven afectadas.

Soporta rotacion (S-18): `data/secret.json` guarda la clave activa mas una
lista de claves de verificacion anteriores. Las cookies YA firmadas con una
clave antigua siguen siendo validas mientras esa clave este en la lista
(ver `claves_verificacion_previas` mas abajo y su uso en
`stockhogar/__init__.py::SessionInterfaceOmitible.get_signing_serializer`);
solo la clave activa firma cookies NUEVAS.
"""
import json
import secrets

from .config import CLAVES_PATH

MAX_CLAVES_VERIFICACION = 2


def _migrar_formato_antiguo(claves):
    """Ficheros secret.json de antes de soportar rotacion solo tenian
    "flask_secret_key". Se completan con una lista vacia de claves de
    verificacion, sin tocar la clave activa (ninguna sesion existente se
    invalida por esta migracion)."""
    claves.setdefault("claves_verificacion_previas", [])
    return claves


def _cargar_claves():
    if CLAVES_PATH.exists():
        claves = json.loads(CLAVES_PATH.read_text(encoding="utf-8"))
        return _migrar_formato_antiguo(claves)

    claves = {"flask_secret_key": secrets.token_hex(32), "claves_verificacion_previas": []}
    _guardar(claves)
    return claves


def _guardar(claves):
    CLAVES_PATH.write_text(json.dumps(claves), encoding="utf-8")
    try:
        CLAVES_PATH.chmod(0o600)
    except OSError:
        pass  # No disponible en todos los sistemas de ficheros (p.ej. algunos montajes en Windows).


def rotar_clave():
    """Genera una clave de firma nueva y mueve la actual a la lista de
    verificacion (conservando como maximo MAX_CLAVES_VERIFICACION antiguas,
    para no acumular indefinidamente). Las sesiones firmadas con claves aun
    en esa lista siguen siendo validas; las que ya se hayan descartado
    dejan de aceptarse (mismo efecto que si el fichero se perdiera).

    Uso en una rotacion de emergencia real (p.ej. sospecha de filtracion de
    secret.json): desde un shell de Flask del contenedor,
        >>> from stockhogar import seguridad
        >>> seguridad.rotar_clave()
    y reiniciar el proceso para que gunicorn recargue la clave activa en
    todos los workers (este modulo la lee una sola vez al importarse).
    """
    global _claves, FLASK_SECRET_KEY, CLAVES_VERIFICACION_PREVIAS

    nuevas_previas = [_claves["flask_secret_key"]] + _claves["claves_verificacion_previas"]
    _claves = {
        "flask_secret_key": secrets.token_hex(32),
        "claves_verificacion_previas": nuevas_previas[:MAX_CLAVES_VERIFICACION],
    }
    _guardar(_claves)
    FLASK_SECRET_KEY = _claves["flask_secret_key"]
    CLAVES_VERIFICACION_PREVIAS = _claves["claves_verificacion_previas"]
    return FLASK_SECRET_KEY


_claves = _cargar_claves()
FLASK_SECRET_KEY = _claves["flask_secret_key"]
CLAVES_VERIFICACION_PREVIAS = _claves["claves_verificacion_previas"]
