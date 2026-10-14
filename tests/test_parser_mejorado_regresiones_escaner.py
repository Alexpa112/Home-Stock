"""Regresiones del parser del escaner local, halladas al pasar tickets sinteticos
por Tesseract de verdad (formatos Mercadona, Carrefour y Lidl).

Todas son de la forma "el texto OCR estaba bien y el articulo se perdia o salia
mal": palabras de control buscadas como subcadena, lineas de detalle de peso o
de "N x precio", ruido de OCR convertido en articulo y decimales mal leidos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado, TipoUnidad


def _parsear(texto):
    return ParserMejorado().parsear(texto)


def _por_nombre(texto):
    return {p.nombre: p for p in _parsear(texto)}


# --------------------------------------------------- palabras de control completas
def test_el_aceite_de_oliva_no_se_descarta_por_contener_iva():
    """"iva" (el impuesto) casaba como SUBCADENA de "OLIVA": se perdia toda
    linea de aceite de oliva, de los articulos mas comunes."""
    productos = _por_nombre("1 ACEITE OLIVA VIRGEN 7,95\n1 PAN 1,00\nTOTAL 8,95\n")
    assert "Aceite Oliva Virgen" in productos
    assert productos["Aceite Oliva Virgen"].precio_total == 7.95


def test_articulos_con_una_palabra_de_control_DENTRO_de_otra_no_se_pierden():
    """La palabra de control se busca completa: "iva" dentro de OLIVAS,
    ACTIVA, ALTERNATIVA no es el impuesto. (Una palabra de control suelta, como
    "CAJA" o "CLUB" en "CAJA HUEVOS", SI se sigue descartando: esta en la lista a
    proposito y aflojarlo mas dejaria pasar lineas de control.)"""
    texto = (
        "MERCADONA S.A.\n"
        "1 OLIVAS RELLENAS 1,40\n"
        "1 LECHE ACTIVA 1,99\n"
        "1 BEBIDA ALTERNATIVA 2,20\n"
        "TOTAL 5,59\n"
    )
    nombres = set(_por_nombre(texto))
    assert {"Olivas Rellenas", "Leche Activa", "Bebida Alternativa"} <= nombres


def test_las_lineas_de_control_reales_siguen_descartandose():
    texto = (
        "1 LECHE ENTERA 1L 0,89\n"
        "IVA 10% 0,08\n"
        "SUBTOTAL 0,89\n"
        "TOTAL 0,89\n"
    )
    assert list(_por_nombre(texto)) == ["Leche Entera"]


def test_plural_de_palabra_de_control_tambien_se_descarta():
    assert _parsear("1 LECHE 0,89\nDESCUENTOS 0,10\nPUNTOS 12\nTOTAL 0,79\n")[0].nombre == "Leche"
    assert len(_parsear("1 LECHE 0,89\nDESCUENTOS 0,10\nPUNTOS 12\nTOTAL 0,79\n")) == 1


# --------------------------------------------------- articulos a peso (linea de detalle)
def test_peso_en_formato_carrefour_con_x_se_une_al_articulo_anterior():
    """"0,850 kg x 1,89 EUR/kg" dejaba el nombre "X Eur": un articulo fantasma,
    y el producto real se quedaba en 1 ud."""
    productos = _por_nombre("TOMATE PERA 1,61\n   0,850 kg x 1,89 EUR/kg\nPAN 0,90\nTOTAL 2,51\n")
    assert set(productos) == {"Tomate Pera", "Pan"}
    tomate = productos["Tomate Pera"]
    assert tomate.cantidad == 0.85 and tomate.unidad == TipoUnidad.KILOGRAMO
    assert tomate.precio_total == 1.61, "el importe de la linea no debe pisarse con el precio por kg"
    assert tomate.precio_unitario == 1.89


def test_peso_en_formato_mercadona_sigue_funcionando():
    productos = _por_nombre("MERCADONA S.A.\n1 TOMATE PERA\n0,850 kg 1,89 EUR/kg 1,61\nTOTAL 1,61\n")
    tomate = productos["Tomate Pera"]
    assert tomate.cantidad == 0.85 and tomate.unidad == TipoUnidad.KILOGRAMO
    assert tomate.precio_unitario == 1.89 and tomate.precio_total == 1.61


def test_residuos_de_ocr_en_la_linea_de_detalle_no_crean_articulos():
    for residuo in ("0,850 kg Eur/Kkg 1,89", "0,850 kg . Eur 1,89", "0,850 kg x Eur ) 1,89"):
        productos = _parsear(f"PLATANO 1,61\n{residuo}\nTOTAL 1,61\n")
        assert [p.nombre for p in productos] == ["Platano"], residuo


# --------------------------------------------------- "N x precio"
def test_multiplicador_en_la_misma_linea():
    yogur = _por_nombre("YOGUR NATURAL   4 x 0,55   2,20\nTOTAL 2,20\n")["Yogur Natural"]
    assert yogur.cantidad == 4 and yogur.unidad == TipoUnidad.UNIDAD
    assert yogur.precio_total == 2.20


def test_multiplicador_en_su_propia_linea_formato_lidl():
    """Linea "2 x 1,85" sin letras: la descartaba _es_linea_valida."""
    pan = _por_nombre("Pan de molde 3,70 A\n   2 x 1,85\nTotal 3,70\n")["Pan De Molde"]
    assert pan.cantidad == 2 and pan.unidad == TipoUnidad.UNIDAD
    assert pan.precio_unitario == 1.85 and pan.precio_total == 3.70


def test_multiplicador_manda_sobre_el_tamano_de_envase_del_nombre():
    agua = _por_nombre("Agua mineral 1,5L 2,52 A\n   6 x 0,42\nTotal 2,52\n")["Agua Mineral"]
    assert agua.cantidad == 6 and agua.unidad == TipoUnidad.UNIDAD


def test_ocr_que_dobla_la_x_tambien_vale():
    assert _por_nombre("PAN DE MOLDE   2 xx 1,85   3,70\nTOTAL 3,70\n")["Pan De Molde"].cantidad == 2


def test_la_promocion_2x1_no_se_toma_por_multiplicador():
    pro = _parsear("2X1 GALLETAS MARIA 1,20\nTOTAL 1,20\n")
    assert pro[0].nombre == "Galletas Maria"


def test_el_tamano_de_envase_sin_cantidad_sigue_siendo_1_litro():
    """Decision del equipo (ver test_parser_mejorado_nombre_articulo): sin
    cantidad delante, "LECHE ENTERA 1L" es 1 litro. No debe cambiar."""
    leche = _por_nombre("LECHE ENTERA 1L   1,20\nTOTAL 1,20\n")["Leche Entera"]
    assert leche.cantidad == 1 and leche.unidad == TipoUnidad.LITRO


# --------------------------------------------------- ruido de OCR
def test_el_ruido_de_sombras_y_bordes_no_se_convierte_en_articulo():
    texto = (
        "1 LECHE ENTERA 0,89\n"
        "Coocoooe.On.On.Onoeoen.Nnnnan Nooo». An» In 1,00\n"
        "Pa A A A A — — — 2,00\n"
        "£ Xx 3,00\n"
        "TOTAL 0,89\n"
    )
    assert [p.nombre for p in _parsear(texto)] == ["Leche Entera"]


def test_nombres_legitimos_cortos_o_con_simbolos_de_ocr_se_conservan():
    nombres = {p.nombre for p in _parsear("1 PAN 1,00\n1 AJO 0,40\n1 L€CH€ €NT€RA 0,89\nTOTAL 2,29\n")}
    assert {"Pan", "Ajo"} <= nombres and len(nombres) == 3


def test_un_importe_mal_leido_no_se_queda_pegado_al_nombre():
    """"2,405" (un dijito de mas) no casa con el formato de precio y acababa en
    el nombre: "Huevos Camperos 2,405"."""
    assert _por_nombre("MERCADONA S.A.\n1 HUEVOS CAMPEROS 2,405\nTOTAL 2,45\n").keys() == {"Huevos Camperos"}


def test_coma_decimal_leida_como_dos_puntos_o_punto_y_coma():
    productos = _por_nombre("MERCADONA S.A.\n1 HUEVOS CAMPEROS 2:45\n2 PAN DE MOLDE 1;85 3:70 A\nTOTAL 6,15\n")
    assert productos["Huevos Camperos"].precio_total == 2.45
    assert productos["Pan De Molde"].precio_unitario == 1.85
    assert productos["Pan De Molde"].precio_total == 3.70


def test_una_hora_de_la_cabecera_no_se_convierte_en_precio():
    productos = _parsear("MERCADONA S.A.\n12/10/2026 18:32\n1 LECHE 0,89\nTOTAL 0,89\n")
    assert [p.nombre for p in productos] == ["Leche"]


def test_cabecera_de_hipermercado_no_se_cuela_como_articulo():
    """Regresion de mi propio cambio: "HIPERMERCADO" debe seguir reconociendose
    como cabecera (por subcadena) aunque el OCR estropee la linea del CIF."""
    productos = _parsear(
        "CARREFOUR HIPERMERCADO\nAvda. de America 45 Madrid\n=====\nPAN 0,90\nTOTAL 0,90\n"
    )
    assert [p.nombre for p in productos] == ["Pan"]
