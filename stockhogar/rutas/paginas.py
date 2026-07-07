"""Ruta de la pagina principal (SPA)."""
from flask import Blueprint, render_template

from ..config import CATEGORIES

bp = Blueprint("paginas", __name__)


@bp.route("/")
def index():
    return render_template("index.html", categorias=CATEGORIES)
