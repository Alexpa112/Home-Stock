import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _base_de_datos_aislada():
    """Aparta la suite de data/stock.db, la BD real de desarrollo.

    Hasta ahora todos los tests escribían en la misma base de datos que usa la
    app, en contra de la REGLA 10 del CLAUDE.md. Eso tenía tres consecuencias:

    * Los tests ensuciaban datos reales (usuarios, hogares y artículos de
      prueba quedaban mezclados con los de verdad si un tearDown fallaba).
    * Dos procesos contra el mismo fichero SQLite se bloqueaban entre sí:
      "database is locked" al lanzar la suite mientras la app estaba
      levantada, y errores intermitentes al ejecutar dos suites a la vez.
    * La suite no se podía paralelizar.

    Se parchea `stockhogar.db.DB_PATH` (no la de config) porque db.py la
    importa por nombre, así que el binding que cuenta es el de ese módulo. Se
    resuelve en cada llamada a get_db()/_init_db_impl(), de modo que basta con
    sustituir el atributo antes del primer test.

    Es de ámbito de sesión: init_db() siembra el catálogo estándar (cientos de
    artículos) y hacerlo por test multiplicaría el tiempo de la suite.
    """
    import stockhogar.config as config
    import stockhogar.db as db_modulo

    directorio = Path(tempfile.mkdtemp(prefix="stockhogar-tests-"))
    ruta_bd = directorio / "stock.db"

    originales = {
        "db.DB_PATH": db_modulo.DB_PATH,
        "config.DB_PATH": config.DB_PATH,
        "config.DATA_DIR": config.DATA_DIR,
    }
    db_modulo.DB_PATH = ruta_bd
    config.DB_PATH = ruta_bd
    config.DATA_DIR = directorio

    try:
        yield ruta_bd
    finally:
        db_modulo.DB_PATH = originales["db.DB_PATH"]
        config.DB_PATH = originales["config.DB_PATH"]
        config.DATA_DIR = originales["config.DATA_DIR"]
        shutil.rmtree(directorio, ignore_errors=True)


@pytest.fixture(autouse=True)
def _sin_verificacion_real_de_contrasenas_filtradas(monkeypatch):
    """Evita llamadas de red reales a la API de Have I Been Pwned durante los
    tests: no son hermeticos ni deterministas, y contraseñas de fixture como
    "password123" SI estan filtradas de verdad, lo que rompe tests que no
    tienen nada que ver con esa comprobacion. Los tests que quieran cubrir el
    caso "contraseña filtrada" deben mockear
    stockhogar.rutas.auth.es_password_filtrada explicitamente."""
    monkeypatch.setattr("stockhogar.rutas.auth.es_password_filtrada", lambda password: False)
