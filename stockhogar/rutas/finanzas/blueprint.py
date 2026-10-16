"""Blueprint de gastos compartidos (los modulos de este paquete registran sus rutas en el)."""
from flask import Blueprint


bp = Blueprint("gastos", __name__, url_prefix="/api/gastos")
