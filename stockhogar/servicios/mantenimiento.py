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

_cambio = threading.Condition()
_estado_actual: bool = RUTA_FLAG.exists()


def _vigilar():
    """Hilo daemon que comprueba el flag cada segundo y notifica a todos los
    streams SSE en cuanto detecta un cambio, sin depender de peticiones HTTP."""
    global _estado_actual
    while True:
        time.sleep(1)
        nuevo = RUTA_FLAG.exists()
        if nuevo != _estado_actual:
            _estado_actual = nuevo
            with _cambio:
                _cambio.notify_all()


_hilo = threading.Thread(target=_vigilar, daemon=True, name="mantenimiento-watcher")
_hilo.start()


def activo() -> bool:
    return _estado_actual


def mensaje():
    try:
        return RUTA_FLAG.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def esperar_cambio(timeout_s: float = 55.0) -> bool:
    """Bloquea hasta que el estado de mantenimiento cambie o se agote el timeout.

    Retorna True si hubo cambio, False si fue timeout. Usado por el endpoint SSE.
    """
    with _cambio:
        return _cambio.wait(timeout=timeout_s)
