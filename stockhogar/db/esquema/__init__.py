"""Esquema de la base de datos, por temas y en el orden en que debe ejecutarse.

El orden importa: las migraciones de un paso suponen las tablas del anterior (p.ej. `hogares`
nace de renombrar `listas`). Todos los pasos son idempotentes (CREATE ... IF NOT EXISTS y
columnas añadidas solo si faltan), asi que se ejecutan completos en cada arranque.
"""
from . import base, catalogo, gastos, hogares, push, recetas, seguridad, tickets

PASOS = (base, catalogo, hogares, gastos, recetas, seguridad, push, tickets)


def crear_esquema(db):
    for paso in PASOS:
        paso.aplicar(db)
