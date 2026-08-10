"""Tests del emparejado de nombres del MatcherInteligente.

Por encima del umbral el articulo se da por existente y al confirmar el ticket
el stock se suma a ESE producto del catalogo, asi que estos tests fijan las dos
mitades del comportamiento: los nombres que deben emparejar (variantes con
tilde, palabras en otro orden, tamaño de envase de mas) y, sobre todo, los que
NO deben emparejar, porque una coincidencia falsa mueve stock del producto
equivocado y es peor que dejarlo como articulo nuevo.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.matcher_inteligente import MatcherInteligente

CATALOGO = [
    {"id": 1, "nombre": "Leche entera 1L", "categoria": "Bebidas", "icono": "🥛"},
    {"id": 2, "nombre": "Pan integral 500g", "categoria": "Alimentación", "icono": "🍞"},
    {"id": 3, "nombre": "Tomates frescos", "categoria": "Frutas y Verduras", "icono": "🍅"},
    {"id": 4, "nombre": "Manzanas rojas", "categoria": "Frutas y Verduras", "icono": "🍎"},
]


class _Cursor:
    def __init__(self, filas):
        self._filas = filas

    def fetchall(self):
        return self._filas


class _DbFalsa:
    def execute(self, consulta, parametros=None):
        if "FROM productos" in consulta:
            return _Cursor(CATALOGO)
        return _Cursor([])


def _buscar(nombre_ocr):
    # Instancia nueva por busqueda: el matcher cachea el catalogo por instancia.
    return MatcherInteligente().buscar_en_catalogo(nombre_ocr, _DbFalsa())


def test_nombre_practicamente_igual_empareja():
    resultado = _buscar("LECHE ENTERA 1L")
    assert resultado is not None
    assert resultado["id"] == 1


def test_nombre_sin_el_tamano_del_envase_empareja():
    resultado = _buscar("Leche entera")
    assert resultado is not None
    assert resultado["id"] == 1


def test_tilde_perdida_o_sobrante_no_impide_emparejar():
    resultado = _buscar("Lechè entera")
    assert resultado is not None
    assert resultado["id"] == 1


def test_palabras_en_otro_orden_emparejan():
    """La comparacion caracter a caracter puntua mal un nombre reordenado; lo
    salva el factor de palabras en comun."""
    resultado = _buscar("Pascual leche entera")
    assert resultado is not None
    assert resultado["id"] == 1


def test_producto_distinto_no_empareja_por_compartir_una_palabra():
    """"Tomate frito" no es "Tomates frescos": sumarle el stock seria un error
    silencioso."""
    assert _buscar("Tomate frito Solis 725 grs") is None


def test_producto_que_no_esta_en_el_catalogo_no_empareja():
    assert _buscar("Desodorante Axe Leather 150 ml") is None
    assert _buscar("XYZ123 Articulo inexistente") is None


def test_ruido_de_ocr_dentro_de_las_palabras_no_impide_emparejar():
    """El OCR mete "€" y "@" dentro de las palabras; con el resto del nombre
    intacto ("1L") sigue estando claro de que producto se trata."""
    resultado = _buscar("L€ch€ €nt€ra 1L")
    assert resultado is not None
    assert resultado["id"] == 1


def test_nombre_destrozado_por_el_ocr_se_deja_como_articulo_nuevo():
    """Sin nada reconocible que compartir con el catalogo no hay forma de
    saber a que producto se refiere: mejor articulo nuevo que adivinar mal."""
    assert _buscar("B4RR1T4S C3RE4L") is None
    assert _buscar("Xy@z# qq") is None


def test_nombre_demasiado_corto_no_empareja():
    assert _buscar("L") is None
    assert _buscar("") is None


def test_devuelve_alternativas_para_que_el_usuario_corrija():
    resultado = _buscar("Manzanas")
    assert resultado is not None
    assert resultado["id"] == 4
    assert isinstance(resultado["alternativas"], list)
