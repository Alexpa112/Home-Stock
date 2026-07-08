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


def _migrar_lista_compra_a_articulos(db, espacio_defecto_id):
    """
    Migra datos de la tabla antigua lista_compra a articulos_lista.

    Crea una lista 'por defecto' para cada usuario con sus artículos existentes.
    Esta función se ejecuta solo si encuentra la tabla antigua.
    """
    # Obtener todos los usuarios
    usuarios = db.execute("SELECT id, nombre_usuario FROM usuarios").fetchall()

    for usuario in usuarios:
        usuario_id = usuario["id"]
        nombre_usuario = usuario["nombre_usuario"]

        # Crear lista 'por defecto' para este usuario si no existe
        lista_existente = db.execute(
            "SELECT id FROM listas WHERE usuario_propietario_id = ? AND nombre = 'Mi lista'",
            (usuario_id,),
        ).fetchone()

        if not lista_existente:
            cur = db.execute(
                "INSERT INTO listas (nombre, descripcion, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion, icono) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("Mi lista", "Lista de compra principal", usuario_id, 1, ahora(), ahora(), "📋"),
            )
            lista_id = cur.lastrowid
        else:
            lista_id = lista_existente["id"]

        # Migrar artículos de lista_compra que pertenecían a este usuario/espacio
        # (Asumimos que todos los artículos sin usuario explícito son del primer usuario)
        if usuario_id == usuarios[0]["id"]:
            # Verificar qué columnas existen en la tabla antigua
            columnas_existentes = {
                col["name"] for col in db.execute(
                    "PRAGMA table_info(lista_compra)"
                ).fetchall()
            }

            # Construir el SELECT dinámicamente según las columnas disponibles
            campos = ["?", "producto_id", "nombre", "unidad"]

            if "categoria" in columnas_existentes:
                campos.append("COALESCE(categoria, 'Otros')")
            else:
                campos.append("'Otros'")

            if "icono" in columnas_existentes:
                campos.append("icono")
            else:
                campos.append("NULL")

            if "cantidad" in columnas_existentes:
                campos.append("COALESCE(cantidad, 1)")
            else:
                campos.append("1")

            if "sub_descripcion" in columnas_existentes:
                campos.append("sub_descripcion")
            else:
                campos.append("NULL")

            campos.append("origen")

            if "activo" in columnas_existentes:
                campos.append("COALESCE(activo, 1)")
            else:
                campos.append("1")

            if "fecha_completado" in columnas_existentes:
                campos.append("fecha_completado")
            else:
                campos.append("NULL")

            campos.append("?")  # fecha_creacion

            select_clause = f"SELECT {', '.join(campos)} FROM lista_compra"

            db.execute(
                f"""
                INSERT INTO articulos_lista
                (lista_id, producto_id, nombre, unidad, categoria, icono, cantidad,
                 sub_descripcion, origen, activo, fecha_completado, fecha_creacion)
                {select_clause}
                """,
                (lista_id, ahora()),
            )

    # Después de migrar, renombrar la tabla antigua para que no interfiera
    try:
        db.execute("ALTER TABLE lista_compra RENAME TO lista_compra_backup")
    except sqlite3.OperationalError:
        pass  # Si no se puede renombrar, simplemente continuar


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Tabla de usuarios (debe existir antes de crear listas, ya que las listas
    # tienen una relación con usuarios)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            fecha_creacion TEXT NOT NULL,
            email TEXT
        )
        """
    )
    asegurar_columna(db, "usuarios", "email", "TEXT")

    # Tabla para cuentas OAuth (Google, Apple)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            proveedor TEXT NOT NULL CHECK (proveedor IN ('google', 'apple')),
            id_proveedor TEXT NOT NULL,
            email TEXT NOT NULL,
            nombre TEXT,
            foto_perfil TEXT,
            fecha_creacion TEXT NOT NULL,
            UNIQUE(proveedor, id_proveedor)
        )
        """
    )

    # Tabla listas: contenedor principal de artículos, similar a Bring!
    # Cada lista pertenece a un usuario (propietario) y puede compartirse
    # con otros usuarios mediante permisos_lista
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS listas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            privada INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "listas", "icono", "TEXT NOT NULL DEFAULT '📋'")

    # Tabla permisos_lista: relación usuario ↔ lista con niveles de acceso
    # niveles: 'ver' (solo lectura) o 'editar' (lectura + escritura)
    # El propietario tiene control total sin necesidad de estar aquí
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS permisos_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'editar')),
            fecha_otorgado TEXT NOT NULL,
            UNIQUE(lista_id, usuario_id)
        )
        """
    )

    # Tabla de invitaciones para compartir listas por email
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS invitaciones_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            email_destino TEXT NOT NULL,
            nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'editar')),
            codigo_invitacion TEXT NOT NULL UNIQUE,
            usado INTEGER NOT NULL DEFAULT 0,
            usuario_aceptacion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            fecha_creacion TEXT NOT NULL,
            fecha_expiracion TEXT NOT NULL,
            fecha_aceptacion TEXT
        )
        """
    )

    # Espacios: ahora son opcionales (podría usarse para categorizar listas después)
    # Se mantiene para compatibilidad hacia atrás
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

    # Tabla articulos_lista: artículos dentro de cada lista
    # Migración: originalmente era lista_compra, ahora vinculada a listas
    # en lugar de espacios
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS articulos_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
            nombre TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT 'ud',
            categoria TEXT NOT NULL DEFAULT 'Otros',
            icono TEXT,
            cantidad INTEGER NOT NULL DEFAULT 1,
            sub_descripcion TEXT,
            origen TEXT NOT NULL DEFAULT 'manual',
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_completado TEXT,
            fecha_creacion TEXT
        )
        """
    )

    # Compatibilidad: si existe lista_compra antigua, no hacer nada por ahora
    # (se migrará después con la función _migrar_lista_compra_a_articulos)
    tabla_existe = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lista_compra'"
    ).fetchone()
    if tabla_existe:
        # Tabla antigua existe, es una instalación anterior
        _migrar_lista_compra_a_articulos(db, espacio_defecto_id)
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

    db.commit()
    db.close()
