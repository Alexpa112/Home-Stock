"""Cola de trabajos opcionales en segundo plano, con UN solo hilo consumidor.

Traducir un articulo (inferencia neuronal de Argos) tarda segundos y carga un modelo. Antes cada
articulo lanzaba su propio hilo: un CSV de 500 filas creaba 500 hilos que cargaban el modelo a la
vez y tumbaban una Raspberry Pi. Ahora los trabajos hacen cola y se atienden de uno en uno.

La cola esta acotada: son trabajos opcionales (una traduccion que no llega se hace la proxima
vez que se guarde el articulo), asi que si se llena se descarta lo nuevo en vez de acumular
memoria sin limite.
"""
import logging
import queue
import threading

logger = logging.getLogger(__name__)

TAMANO_MAXIMO = 200

_cola = queue.Queue(maxsize=TAMANO_MAXIMO)
_hilo = None
_candado = threading.Lock()


def _consumir():
    while True:
        trabajo, nombre = _cola.get()
        try:
            trabajo()
        except Exception:
            logger.exception("Error en el trabajo en segundo plano %s", nombre)
        finally:
            _cola.task_done()


def encolar(trabajo, nombre="trabajo"):
    """Pone `trabajo` (un callable sin argumentos) en la cola. Devuelve False si estaba llena
    y se descarto."""
    global _hilo
    with _candado:
        if _hilo is None or not _hilo.is_alive():
            _hilo = threading.Thread(target=_consumir, name="trabajos-segundo-plano", daemon=True)
            _hilo.start()
    try:
        _cola.put_nowait((trabajo, nombre))
        return True
    except queue.Full:
        logger.warning("Cola de segundo plano llena (%d): se descarta %s", TAMANO_MAXIMO, nombre)
        return False


def esperar_vacia(timeout=None):
    """Solo para tests: espera a que se atiendan los trabajos pendientes."""
    _cola.join() if timeout is None else _esperar_con_limite(timeout)


def _esperar_con_limite(timeout):
    import time
    limite = time.time() + timeout
    while time.time() < limite and _cola.unfinished_tasks:
        time.sleep(0.01)
