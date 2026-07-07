"""Conexion a SQLite, migraciones del esquema y utilidades de fecha."""
import sqlite3
from datetime import datetime

from flask import g

from .config import CATALOGO_DEFECTO, CATEGORIAS_DEFECTO, DB_PATH, DIAS_AVISO_DEFECTO


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


def quitar_columna_si_existe(db, tabla, columna):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna in columnas:
        try:
            db.execute(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
        except sqlite3.OperationalError:
            pass  # Version de SQLite anterior a 3.35: se queda la columna, pero sin usarse.


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Espacios (stocks independientes: "Casa", "Piso de la playa", etc.).
    # Se crea siempre al menos uno, para que el stock y la lista de la compra
    # ya existentes en instalaciones previas queden asignados a él.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS espacios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono TEXT NOT NULL DEFAULT '🏠',
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "espacios", "color", "TEXT NOT NULL DEFAULT '#B5551A'")
    if db.execute("SELECT COUNT(*) AS n FROM espacios").fetchone()["n"] == 0:
        db.execute(
            "INSERT INTO espacios (nombre, icono, color, fecha_creacion) VALUES (?, ?, ?, ?)",
            ("Mi casa", "🏠", "#B5551A", ahora()),
        )
    espacio_defecto_id = db.execute("SELECT id FROM espacios ORDER BY id LIMIT 1").fetchone()["id"]

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
    asegurar_columna(db, "productos", "icono", "TEXT")
    asegurar_columna(db, "productos", "espacio_id", "INTEGER")
    # Rellena fechas de productos ya existentes que no las tuvieran (migraciones previas).
    db.execute("UPDATE productos SET fecha_creacion = ? WHERE fecha_creacion IS NULL", (ahora(),))
    db.execute("UPDATE productos SET fecha_actualizacion = ? WHERE fecha_actualizacion IS NULL", (ahora(),))
    db.execute("UPDATE productos SET espacio_id = ? WHERE espacio_id IS NULL", (espacio_defecto_id,))

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS lista_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
            nombre TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT 'ud',
            origen TEXT NOT NULL DEFAULT 'manual'
        )
        """
    )
    asegurar_columna(db, "lista_compra", "categoria", "TEXT NOT NULL DEFAULT 'Otros'")
    asegurar_columna(db, "lista_compra", "activo", "INTEGER NOT NULL DEFAULT 1")
    asegurar_columna(db, "lista_compra", "fecha_completado", "TEXT")
    asegurar_columna(db, "lista_compra", "icono", "TEXT")
    asegurar_columna(db, "lista_compra", "cantidad", "INTEGER NOT NULL DEFAULT 1")
    asegurar_columna(db, "lista_compra", "sub_descripcion", "TEXT")
    asegurar_columna(db, "lista_compra", "espacio_id", "INTEGER")
    db.execute("UPDATE lista_compra SET espacio_id = ? WHERE espacio_id IS NULL", (espacio_defecto_id,))
    quitar_columna_si_existe(db, "lista_compra", "sincronizado_bring")
    db.execute("DROP TABLE IF EXISTS ajustes")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono TEXT NOT NULL DEFAULT '🗂️'
        )
        """
    )
    db.executemany(
        "INSERT OR IGNORE INTO categorias (nombre, icono) VALUES (?, ?)",
        CATEGORIAS_DEFECTO,
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_articulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
            icono TEXT NOT NULL,
            categoria TEXT,
            unidad TEXT NOT NULL DEFAULT 'ud',
            sub_descripcion TEXT,
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "historial_articulos", "unidad", "TEXT NOT NULL DEFAULT 'ud'")
    asegurar_columna(db, "historial_articulos", "sub_descripcion", "TEXT")
    asegurar_columna(db, "historial_articulos", "cantidad_defecto", "INTEGER NOT NULL DEFAULT 1")

    # Catalogo de productos habituales de supermercado (ver config.py): se
    # siembra una vez via INSERT OR IGNORE, asi que nunca pisa un articulo
    # que el usuario ya haya personalizado con el mismo nombre.
    db.executemany(
        "INSERT OR IGNORE INTO historial_articulos "
        "(nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, ?, 1, ?)",
        [(n, c, i, u, s, ahora()) for (n, c, i, u, s) in CATALOGO_DEFECTO],
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            fecha_creacion TEXT NOT NULL
        )
        """
    )

    db.commit()
    db.close()
