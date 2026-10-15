"""Blueprint de la lista de la compra (los modulos de este paquete registran sus rutas en el)."""
import logging
from flask import Blueprint


bp = Blueprint("articulos_compra", __name__, url_prefix="/api/articulos")


logger = logging.getLogger(__name__)
