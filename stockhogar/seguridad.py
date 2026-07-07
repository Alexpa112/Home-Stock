"""
Clave de sesion de Flask, generada una vez y guardada en `data/secret.json`
(fuera del control de versiones). Si ese fichero se pierde, las sesiones
iniciadas quedan invalidadas, pero las contraseñas de los usuarios (que van
con hash, no cifradas) no se ven afectadas.
"""
import json
import secrets

from .config import CLAVES_PATH


def _cargar_claves():
    if CLAVES_PATH.exists():
        return json.loads(CLAVES_PATH.read_text(encoding="utf-8"))

    claves = {"flask_secret_key": secrets.token_hex(32)}
    CLAVES_PATH.write_text(json.dumps(claves), encoding="utf-8")
    try:
        CLAVES_PATH.chmod(0o600)
    except OSError:
        pass  # No disponible en todos los sistemas de ficheros (p.ej. algunos montajes en Windows).
    return claves


_claves = _cargar_claves()
FLASK_SECRET_KEY = _claves["flask_secret_key"]
