"""Ruta de la pagina principal (SPA)."""
from flask import Blueprint, render_template, session, redirect, url_for

from ..api import manejo_errores

bp = Blueprint("paginas", __name__)


@bp.route("/")
@manejo_errores
def index():
    return render_template("index.html")


@bp.route("/aceptar-invitacion/<codigo>")
@manejo_errores
def aceptar_invitacion_pagina(codigo):
    """Página para aceptar invitación (solo si está logueado)."""
    usuario_id = session.get("usuario_id")

    # Si no está logueado, redirigir a login
    if not usuario_id:
        return redirect(url_for("auth.pagina_login"))

    # Renderizar página de aceptación
    return render_template("aceptar_invitacion.html", codigo=codigo)
