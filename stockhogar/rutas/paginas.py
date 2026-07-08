"""Ruta de la pagina principal (SPA)."""
from flask import Blueprint, render_template

from ..api import manejo_errores

bp = Blueprint("paginas", __name__)


@bp.route("/")
@manejo_errores
def index():
    return render_template("index.html")
