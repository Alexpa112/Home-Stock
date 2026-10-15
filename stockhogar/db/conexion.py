"""Conexion a SQLite por peticion y utilidades de fecha y de columnas."""
import sqlite3
from datetime import datetime

from flask import g

from .. import config


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        # WAL + synchronous=NORMAL: en la SD de la Raspberry Pi el modo por
        # defecto (rollback journal + synchronous=FULL) hace un fsync costoso
        # en cada commit y bloquea lectores mientras hay una escritura.
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA synchronous = NORMAL")
        # Si otra conexion tiene una escritura en curso, esperar hasta 5s en
        # vez de fallar al instante con "database is locked" (relevante sobre
        # todo bajo tests, que abren/cierran conexiones muy seguido contra el
        # mismo fichero).
        g.db.execute("PRAGMA busy_timeout = 5000")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def asegurar_columna(db, tabla, columna, definicion):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna not in columnas:
        db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def quitar_columna_si_existe(db, tabla, columna):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna in columnas:
        try:
            db.execute(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
        except sqlite3.OperationalError:
            pass  # Version de SQLite anterior a 3.35: se queda la columna, pero sin usarse.
