"""Rutas para gestionar categorías de gasto (editables desde la app),
catálogo independiente del de categorías de producto (ver rutas/inventario/categorias.py)."""
from flask import Blueprint

from ...api import manejo_errores, requerir_sesion
from ...config import CATEGORIA_GASTO_DEFECTO, CATEGORIAS_GASTO_DEFECTO
from ...servicios.catalogo_categorias import CatalogoCategorias

bp = Blueprint("categorias_gasto", __name__, url_prefix="/api/categorias-gasto")

CATALOGO = CatalogoCategorias(
    tabla="categorias_gasto",
    tabla_uso="gastos",
    comodin=CATEGORIA_GASTO_DEFECTO,
    de_serie=tuple(c[0] for c in CATEGORIAS_GASTO_DEFECTO),
    clave_en_uso="err_categoria_gasto_en_uso",
)


def normalizar_categoria_gasto(db, nombre):
    """A diferencia de normalizar_categoria (producto), la categoría de un
    gasto es opcional: si no viene informada se devuelve None (sin
    categoría) en vez de caer en el comodín "Otros"."""
    if not nombre:
        return None
    fila = db.execute("SELECT nombre FROM categorias_gasto WHERE nombre = ?", (nombre,)).fetchone()
    return fila["nombre"] if fila else CATEGORIA_GASTO_DEFECTO


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_categorias_gasto():
    return CATALOGO.listar()


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_categoria_gasto():
    return CATALOGO.crear()


@bp.route("/<int:categoria_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_categoria_gasto(categoria_id):
    return CATALOGO.borrar(categoria_id)
