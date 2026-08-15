"""Utilidades de red: IP real del visitante y limitacion de tasa simple.

Cloudflare Tunnel inyecta la cabecera CF-Connecting-IP con la IP publica real
del visitante; si esta presente se prioriza sobre X-Forwarded-For (que solo
refleja el proxy interno de confianza, Next, una vez ProxyFix lo procesa).

PERO esa cabecera solo vale si la peticion ha llegado de verdad por nuestro
proxy: la manda el cliente como cualquier otra, y antes se aceptaba siempre.
Con eso, TODOS los limites de tasa eran de adorno: bastaba con ir cambiando
CF-Connecting-IP en cada intento para que ni el contador por IP ni el de
ip+cuenta de intentos_login llegasen nunca a su tope, dejando la puerta
abierta a fuerza bruta ilimitada contra cualquier contraseña (y lo mismo con
el reset de contraseña, el 2FA y la cuota de OCR). Ahora solo se hace caso a
la cabecera si el ultimo salto esta en PROXIES_CONFIABLES.
"""
import ipaddress
import time

from flask import request

from .config import PROXIES_CONFIABLES

_REDES_CONFIABLES = []
for _rango in PROXIES_CONFIABLES:
    try:
        _REDES_CONFIABLES.append(ipaddress.ip_network(_rango, strict=False))
    except ValueError:
        # Un rango mal escrito en la config no debe tumbar el arranque: se
        # ignora, que es el lado seguro (deja de confiarse en esa red).
        pass


def _ip_valida(texto: str):
    try:
        return ipaddress.ip_address(texto)
    except ValueError:
        return None


def _viene_de_proxy_confiable(direccion: str) -> bool:
    ip = _ip_valida(direccion)
    if ip is None:
        return False
    return any(ip in red for red in _REDES_CONFIABLES)


def ip_cliente() -> str:
    directa = request.remote_addr or "desconocida"

    cabecera = request.headers.get("CF-Connecting-IP")
    if cabecera and _viene_de_proxy_confiable(directa):
        # Se valida que sea una IP de verdad, no solo que venga rellena: el
        # valor acaba siendo clave del contador de tasa y columna en
        # intentos_login, y una cadena arbitraria (o muy larga) del cliente no
        # tiene por que llegar hasta ahi.
        candidata = cabecera.split(",")[0].strip()
        if _ip_valida(candidata) is not None:
            return candidata

    return directa


# Limite de tasa generico en memoria, purgado en cada llamada de escritura
# (sin cron). Pensado para casos muy permisivos (p.ej. /api/log/client) donde
# no hace falta la persistencia en SQLite de intentos_login.py.
_contadores: dict[str, list[float]] = {}


def limite_por_ip(clave: str, max_por_ventana: int, ventana_segundos: int) -> bool:
    """Registra un uso de `clave` y devuelve True si se ha superado el limite."""
    ahora = time.monotonic()
    limite = ahora - ventana_segundos
    usos = [t for t in _contadores.get(clave, []) if t > limite]
    usos.append(ahora)
    _contadores[clave] = usos
    return len(usos) > max_por_ventana
