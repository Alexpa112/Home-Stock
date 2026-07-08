"""Ruta de la pagina principal (SPA)."""
from flask import Blueprint, render_template

bp = Blueprint("paginas", __name__)


@bp.route("/")
def index():
    return render_template("index.html")
