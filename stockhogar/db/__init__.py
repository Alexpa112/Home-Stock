"""Base de datos SQLite: conexion por peticion, esquema y migraciones.

    conexion.py       get_db / close_db / ahora y utilidades de columnas
    esquema/          tablas por tema (usuarios, catalogo, hogares, gastos, recetas, seguridad, push)
    migraciones.py    migraciones de datos idempotentes
    iconos.py         emojis antiguos -> iconos Lucide
    inicializacion.py init_db (con flock entre procesos de gunicorn)
"""
from .conexion import ahora, asegurar_columna, close_db, get_db, quitar_columna_si_existe
from .inicializacion import init_db

__all__ = ["ahora", "asegurar_columna", "close_db", "get_db", "init_db", "quitar_columna_si_existe"]
