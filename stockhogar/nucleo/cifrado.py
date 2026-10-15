"""Cifrado en reposo de los datos sensibles de la base de datos.

Fernet (AES-128-CBC + HMAC-SHA256, con fecha) con claves de `seguridad.py`.
Lo cifrado lleva el prefijo `DRM1:` (texto) o `DRM1\\0` (bytes), asi que:

- Los datos antiguos sin cifrar siguen leyendose (migracion progresiva).
- `cifrar_existentes()` cifra de una vez lo que ya estaba guardado en claro.
- Con una rotacion (`seguridad.rotar_clave_cifrado()`) las claves anteriores
  siguen descifrando y `recifrar_existentes()` pasa todo a la clave nueva.

Protege la base de datos copiada o filtrada sin el fichero `secret.json`
(copias de seguridad, disco extraido). No protege de quien ya controla el
proceso de la aplicacion, que tiene la clave.
"""
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from . import seguridad

logger = logging.getLogger(__name__)

_PREFIJO_TEXTO = "DRM1:"
_PREFIJO_BYTES = b"DRM1\x00"


def _fernet():
    claves = [seguridad.CLAVE_CIFRADO, *seguridad.CLAVES_CIFRADO_PREVIAS]
    return MultiFernet([Fernet(c.encode() if isinstance(c, str) else c) for c in claves])


def esta_cifrado(valor):
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return bytes(valor).startswith(_PREFIJO_BYTES)
    return isinstance(valor, str) and valor.startswith(_PREFIJO_TEXTO)


def cifrar_texto(texto):
    if texto is None or esta_cifrado(texto):
        return texto
    return _PREFIJO_TEXTO + _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def descifrar_texto(valor):
    """Devuelve el texto en claro; lo no cifrado (datos antiguos) se devuelve igual."""
    if not esta_cifrado(valor):
        return valor
    try:
        return _fernet().decrypt(valor[len(_PREFIJO_TEXTO):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("No se pudo descifrar un dato: clave de cifrado distinta a la usada al guardarlo")
        return None


def cifrar_bytes(datos):
    if datos is None or esta_cifrado(datos):
        return datos
    return _PREFIJO_BYTES + _fernet().encrypt(bytes(datos))


def descifrar_bytes(valor):
    if valor is None:
        return None
    valor = bytes(valor)
    if not valor.startswith(_PREFIJO_BYTES):
        return valor
    try:
        return _fernet().decrypt(valor[len(_PREFIJO_BYTES):])
    except InvalidToken:
        logger.error("No se pudo descifrar un fichero: clave de cifrado distinta a la usada al guardarlo")
        return None


def _recorrer(db, recifrar):
    """Cifra (o recifra) recibos y claves push. Devuelve cuantas filas cambio."""
    cambios = 0
    for fila in db.execute("SELECT id, imagen_recibo FROM gastos WHERE imagen_recibo IS NOT NULL").fetchall():
        actual = bytes(fila["imagen_recibo"])
        if esta_cifrado(actual) and not recifrar:
            continue
        claro = descifrar_bytes(actual)
        if claro is None:
            continue
        db.execute("UPDATE gastos SET imagen_recibo = ? WHERE id = ?", (cifrar_bytes(claro), fila["id"]))
        cambios += 1
    for fila in db.execute("SELECT id, p256dh, auth FROM push_subscriptions").fetchall():
        if esta_cifrado(fila["auth"]) and not recifrar:
            continue
        p256dh, auth = descifrar_texto(fila["p256dh"]), descifrar_texto(fila["auth"])
        if p256dh is None or auth is None:
            continue
        db.execute("UPDATE push_subscriptions SET p256dh = ?, auth = ? WHERE id = ?",
                   (cifrar_texto(p256dh), cifrar_texto(auth), fila["id"]))
        cambios += 1
    if cambios:
        db.commit()
    return cambios


def cifrar_existentes(db):
    """Cifra lo que aun este en claro (se llama al arrancar; es idempotente)."""
    return _recorrer(db, recifrar=False)


def recifrar_existentes(db):
    """Tras una rotacion: vuelve a cifrar todo con la clave activa."""
    return _recorrer(db, recifrar=True)
