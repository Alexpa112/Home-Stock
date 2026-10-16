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
import os
import secrets

from cryptography.fernet import Fernet

from ..config import CLAVES_PATH

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

MAX_CLAVES_VERIFICACION = 2


def _migrar_formato_antiguo(claves):
    """Ficheros secret.json de antes de soportar rotacion solo tenian
    "flask_secret_key". Se completan con una lista vacia de claves de
    verificacion, sin tocar la clave activa (ninguna sesion existente se
    invalida por esta migracion)."""
    claves.setdefault("claves_verificacion_previas", [])
    return claves


def _cargar_claves():
    """Con flock: gunicorn arranca varios workers a la vez y, en el primer
    arranque, todos veian que no habia secret.json y lo creaban con claves
    distintas (o se pisaban el .tmp y el worker caia al arrancar)."""
    if fcntl is None:
        return _cargar_claves_impl()
    CLAVES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAVES_PATH.with_name(".secret.lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            return _cargar_claves_impl()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _cargar_claves_impl():
    if CLAVES_PATH.exists():
        claves = _migrar_formato_antiguo(json.loads(CLAVES_PATH.read_text(encoding="utf-8")))
        # Instalaciones anteriores al cifrado en reposo: se crea su clave sin tocar la de sesion.
        if "cifrado_clave" not in claves:
            claves["cifrado_clave"] = Fernet.generate_key().decode()
            claves["cifrado_claves_previas"] = []
            _guardar(claves)
        return claves

    claves = {
        "flask_secret_key": secrets.token_hex(32),
        "claves_verificacion_previas": [],
        "cifrado_clave": Fernet.generate_key().decode(),
        "cifrado_claves_previas": [],
    }
    _guardar(claves)
    return claves


def _guardar(claves):
    """Escritura atomica con permisos 0600 desde el primer byte (con write_text +
    chmod el fichero existia unos instantes legible por otros usuarios)."""
    temporal = CLAVES_PATH.with_name(CLAVES_PATH.name + ".tmp")
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(claves, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, CLAVES_PATH)
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
        >>> from stockhogar.nucleo import seguridad
        >>> seguridad.rotar_clave()
    y reiniciar el proceso para que gunicorn recargue la clave activa en
    todos los workers (este modulo la lee una sola vez al importarse).
    """
    global _claves, FLASK_SECRET_KEY, CLAVES_VERIFICACION_PREVIAS

    nuevas_previas = [_claves["flask_secret_key"]] + _claves["claves_verificacion_previas"]
    _claves = {
        **_claves,  # conserva las claves de cifrado en reposo
        "flask_secret_key": secrets.token_hex(32),
        "claves_verificacion_previas": nuevas_previas[:MAX_CLAVES_VERIFICACION],
    }
    _guardar(_claves)
    FLASK_SECRET_KEY = _claves["flask_secret_key"]
    CLAVES_VERIFICACION_PREVIAS = _claves["claves_verificacion_previas"]
    return FLASK_SECRET_KEY


_claves = _cargar_claves()
# Las variables de entorno mandan sobre el fichero: permiten guardar los secretos
# fuera del disco de datos (gestor de secretos, Docker secrets).
FLASK_SECRET_KEY = os.getenv("DREAME_SECRET_KEY") or _claves["flask_secret_key"]
CLAVES_VERIFICACION_PREVIAS = _claves["claves_verificacion_previas"]
CLAVE_CIFRADO = os.getenv("DREAME_CIFRADO_KEY") or _claves["cifrado_clave"]
CLAVES_CIFRADO_PREVIAS = _claves.get("cifrado_claves_previas", [])


def rotar_clave_cifrado():
    """Nueva clave de cifrado en reposo; la actual pasa a la lista de descifrado.
    Despues hay que llamar a cifrado.recifrar_existentes() para que los datos
    ya guardados pasen a la clave nueva."""
    global CLAVE_CIFRADO, CLAVES_CIFRADO_PREVIAS
    previas = [_claves["cifrado_clave"]] + _claves.get("cifrado_claves_previas", [])
    _claves["cifrado_clave"] = Fernet.generate_key().decode()
    _claves["cifrado_claves_previas"] = previas[:MAX_CLAVES_VERIFICACION]
    _guardar(_claves)
    CLAVE_CIFRADO = _claves["cifrado_clave"]
    CLAVES_CIFRADO_PREVIAS = _claves["cifrado_claves_previas"]
    return CLAVE_CIFRADO
