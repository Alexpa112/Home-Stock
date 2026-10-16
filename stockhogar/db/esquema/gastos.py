"""Gastos compartidos: gastos, participantes, liquidaciones, categorias de gasto y recurrentes."""
from ...config import CATEGORIAS_GASTO_DEFECTO
from ..conexion import asegurar_columna


def aplicar(db):
    # Gastos compartidos del hogar (division tipo Tricount): tablas nuevas,
    # sin datos previos que migrar, por eso basta CREATE TABLE IF NOT EXISTS simple.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            descripcion TEXT NOT NULL,
            importe_total REAL NOT NULL,
            fecha TEXT NOT NULL,
            usuario_pagador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            creado_por_usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_gastos_hogar_fecha ON gastos(hogar_id, fecha)")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos_participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gasto_id INTEGER NOT NULL REFERENCES gastos(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            importe REAL NOT NULL,
            UNIQUE(gasto_id, usuario_id)
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_gastos_participantes_gasto ON gastos_participantes(gasto_id)")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS liquidaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            usuario_origen_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            usuario_destino_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            importe REAL NOT NULL,
            fecha TEXT NOT NULL,
            nota TEXT
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_liquidaciones_hogar_fecha ON liquidaciones(hogar_id, fecha)")

    # Categorias de gasto (independientes de las de producto, ver
    # rutas/finanzas/categorias_gasto.py) y columna opcional en gastos para
    # asignarlas. Sin datos previos que migrar aparte de la columna nueva.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias_gasto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono TEXT NOT NULL DEFAULT 'h-folder'
        )
        """
    )
    db.executemany(
        "INSERT INTO categorias_gasto (nombre, icono) VALUES (?, ?) ON CONFLICT(nombre) DO NOTHING",
        CATEGORIAS_GASTO_DEFECTO,
    )
    asegurar_columna(db, "gastos", "categoria", "TEXT")

    # Foto de recibo adjunta a un gasto (opcional): se guarda como BLOB en
    # la propia stock.db (igual que el resto de datos) en vez de en una
    # carpeta aparte, para no tener que respaldar/gestionar un directorio
    # adicional en la Raspberry Pi.
    asegurar_columna(db, "gastos", "imagen_recibo", "BLOB")
    asegurar_columna(db, "gastos", "imagen_recibo_mime", "TEXT")

    # Gastos recurrentes: plantillas que se materializan como gastos
    # normales (generacion perezosa al listar, ver rutas/finanzas/registro_gastos.py) en
    # vez de depender de una tarea programada aparte.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos_recurrentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            descripcion TEXT NOT NULL,
            importe_total REAL NOT NULL,
            categoria TEXT,
            usuario_pagador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            frecuencia TEXT NOT NULL,
            fecha_fin TEXT,
            proxima_fecha TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_gastos_recurrentes_hogar ON gastos_recurrentes(hogar_id, activo)"
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos_recurrentes_participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gasto_recurrente_id INTEGER NOT NULL REFERENCES gastos_recurrentes(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            importe REAL NOT NULL,
            UNIQUE(gasto_recurrente_id, usuario_id)
        )
        """
    )
