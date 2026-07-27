"""Modo mantenimiento: bloquea el uso normal de la app y muestra un aviso a
los usuarios mientras se hacen cambios o backups.

Se controla con un fichero flag en disco (no en la base de datos) para que
sea instantaneo, no dependa de que la BD este disponible, y sobreviva a un
reinicio del proceso si se reinicia con el mantenimiento aun activo.

Esta app solo LEE el flag. Quien lo activa/desactiva es el Panel de Gestion
del Servidor (proyecto independiente, fuera de este repositorio), escribiendo
o borrando el mismo fichero directamente - no hay ninguna llamada de codigo
entre ambos proyectos.
"""
import time
import threading

from ..config import DATA_DIR

RUTA_FLAG = DATA_DIR / "mantenimiento.flag"

TTL_CACHE_SEGUNDOS = 3
_cache = {"valor": None, "expira": 0.0}

# Condición para notificar a los streams SSE en cuanto cambie el estado.
_cambio = threading.Condition()


def activo():
    ahora = time.monotonic()
    if _cache["valor"] is None or ahora >= _cache["expira"]:
        nuevo = RUTA_FLAG.exists()
        if nuevo != _cache["valor"] and _cache["valor"] is not None:
            # El estado cambió: despertar a todos los streams SSE suscritos.
            with _cambio:
                _cambio.notify_all()
        _cache["valor"] = nuevo
        _cache["expira"] = ahora + TTL_CACHE_SEGUNDOS
    return _cache["valor"]


def mensaje():
    try:
        return RUTA_FLAG.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def esperar_cambio(timeout_s: float = 55.0) -> bool:
    """Bloquea hasta que el estado de mantenimiento cambie o se agote el timeout.

    Retorna True si hubo cambio, False si fue timeout. Usado por el endpoint SSE
    para mantener la conexión abierta y empujar el evento al instante.
    """
    with _cambio:
        return _cambio.wait(timeout=timeout_s)
