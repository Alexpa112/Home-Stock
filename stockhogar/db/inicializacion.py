"""Arranque de la base de datos: crea el esquema y aplica las migraciones, una sola vez a la vez."""
import sqlite3

from .. import config
from .esquema import crear_esquema
from .migraciones import aislar_catalogos_por_hogar, reparar_fk_articulos_personalizados_old

try:
    import fcntl  # No disponible en Windows; solo se usa en el contenedor Linux.
except ImportError:
    fcntl = None


def init_db():
    """Ejecuta las migraciones protegidas por un flock sobre un fichero aparte.

    gunicorn arranca --workers 2 (procesos separados, ver el CMD de
    Dockerfile.raspbian) y cada uno llama a create_app() -> init_db() al
    bootear. Sin este lock, los dos ejecutan las mismas sentencias
    'ALTER TABLE ... ADD COLUMN' casi a la vez contra el mismo fichero
    SQLite; aunque hay un PRAGMA busy_timeout, se ha visto en produccion
    (2026-07-29) que la sucesion de varias ALTER TABLE seguidas puede agotar
    igualmente el timeout con "database is locked", tumbando el worker y
    disparando el rollback automatico del deploy. Con el flock, el segundo
    worker simplemente espera a que el primero termine las migraciones antes
    de arrancar las suyas (que entonces son no-ops, las columnas ya existen).
    """
    if fcntl is None:
        _init_db_impl()
        return
    lock_path = config.DB_PATH.parent / ".init_db.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            _init_db_impl()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)



def _init_db_impl():
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 5000")
    # Si una migracion falla a mitad (p.ej. contencion transitoria bajo
    # tests que comparten el mismo fichero SQLite), el try/finally
    # garantiza que esta conexion se cierra igualmente: sin esto, una
    # unica fila fallida dejaba la conexion abierta para siempre,
    # bloqueando con "database is locked" TODAS las llamadas
    # posteriores a init_db() (cada test que llama a create_app()).
    try:
        reparar_fk_articulos_personalizados_old(db)
        crear_esquema(db)
        db.commit()

        # "Espacios" (stocks independientes tipo casa/oficina) se eliminó: nunca tuvo UI y
        # su función de aislamiento ya la cubren las "listas". Se borra la tabla una vez
        # migrados los datos que dependían de ella (productos, historial_articulos,
        # articulos_personalizados, más arriba).
        db.execute("DROP TABLE IF EXISTS espacios")

        aislar_catalogos_por_hogar(db)
        db.commit()
    finally:
        db.close()
