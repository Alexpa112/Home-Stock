"""Rutas de la lista de la compra: articulos, importacion/exportacion CSV y catalogo personalizado.

Los modulos comparten el Blueprint `articulos_compra` (blueprint.py).
"""
from . import importacion, lista, personalizados  # noqa: F401
from .blueprint import bp

__all__ = ["bp"]
