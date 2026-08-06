"""Límite de intentos fallidos de login, persistido en SQLite (tabla
intentos_login, ver stockhogar/db.py).

Antes era un diccionario en memoria del proceso: con gunicorn --workers 2
(procesos separados, ver Dockerfile.raspbian) cada worker tenia su propio
contador, y el bloqueo era un cubo GLOBAL por IP (protegia la IP pero no una
cuenta atacada desde varias IPs). Ahora se persiste y se comprueban DOS
cubos independientes:
  - por IP: protege contra una IP que prueba muchas cuentas distintas.
  - por IP+cuenta: protege una cuenta contra fuerza bruta desde varias IPs.
Basta con que CUALQUIERA de los dos supere el umbral para bloquear.
"""
import time

from ..db import get_db

MAX_INTENTOS = 5
VENTANA_SEGUNDOS = 10 * 60


def _clave_cuenta(ip, cuenta):
    return f"{ip}:{cuenta.strip().lower()}" if cuenta else None


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
    db.commit()


def limpiar_exito(ip, cuenta=None):
    db = get_db()
    limite = int(time.time()) - VENTANA_SEGUNDOS
    _purgar(db, limite)
    db.execute("DELETE FROM intentos_login WHERE clave = ?", (ip,))
    clave_cuenta = _clave_cuenta(ip, cuenta)
    if clave_cuenta:
        db.execute("DELETE FROM intentos_login WHERE clave = ?", (clave_cuenta,))
    db.commit()
