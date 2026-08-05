"""Módulo único de autorización sobre hogares (S-15).

Antes de esto, cada blueprint reimplementaba su propia comprobación de
"¿puede este usuario ver/editar este hogar?" con helpers privados distintos
(permisos.py, hogares.py, gastos.py, articulos_compra.py...), lo que dejaba
la puerta abierta a un IDOR el día que un endpoint nuevo implementase la
comprobación de forma distinta a las demás. Este módulo centraliza la
jerarquía de niveles (propietario > editar > ver) en un único sitio.
"""
from functools import wraps

from flask import g, request, session

from .api import APIResponse
from .db import get_db

NIVELES = {"ver": 1, "editar": 2, "propietario": 3}


def nivel_acceso_hogar(db, hogar_id, usuario_id):
    """Devuelve "propietario", "editar", "ver" o None (sin acceso) para el
    usuario dado sobre el hogar dado."""
    hogar = db.execute(
        "SELECT usuario_propietario_id FROM hogares WHERE id = ?", (hogar_id,)
    ).fetchone()
    if not hogar:
        return None
    if hogar["usuario_propietario_id"] == usuario_id:
        return "propietario"
    permiso = db.execute(
        "SELECT nivel FROM permisos_hogar WHERE hogar_id = ? AND usuario_id = ?",
        (hogar_id, usuario_id),
    ).fetchone()
    if permiso and permiso["nivel"] in NIVELES:
        return permiso["nivel"]
    return None


def requerir_hogar(nivel_minimo="ver"):
    """Decorador de ruta: exige que el usuario autenticado tenga, sobre el
    hogar de la URL, al menos `nivel_minimo` ("ver", "editar" o
    "propietario"). Debe usarse SIEMPRE junto a @requerir_sesion (lee
    session["usuario_id"], que ese decorador ya valida) y por debajo de él
    en la pila de decoradores, ya que Flask exige @bp.route en la posición
    más externa.

    Lee `hogar_id` de los kwargs de la ruta Flask (p.ej. @bp.route("/<int:hogar_id>/...")).
    Si un endpoint concreto resuelve el hogar de otra forma (p.ej.
    _resolver_hogar_id en articulos_compra.py, que puede depender de la
    sesión en vez de venir en la URL), no uses este decorador en él.
    """
    if nivel_minimo not in NIVELES:
        raise ValueError(f"nivel_minimo desconocido: {nivel_minimo}")

    def envoltura(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            hogar_id = kwargs.get("hogar_id")
            usuario_id = session.get("usuario_id")
            nivel = nivel_acceso_hogar(get_db(), hogar_id, usuario_id) if hogar_id is not None else None
            if nivel is None or NIVELES[nivel] < NIVELES[nivel_minimo]:
                return APIResponse.no_permitido()
            g.nivel_acceso_hogar = nivel
            return f(*args, **kwargs)
        return decorated
    return envoltura
