"""Limite de tasa generico persistido en SQLite, para contadores por IP que
necesitan sobrevivir a varios workers de gunicorn (a diferencia de
red.limite_por_ip, que es en memoria del proceso y pensado solo para casos
muy permisivos donde la exactitud entre workers no importa, p.ej.
/api/log/client).

Reutiliza la misma tabla que servicios/cuenta/intentos_login.py
(intentos_login: clave, fecha_intento), con el mismo razonamiento: un dict en
memoria deja el contador visible solo para el worker que registro el intento,
asi que con --workers 2 el limite real es hasta 2x el nominal. Cada uso debe
llevar su propio prefijo en la clave para no colisionar con las claves de
login (ip pelada, "ip:cuenta", "cuenta:cuenta") ni entre si.
"""
import time

from ..db import get_db


def superado(clave: str, max_por_ventana: int, ventana_segundos: int) -> bool:
    """Registra un uso de `clave` y devuelve True si con este ya se ha
    superado el limite (mismo contrato que red.limite_por_ip)."""
    db = get_db()
    limite = int(time.time()) - ventana_segundos
    db.execute("DELETE FROM intentos_login WHERE clave = ? AND fecha_intento < ?", (clave, limite))
    ahora = int(time.time())
    db.execute("INSERT INTO intentos_login (clave, fecha_intento) VALUES (?, ?)", (clave, ahora))
    db.commit()
    fila = db.execute(
        "SELECT COUNT(*) AS n FROM intentos_login WHERE clave = ? AND fecha_intento >= ?",
        (clave, limite),
    ).fetchone()
    return fila["n"] > max_por_ventana
