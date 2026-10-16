"""Rutas de cuenta: sesion, doble factor, perfil, credenciales y datos personales (RGPD), mas OAuth.

Todos los modulos comparten el Blueprint `auth` (blueprint.py): al importarlos se registran
sus rutas. `comunes.py` reune lo que usan varios (tokens, validaciones, reautenticacion).
"""
from . import comunes, credenciales, datos_personales, doble_factor, perfil, sesion  # noqa: F401
from .blueprint import RUTAS_PUBLICAS, bp

__all__ = ["RUTAS_PUBLICAS", "bp"]
