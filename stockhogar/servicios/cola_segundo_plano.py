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
import time

logger = logging.getLogger(__name__)

TAMANO_MAXIMO = 200


class ColaSegundoPlano:
    def __init__(self, tamano_maximo=TAMANO_MAXIMO, nombre_hilo="trabajos-segundo-plano"):
        self.tamano_maximo = tamano_maximo
        self._nombre_hilo = nombre_hilo
        self._cola = queue.Queue(maxsize=tamano_maximo)
        self._hilo = None
        self._candado = threading.Lock()

    def _consumir(self):
        while True:
            trabajo, nombre = self._cola.get()
            try:
                trabajo()
            except Exception:
                logger.exception("Error en el trabajo en segundo plano %s", nombre)
            finally:
                self._cola.task_done()

    def encolar(self, trabajo, nombre="trabajo"):
        """Pone `trabajo` (un callable sin argumentos) en la cola. Devuelve False si estaba llena
        y se descarto."""
        with self._candado:
            if self._hilo is None or not self._hilo.is_alive():
                self._hilo = threading.Thread(target=self._consumir, name=self._nombre_hilo, daemon=True)
                self._hilo.start()
        try:
            self._cola.put_nowait((trabajo, nombre))
            return True
        except queue.Full:
            logger.warning("Cola de segundo plano llena (%d): se descarta %s", self.tamano_maximo, nombre)
            return False

    def esperar_vacia(self, timeout=30):
        """Espera a que se atiendan los trabajos pendientes. Devuelve False si se agoto el tiempo."""
        limite = time.time() + timeout
        while time.time() < limite:
            if self._cola.unfinished_tasks == 0:
                return True
            time.sleep(0.01)
        return self._cola.unfinished_tasks == 0


# Cola compartida del proceso (traducciones de articulos y productos).
cola_por_defecto = ColaSegundoPlano()
encolar = cola_por_defecto.encolar
