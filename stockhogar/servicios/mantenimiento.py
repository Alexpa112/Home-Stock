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

from ..config import DATA_DIR

RUTA_FLAG = DATA_DIR / "mantenimiento.flag"

# activo() se llama en el before_request de CADA peticion no estatica (ver
# stockhogar/__init__.py): sin cachear, es un stat() de disco sincrono por
# peticion aunque el flag solo lo cambie un proceso externo (el Panel de
# Gestion) muy de vez en cuando. Con este TTL, a lo sumo se tarda
# TTL_CACHE_SEGUNDOS en reaccionar a un cambio real, lo cual es aceptable
# para una pantalla de mantenimiento (no es una comprobacion de seguridad
# que deba ser instantanea).
TTL_CACHE_SEGUNDOS = 3
_cache = {"valor": None, "expira": 0.0}


def activo():
    ahora = time.monotonic()
    if _cache["valor"] is None or ahora >= _cache["expira"]:
        _cache["valor"] = RUTA_FLAG.exists()
        _cache["expira"] = ahora + TTL_CACHE_SEGUNDOS
    return _cache["valor"]


def mensaje():
    try:
        return RUTA_FLAG.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
