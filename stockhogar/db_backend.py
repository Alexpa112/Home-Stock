"""Capa de abstraccion de conexion a base de datos: SQLite (motor por
defecto, comportamiento IDENTICO al actual) o PostgreSQL (opt-in,
experimental, ver docs/PROPUESTA_SEGURIDAD_Y_FUNCIONALIDADES.md, Fase 1.5).

Mientras DB_ENGINE=sqlite (el valor por defecto si no se define), esta app
funciona exactamente igual que antes de este modulo: `conectar()` delega en
`stockhogar.db.get_db()` sin cambiar PRAGMAs, row_factory ni nada. El soporte
Postgres es opt-in mediante DB_ENGINE=postgres y NO ha sido validado con una
migracion de datos real todavia (ver scripts/migrar_a_postgres.py); no
activar en produccion sin haber corrido esa migracion y verificado los datos.

Inventario de sintaxis especifica de SQLite en stockhogar/ (grep sobre todos
los .py, 2026-08-05), que motiva por que esta capa hace falta y que se
tradujo (o no) en el Paso 3 de la tarea de migracion:

    - `.lastrowid` (tras INSERT, estilo sqlite3.Cursor): 14 apariciones en
      stockhogar/db.py, rutas/articulos_compra.py, rutas/categorias.py,
      rutas/categorias_gasto.py, rutas/gastos.py, rutas/hogares.py,
      rutas/oauth.py, servicios/stock.py. Postgres no tiene `.lastrowid`; el
      equivalente portable es `INSERT ... RETURNING id`. NO se ha tocado en
      esta tarea (alcance demasiado amplio y sensible para hacerlo a la vez
      que el resto de cambios sin una revision mas detenida - ver informe).
    - `INSERT OR REPLACE`: 4 apariciones (rutas/permisos.py,
      rutas/productos.py). Equivalente Postgres: `INSERT ... ON CONFLICT
      (col_unica) DO UPDATE SET ...`. Pendiente, mismo motivo que arriba.
    - `INSERT OR IGNORE`: 6 apariciones (db.py, servicios/stock.py).
      Equivalente: `INSERT ... ON CONFLICT (col_unica) DO NOTHING`.
      Pendiente.
    - `COLLATE NOCASE`: 37 apariciones (db.py y varios blueprints en
      rutas/). Equivalente portable sin configuracion especial de collation
      en el servidor Postgres: `LOWER(columna) = LOWER(?)`. Pendiente.
    - `PRAGMA table_info(...)` / `PRAGMA writable_schema`: 20 apariciones,
      todas en db.py (asegurar_columna, quitar_columna_si_existe y varias
      migraciones ad-hoc de una sola vez). Equivalente Postgres:
      `information_schema.columns`. Pendiente (habria que centralizarlo en
      asegurar_columna/quitar_columna_si_existe, que son los unicos puntos
      de entrada).
    - `strftime(...)`: 1 aparicion. `julianday(...)`: 0. No se ha revisado
      su equivalente Postgres por no bloquear el resto de la tarea.
    - `AUTOINCREMENT` (SQLite): 30 apariciones, todas en `CREATE TABLE ...
      id INTEGER PRIMARY KEY AUTOINCREMENT`. En Postgres el equivalente es
      `SERIAL`/`GENERATED ALWAYS AS IDENTITY`; lo resuelve
      scripts/migrar_a_postgres.py al recrear el esquema en destino, no
      hace falta tocar db.py para esto salvo que se quiera un init_db()
      que cree tablas nativamente en Postgres (no implementado: la via
      soportada para tener esquema en Postgres es migrar datos ya
      existentes desde SQLite con el script, no arrancar en Postgres desde
      cero).
    - `?` como marcador de parametro (estilo sqlite3): omnipresente en todo
      el codigo. Postgres/psycopg2 usa `%s`. Resuelto por el wrapper de
      cursor de este modulo (ver CursorCompatPostgres mas abajo): traduce
      automaticamente `?` -> `%s` solo cuando el motor activo es Postgres,
      para no tener que tocar cientos de lineas de SQL ya escritas.

    NOTA IMPORTANTE: dado que el Paso 3 (traduccion de .lastrowid,
    INSERT OR REPLACE/IGNORE, COLLATE NOCASE y PRAGMA table_info en
    stockhogar/db.py y en los blueprints de rutas/) NO se ha aplicado, el
    camino DB_ENGINE=postgres de este modulo permite CONECTAR y ejecutar
    SQL simple contra Postgres, pero init_db() y buena parte de las rutas
    fallaran contra Postgres real hasta que ese trabajo se complete (usan
    sintaxis SQLite que Postgres no entiende). Ver el informe final de la
    tarea para el razonamiento de por que se prioriza no tocar esas ~77
    apariciones repartidas en 8+ ficheros en la misma tanda que el resto de
    esta migracion.
"""
import os
import re

