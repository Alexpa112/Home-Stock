"""Límite de intentos fallidos de login, persistido en SQLite (tabla
intentos_login, ver stockhogar/db.py).

Antes era un diccionario en memoria del proceso: con gunicorn --workers 2
(procesos separados, ver Dockerfile.raspbian) cada worker tenia su propio
contador. Ahora se persiste y se comprueban TRES cubos independientes; basta
con que CUALQUIERA supere su umbral para bloquear:

  - por IP: protege contra una IP que prueba muchas cuentas distintas.
  - por IP+cuenta: acota los intentos de una IP concreta sobre una cuenta.
  - por cuenta: protege UNA cuenta atacada desde MUCHAS IPs distintas.

El tercero se añadio tras una auditoria: el cubo "por IP+cuenta" lleva la IP
en la clave, asi que NO protegia lo que su comentario decia proteger. Quien
pudiera variar la IP percibida -una lista de proxies, o falseando
CF-Connecting-IP desde la red local contra el proxy del frontend- tenia
intentos ILIMITADOS contra una sola cuenta: cada intento caia en un cubo
nuevo y ninguno llegaba al tope.

MAX_INTENTOS_CUENTA es deliberadamente mas alto que MAX_INTENTOS: un cubo por
cuenta sin IP lo puede llenar un tercero a proposito para dejar fuera al dueño
(denegacion de servicio contra una cuenta concreta). Con 20 en 10 minutos, un
usuario normal que se equivoca no lo alcanza nunca, y la fuerza bruta queda
acotada a 20 intentos por ventana en vez de infinitos.
"""
import time

from ..db import get_db

MAX_INTENTOS = 5
# Ver la explicacion del docstring: mas alto a proposito, para que llenarlo no
# sirva como forma de bloquear la cuenta de otro.
MAX_INTENTOS_CUENTA = 20
VENTANA_SEGUNDOS = 10 * 60


def _normalizar_cuenta(cuenta):
    return cuenta.strip().lower() if cuenta else None


def _clave_cuenta(ip, cuenta):
    normalizada = _normalizar_cuenta(cuenta)
    return f"{ip}:{normalizada}" if normalizada else None


def _clave_solo_cuenta(cuenta):
    """Cubo por cuenta SIN la IP: el que acota la fuerza bruta distribuida.

    El prefijo evita colisionar con las claves por IP (una cuenta que se
    llamara "127.0.0.1" compartiria cubo con esa IP).
    """
    normalizada = _normalizar_cuenta(cuenta)
    return f"cuenta:{normalizada}" if normalizada else None


def _purgar(db, limite):
    db.execute("DELETE FROM intentos_login WHERE fecha_intento < ?", (limite,))


def _contar(db, clave, limite):
    fila = db.execute(
        "SELECT COUNT(*) AS n FROM intentos_login WHERE clave = ? AND fecha_intento >= ?",
        (clave, limite),
    ).fetchone()
    return fila["n"]


def bloqueada(ip, cuenta=None):
    db = get_db()
    limite = int(time.time()) - VENTANA_SEGUNDOS
    if _contar(db, ip, limite) >= MAX_INTENTOS:
        return True
    clave_cuenta = _clave_cuenta(ip, cuenta)
    if clave_cuenta and _contar(db, clave_cuenta, limite) >= MAX_INTENTOS:
        return True
    clave_solo_cuenta = _clave_solo_cuenta(cuenta)
    if clave_solo_cuenta and _contar(db, clave_solo_cuenta, limite) >= MAX_INTENTOS_CUENTA:
        return True
    return False


def registrar_fallo(ip, cuenta=None):
    db = get_db()
    limite = int(time.time()) - VENTANA_SEGUNDOS
    _purgar(db, limite)
    ahora = int(time.time())
    db.execute("INSERT INTO intentos_login (clave, fecha_intento) VALUES (?, ?)", (ip, ahora))
    clave_cuenta = _clave_cuenta(ip, cuenta)
    if clave_cuenta:
        db.execute("INSERT INTO intentos_login (clave, fecha_intento) VALUES (?, ?)", (clave_cuenta, ahora))
    clave_solo_cuenta = _clave_solo_cuenta(cuenta)
    if clave_solo_cuenta:
        db.execute("INSERT INTO intentos_login (clave, fecha_intento) VALUES (?, ?)", (clave_solo_cuenta, ahora))
    db.commit()


def limpiar_exito(ip, cuenta=None):
    db = get_db()
    limite = int(time.time()) - VENTANA_SEGUNDOS
    _purgar(db, limite)
    db.execute("DELETE FROM intentos_login WHERE clave = ?", (ip,))
    clave_cuenta = _clave_cuenta(ip, cuenta)
    if clave_cuenta:
        db.execute("DELETE FROM intentos_login WHERE clave = ?", (clave_cuenta,))
    clave_solo_cuenta = _clave_solo_cuenta(cuenta)
    if clave_solo_cuenta:
        db.execute("DELETE FROM intentos_login WHERE clave = ?", (clave_solo_cuenta,))
    db.commit()
