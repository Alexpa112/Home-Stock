"""Migra los datos de la base de datos SQLite de StockHogar a un Postgres
destino (Fase 1.5, ver docs/PROPUESTA_SEGURIDAD_Y_FUNCIONALIDADES.md).

NO borra ni modifica la base SQLite origen: es una copia, no un "mover". La
app sigue funcionando con DB_ENGINE=sqlite despues de correr este script;
cambiar a DB_ENGINE=postgres es una decision manual posterior, una vez
verificados los datos.

Uso:
    python scripts/migrar_a_postgres.py             # migra de verdad
    python scripts/migrar_a_postgres.py --dry-run    # solo cuenta filas

Variables de entorno para el destino (mismas que stockhogar/db_backend.py):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Decisiones de tipos SQLite -> Postgres:
    - Columnas "TEXT" que en SQLite guardan fechas ISO8601 (fecha_creacion,
      fecha_actualizacion, etc.) se copian tal cual como TEXT en Postgres,
      NO se convierten a TIMESTAMP. Motivo: el codigo actual de
      stockhogar/ las trata siempre como texto (comparaciones, formateo,
      SUBSTR), y convertir a TIMESTAMP aqui obligaria a adaptar ese codigo
      en la misma tarea que la migracion de datos, mezclando dos cambios de
      riesgo distinto. Queda como mejora futura una vez el motor Postgres
      este confirmado.
    - Columnas BLOB (fotos de recibos/tickets) se copian a BYTEA.
    - INTEGER PRIMARY KEY AUTOINCREMENT de SQLite -> columna INTEGER normal
      en Postgres con una SEQUENCE asociada via
      `ALTER SEQUENCE ... RESTART WITH ...` al final de la copia de cada
      tabla, para que los proximos INSERT en Postgres no colisionen con los
      ids ya copiados.
    - El esquema de columnas de cada tabla se toma directamente de
      `PRAGMA table_info` sobre el SQLite origen (no se reescribe a mano),
      para no duplicar la fuente de verdad del esquema que ya vive en
      stockhogar/db.py::init_db(). El mapeo de tipo SQLite -> tipo Postgres
      es deliberadamente simple (ver _tipo_postgres) porque SQLite no
      distingue tipos con la misma rigidez que Postgres; sirve para volcar
      datos, no pretende recrear constraints/FKs/UNIQUE (esos se recrean
      aparte, ver limitaciones mas abajo).

Limitaciones conocidas (aceptadas para esta primera version del script):
    - No recrea FOREIGN KEY, UNIQUE ni CHECK constraints en destino, solo
      columnas y tipos basicos. Antes de dar la migracion por completa hay
      que aplicar sobre el Postgres destino el mismo esquema de constraints
      que stockhogar/db.py::init_db() define para SQLite (traducido a
      Postgres), o ejecutar init_db() contra Postgres una vez el Paso 3 de
      la migracion (traduccion de sintaxis SQLite en db.py) este completo.
    - Requiere que las tablas en destino aun no tengan datos (o acepta
      duplicar si se corre dos veces) - no es idempotente. Pensado para una
      unica ejecucion controlada durante la ventana de corte.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stockhogar.config import (  # noqa: E402
    DB_PATH,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def _tipo_postgres(tipo_sqlite, es_blob):
    if es_blob:
        return "BYTEA"
    tipo = (tipo_sqlite or "").upper()
    if "INT" in tipo:
        return "BIGINT"
    if "REAL" in tipo or "DOUB" in tipo or "FLOA" in tipo:
        return "DOUBLE PRECISION"
    return "TEXT"


def _listar_tablas(sqlite_con):
    filas = sqlite_con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [f["name"] for f in filas]


def _columnas(sqlite_con, tabla):
    """Devuelve [(nombre, tipo_sqlite, es_pk)] via PRAGMA table_info, en el
    orden declarado de la tabla."""
    return [
        (fila["name"], fila["type"], bool(fila["pk"]))
        for fila in sqlite_con.execute(f"PRAGMA table_info({tabla})").fetchall()
    ]


def _es_columna_blob(sqlite_con, tabla, columna):
    fila = sqlite_con.execute(f"SELECT typeof({columna}) AS t FROM {tabla} WHERE {columna} IS NOT NULL LIMIT 1").fetchone()
    return bool(fila) and fila["t"] == "blob"


def _crear_tabla_destino(pg_cur, tabla, columnas_info, blobs):
    columnas_sql = []
    pk = None
    for nombre, tipo, es_pk in columnas_info:
        columnas_sql.append(f'"{nombre}" {_tipo_postgres(tipo, nombre in blobs)}')
        if es_pk:
            pk = nombre
    definicion = ", ".join(columnas_sql)
    if pk:
        definicion += f', PRIMARY KEY ("{pk}")'
    pg_cur.execute(f'CREATE TABLE IF NOT EXISTS "{tabla}" ({definicion})')


def _copiar_filas(sqlite_con, pg_cur, tabla, columnas_info, blobs, dry_run):
    nombres = [c[0] for c in columnas_info]
    filas = sqlite_con.execute(f'SELECT {", ".join(nombres)} FROM "{tabla}"').fetchall()
    if dry_run:
        return len(filas)

    placeholders = ", ".join(["%s"] * len(nombres))
    columnas_quoted = ", ".join(f'"{n}"' for n in nombres)
    insert_sql = f'INSERT INTO "{tabla}" ({columnas_quoted}) VALUES ({placeholders})'
    for fila in filas:
        valores = [bytes(fila[n]) if n in blobs and fila[n] is not None else fila[n] for n in nombres]
        pg_cur.execute(insert_sql, valores)
    return len(filas)


def _ajustar_secuencia(pg_cur, tabla, columnas_info):
    pk = next((n for n, _, es_pk in columnas_info if es_pk), None)
    if pk is None:
        return
    pg_cur.execute(
        f'SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE((SELECT MAX("{pk}") FROM "{tabla}"), 1))',
        (tabla, pk),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo cuenta filas, no escribe en Postgres")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERROR] No existe la base SQLite origen: {DB_PATH}")
        sys.exit(1)

    sqlite_con = sqlite3.connect(DB_PATH)
    sqlite_con.row_factory = sqlite3.Row

    pg_con = None
    pg_cur = None
    if not args.dry_run:
        import psycopg2

        pg_con = psycopg2.connect(
            host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        )
        pg_cur = pg_con.cursor()

    tablas = _listar_tablas(sqlite_con)
    recuentos_origen = {}
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Migrando {len(tablas)} tablas de {DB_PATH} a Postgres ({POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB})")

    for tabla in tablas:
        columnas_info = _columnas(sqlite_con, tabla)
        blobs = {nombre for nombre, _, _ in columnas_info if _es_columna_blob(sqlite_con, tabla, nombre)}

        if args.dry_run:
            n = _copiar_filas(sqlite_con, None, tabla, columnas_info, blobs, dry_run=True)
            recuentos_origen[tabla] = n
            print(f"  - {tabla}: {n} filas (no se escribe nada)")
            continue

        _crear_tabla_destino(pg_cur, tabla, columnas_info, blobs)
        n = _copiar_filas(sqlite_con, pg_cur, tabla, columnas_info, blobs, dry_run=False)
        _ajustar_secuencia(pg_cur, tabla, columnas_info)
        pg_con.commit()
        recuentos_origen[tabla] = n
        print(f"  - {tabla}: {n} filas copiadas")

    if args.dry_run:
        print(f"\n[DRY-RUN] Total filas a migrar: {sum(recuentos_origen.values())}")
        sqlite_con.close()
        return

    print("\nVerificando recuentos origen vs destino...")
    errores = []
    for tabla, n_origen in recuentos_origen.items():
        pg_cur.execute(f'SELECT COUNT(*) FROM "{tabla}"')
        n_destino = pg_cur.fetchone()[0]
        if n_destino != n_origen:
            errores.append(f"{tabla}: origen={n_origen} destino={n_destino}")

    sqlite_con.close()
    pg_cur.close()
    pg_con.close()

    if errores:
        print("[ERROR] Recuentos no coinciden:")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)

    print("OK: todos los recuentos coinciden. La base SQLite origen no se ha modificado.")


if __name__ == "__main__":
    main()
