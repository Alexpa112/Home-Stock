"""Rutas para gestionar categorías de productos (editables desde la app)."""
from flask import Blueprint

from ...api import manejo_errores, requerir_sesion
from ...config import CATEGORIA_DEFECTO, CATEGORIAS_DEFECTO
from ...servicios.catalogo_categorias import CatalogoCategorias

bp = Blueprint("categorias", __name__, url_prefix="/api/categorias")

CATALOGO = CatalogoCategorias(
    tabla="categorias",
    tabla_uso="productos",
    comodin=CATEGORIA_DEFECTO,
    de_serie=tuple(c[0] for c in CATEGORIAS_DEFECTO),
    clave_en_uso="err_categoria_en_uso",
)


def normalizar_categoria(db, nombre):
    """Devuelve el nombre si existe como categoría, o el comodín por defecto."""
    fila = db.execute("SELECT nombre FROM categorias WHERE nombre = ?", (nombre,)).fetchone()
    return fila["nombre"] if fila else CATEGORIA_DEFECTO


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_categorias():
    return CATALOGO.listar()


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_categoria():
    return CATALOGO.crear()


@bp.route("/<int:categoria_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_categoria(categoria_id):
    return CATALOGO.borrar(categoria_id)
