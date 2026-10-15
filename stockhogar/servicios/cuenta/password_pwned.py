"""Comprobacion de contraseñas filtradas contra Have I Been Pwned (S-20), via
su API de k-anonymity: solo se envian los primeros 5 caracteres del hash
SHA-1 de la contraseña, nunca la contraseña ni el hash completo.
"""
import hashlib
import logging

import requests

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.pwnedpasswords.com/range/{prefijo}"
_TIMEOUT_SEGUNDOS = 2.5


def es_password_filtrada(password: str) -> bool:
    """True si la contraseña aparece en HIBP. Si la API falla, no hay red o
    hay timeout, devuelve False: un problema de un servicio de terceros no
    debe impedir que un usuario se registre o restablezca su contraseña."""
    try:
        hash_sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # nosec: SHA1 para HIBP k-anonymity API, no para almacenamiento
        prefijo, sufijo = hash_sha1[:5], hash_sha1[5:]
        respuesta = requests.get(_ENDPOINT.format(prefijo=prefijo), timeout=_TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        return any(linea.split(":")[0] == sufijo for linea in respuesta.text.splitlines())
    except Exception:
        logger.warning("No se pudo comprobar la contraseña contra HIBP (se permite igualmente)", exc_info=True)
        return False
