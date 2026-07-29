"""Límite de intentos fallidos de login, en memoria del proceso (sin nueva
dependencia ni persistencia en disco - si el proceso se reinicia, los
contadores se pierden, lo cual es aceptable para este caso de uso).

Mismo patrón que StockHogar-Panel/panel_servidor/intentos_login.py.
Bloquea una IP tras MAX_INTENTOS fallos dentro de VENTANA_SEGUNDOS.

OJO multi-worker: gunicorn corre esta app con --workers 2 (ver el CMD de
Dockerfile.raspbian), procesos separados que NO comparten memoria. Los
contadores de este modulo son por-proceso, asi que en el peor caso un
atacante tiene efectivamente MAX_INTENTOS * num_workers intentos antes de
que TODOS los workers lo bloqueen. Sigue siendo una mitigacion real (pasa
de "sin limite" a "limite acotado"), pero no es un limite exacto entre
procesos; si hiciera falta exactitud habria que moverlo a la base de datos.
"""
import time

MAX_INTENTOS = 5
VENTANA_SEGUNDOS = 10 * 60

_fallos_por_ip = {}


def _limpiar(ip):
    limite = time.monotonic() - VENTANA_SEGUNDOS
    fallos = [t for t in _fallos_por_ip.get(ip, []) if t > limite]
    if fallos:
        _fallos_por_ip[ip] = fallos
    else:
        _fallos_por_ip.pop(ip, None)
    return fallos


def bloqueada(ip):
    return len(_limpiar(ip)) >= MAX_INTENTOS


def registrar_fallo(ip):
    fallos = _limpiar(ip)
    fallos.append(time.monotonic())
    _fallos_por_ip[ip] = fallos


def limpiar_exito(ip):
    _fallos_por_ip.pop(ip, None)
