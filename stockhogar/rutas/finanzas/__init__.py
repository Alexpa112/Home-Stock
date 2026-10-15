"""Rutas de gastos compartidos del hogar y sus categorias.

Los modulos de gastos comparten el Blueprint `gastos` (blueprint.py): al importarlos se registran sus
rutas. `comunes.py` reune lo que usan varios (reparto, miembros, aviso de presupuesto).
"""
from . import categorias_gasto, comunes, recibos, recurrentes, registro_gastos, saldos  # noqa: F401
from .blueprint import bp

__all__ = ["bp"]
