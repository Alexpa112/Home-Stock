"""Utilidades de red: IP real del visitante y limitacion de tasa simple.

Cloudflare Tunnel inyecta la cabecera CF-Connecting-IP con la IP publica real
del visitante; si esta presente se prioriza sobre X-Forwarded-For (que solo
refleja el proxy interno de confianza, Next, una vez ProxyFix lo procesa).
"""
import time

from flask import request


def ip_cliente() -> str:
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "desconocida"


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
