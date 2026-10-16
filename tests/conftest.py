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

    Se parchea `stockhogar.config.DB_PATH`: el paquete `stockhogar.db` la lee de ahi en
    cada llamada a get_db()/init_db(), de modo que basta con sustituir el atributo antes
    del primer test.

    Es de ámbito de sesión: init_db() siembra el catálogo estándar (cientos de
    artículos) y hacerlo por test multiplicaría el tiempo de la suite.
    """
    import stockhogar.config as config

    directorio = Path(tempfile.mkdtemp(prefix="stockhogar-tests-"))
    ruta_bd = directorio / "stock.db"

    originales = {
        "config.DB_PATH": config.DB_PATH,
        "config.DATA_DIR": config.DATA_DIR,
    }
    config.DB_PATH = ruta_bd
    config.DATA_DIR = directorio

    try:
        yield ruta_bd
    finally:
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
    es_password_filtrada de rutas/cuenta/{sesion,credenciales} explicitamente."""
    for modulo in ("sesion", "credenciales"):
        monkeypatch.setattr(f"stockhogar.rutas.cuenta.{modulo}.es_password_filtrada", lambda password: False)
