"""Capa de abstraccion de conexion a base de datos: SQLite (motor por
defecto, comportamiento IDENTICO al actual) o PostgreSQL (opt-in,
experimental, ver docs/PROPUESTA_SEGURIDAD_Y_FUNCIONALIDADES.md, Fase 1.5).

Mientras DB_ENGINE=sqlite (el valor por defecto si no se define), esta app
funciona exactamente igual que antes de este modulo: `conectar()` delega en
`stockhogar.db.get_db()` sin cambiar PRAGMAs, row_factory ni nada. El soporte
Postgres es opt-in mediante DB_ENGINE=postgres y NO ha sido validado con una
migracion de datos real todavia (ver scripts/migrar_a_postgres.py); no
activar en produccion sin haber corrido esa migracion y verificado los datos.

Inventario de sintaxis especifica de SQLite en stockhogar/ (actualizado
2026-08-05 tras completar la traduccion de las rutas activas):

    - `.lastrowid` (tras INSERT, estilo sqlite3.Cursor): TRADUCIDO. Los 14
      sitios (db.py, rutas/articulos_compra.py, rutas/categorias.py,
      rutas/categorias_gasto.py, rutas/gastos.py, rutas/hogares.py,
      rutas/oauth.py, servicios/stock.py) usan ahora `INSERT ... RETURNING
      id` + `cursor.fetchone()["id"]`, sintaxis identica valida en SQLite
      3.35+ y en Postgres. OJO al leerlo: el fetchone() debe hacerse
      INMEDIATAMENTE tras el INSERT, antes de cualquier otro `execute()` u
      `commit()` en la misma conexion - un cursor con RETURNING sin
      consumir bloquea ambas cosas en SQLite ("cannot commit transaction -
      SQL statements in progress").
    - `INSERT OR REPLACE`: TRADUCIDO (rutas/permisos.py, rutas/productos.py)
      a `INSERT ... ON CONFLICT (col_unica) DO UPDATE SET ...`.
    - `INSERT OR IGNORE`: TRADUCIDO (db.py, servicios/stock.py) a
      `INSERT ... ON CONFLICT (col_unica) DO NOTHING`.
    - `COLLATE NOCASE` en queries (WHERE/ORDER BY/LIKE): TRADUCIDO en todos
      los blueprints de rutas/ a `LOWER(columna) = LOWER(?)` /
      `ORDER BY LOWER(columna)` / `LOWER(columna) LIKE LOWER(?)`. Quedan
      SIN tocar (a proposito) las declaraciones `COLLATE NOCASE` a nivel de
      columna en `CREATE TABLE` de db.py (historial_articulos,
      articulos_personalizados) y las migraciones legacy de una sola vez
      gateadas por `PRAGMA table_info` (ver punto siguiente): son DDL que
      solo se ejecuta en el camino SQLite (init_db() nunca corre contra
      Postgres, ver mas abajo), asi que no bloquean nada real.
    - `PRAGMA table_info(...)` / `PRAGMA writable_schema`: PENDIENTE
      (~20 apariciones, todas en db.py: asegurar_columna,
      quitar_columna_si_existe y migraciones legacy ad-hoc). Equivalente
      Postgres: `information_schema.columns`. No se ha traducido porque
      solo importa si alguien ejecutase init_db() contra Postgres, y la via
      soportada es la contraria (migrar datos ya existentes con
      scripts/migrar_a_postgres.py, que recrea el esquema por su cuenta sin
      pasar por asegurar_columna). Bajo valor/alto esfuerzo para el
      alcance actual.
    - `strftime(...)` / `julianday(...)`: no aplica - la unica aparicion
      encontrada (rutas/gastos.py) es `datetime.strftime` de Python, no la
      funcion SQL de SQLite.
    - `AUTOINCREMENT` (SQLite): no requiere traduccion en el codigo de la
      app; lo resuelve scripts/migrar_a_postgres.py al recrear el esquema
      en destino (SERIAL/GENERATED ALWAYS AS IDENTITY), no init_db().
    - `?` como marcador de parametro (estilo sqlite3): resuelto por el
      wrapper de cursor de este modulo (ver CursorCompatPostgres mas abajo).

    ESTADO ACTUAL: con la traduccion de arriba completada, el camino
    DB_ENGINE=postgres deberia funcionar para el trafico normal de la app
    contra un esquema ya migrado con scripts/migrar_a_postgres.py. NO
    verificado contra un Postgres real en esta tanda (sin servidor Postgres
    disponible en el entorno de desarrollo) - antes de activar en
    produccion, probar el flujo completo (migrar datos + arrancar con
    DB_ENGINE=postgres + ejercitar los endpoints) contra una instancia real.
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