from .config import (
    DB_ENGINE,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

_RE_PLACEHOLDER = re.compile(r"\?")


def motor_activo():
    """Devuelve el motor de BD configurado ("sqlite" o "postgres")."""
    return DB_ENGINE if DB_ENGINE in ("sqlite", "postgres") else "sqlite"


class _CursorCompatPostgres:
    """Envuelve un cursor de psycopg2 para que .execute()/.executemany()
    acepten SQL escrito con marcadores `?` (estilo sqlite3), traduciendolos
    a `%s` (estilo psycopg2) antes de delegar. Todo lo demas (fetchone,
    fetchall, lastrowid si se usara, etc.) se delega sin cambios al cursor
    real via __getattr__.

    Limitacion conocida y aceptada: la traduccion es un reemplazo textual de
    "?" por "%s" y NO analiza el SQL, por lo que un literal de texto que
    contenga un caracter "?" tambien se traduciria (falso positivo). Se
    acepta este riesgo porque, revisando el codigo actual, ningun SQL
    embebido en stockhogar/ contiene "?" dentro de un literal (los `?` que
    aparecen siempre son marcadores de parametro), y la alternativa (un
    parser SQL completo) es una complejidad que no esta justificada para
    este caso. Si en el futuro se añade una consulta con un "?" literal,
    debe escribirse evitando el caracter (p.ej. concatenando) para no
    romper esta traduccion.
    """

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        return self._cursor.execute(_RE_PLACEHOLDER.sub("%s", sql), params)

    def executemany(self, sql, seq_of_params):
        return self._cursor.executemany(_RE_PLACEHOLDER.sub("%s", sql), seq_of_params)

    def __getattr__(self, nombre):
        return getattr(self._cursor, nombre)

    def __iter__(self):
        return iter(self._cursor)


class _ConexionCompatPostgres:
    """Envuelve una conexion de psycopg2 para que .execute()/.executemany()
    a nivel de conexion (patron que usa sqlite3.Connection y que el codigo
    existente reutiliza, p.ej. `db.execute(...)`) funcionen igual que con
    sqlite3, delegando en un cursor con RealDictCursor (filas tipo dict,
    accesibles como fila["columna"] igual que sqlite3.Row) y traduccion de
    marcadores de parametro.
    """

    def __init__(self, conexion):
        self._conexion = conexion

    def execute(self, sql, params=()):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def executemany(self, sql, seq_of_params):
        cursor = self.cursor()
        cursor.executemany(sql, seq_of_params)
        return cursor

    def cursor(self):
        import psycopg2.extras

        return _CursorCompatPostgres(self._conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def __getattr__(self, nombre):
        return getattr(self._conexion, nombre)


def conectar():
    """Devuelve una conexion al motor de BD activo.

    - DB_ENGINE=sqlite (defecto): delega en stockhogar.db.get_db(), sin
      ningun cambio de comportamiento respecto a como funciona hoy.
    - DB_ENGINE=postgres: conecta con psycopg2 usando las variables de
      entorno POSTGRES_HOST/PORT/DB/USER/PASSWORD (ver .env.example) y
      devuelve un wrapper compatible con el uso que el resto del codigo
      hace de una conexion sqlite3 (fila["columna"], marcadores `?`).
    """
    if motor_activo() == "postgres":
        import psycopg2

        conexion = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
        )
        return _ConexionCompatPostgres(conexion)

    from . import db as _db

    return _db.get_db()
