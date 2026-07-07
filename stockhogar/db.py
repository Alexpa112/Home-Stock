"""Conexion a SQLite, migraciones del esquema y utilidades de fecha."""
import sqlite3
from datetime import datetime

from flask import g

from .config import DB_PATH, DIAS_AVISO_DEFECTO


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def asegurar_columna(db, tabla, columna, definicion):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna not in columnas:
        db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL DEFAULT 'Otros',
            cantidad INTEGER NOT NULL DEFAULT 0,
            unidad TEXT NOT NULL DEFAULT 'ud',
            stock_minimo INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    asegurar_columna(db, "productos", "fecha_creacion", "TEXT")
    asegurar_columna(db, "productos", "fecha_actualizacion", "TEXT")
    asegurar_columna(db, "productos", "dias_aviso", f"INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO}")
    # Rellena fechas de productos ya existentes que no las tuvieran (migraciones previas).
    db.execute("UPDATE productos SET fecha_creacion = ? WHERE fecha_creacion IS NULL", (ahora(),))
    db.execute("UPDATE productos SET fecha_actualizacion = ? WHERE fecha_actualizacion IS NULL", (ahora(),))

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS lista_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
            nombre TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT 'ud',
            origen TEXT NOT NULL DEFAULT 'manual',
            sincronizado_bring INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS ajustes (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
        """
    )
    db.commit()
    db.close()
