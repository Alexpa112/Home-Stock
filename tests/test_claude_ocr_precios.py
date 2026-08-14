"""El motor de vision debe extraer precios, totales y confianza, no solo
nombre/cantidad.

Antes el esquema solo pedia nombre_ticket/cantidad/unidad/producto_id, asi que
rutas/tickets.py rellenaba precio_unitario=0, precio_total=0 y
confianza_nombre=100 fijos: la app mostraba confianza del 100% para todo y
nunca un precio.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.claude_ocr import (
    _ESQUEMA_RESPUESTA,
    _normalizar_items,
    _normalizar_totales,
)


def _campos_del_esquema():
    return _ESQUEMA_RESPUESTA["properties"]["productos"]["items"]["properties"]


def test_el_esquema_pide_precios_y_confianza():
    campos = _campos_del_esquema()
    for campo in ("precio_unitario", "precio_total", "confianza"):
        assert campo in campos, f"el esquema no pide {campo}"


def test_el_esquema_pide_los_totales_del_pie():
    totales = _ESQUEMA_RESPUESTA["properties"]["totales"]["properties"]
    assert set(totales) == {"subtotal", "impuestos", "total"}


def test_los_precios_admiten_null_en_el_esquema():
    # Un ticket que solo imprime el importe de linea no debe forzar al modelo
    # a inventarse el precio unitario.
    campos = _campos_del_esquema()
    tipos = [t["type"] for t in campos["precio_unitario"]["anyOf"]]
    assert "null" in tipos


def test_caso_1_articulo_con_cantidad_y_precio():
    items = _normalizar_items([{
        "nombre_ticket": "LECHE ENTERA 1L",
        "cantidad": 2, "unidad": "ud", "producto_id": None,
        "precio_unitario": 1.25, "precio_total": 2.50, "confianza": 0.95,
    }], ids_catalogo=set())

    assert len(items) == 1
    item = items[0]
    assert item["nombre_ticket"] == "LECHE ENTERA 1L"
    assert item["cantidad"] == 2
    assert item["precio_unitario"] == 1.25
    assert item["precio_total"] == 2.50
    assert item["coherencia_precio"] == "cuadra"
    assert item["confianza"] > 0.9


def test_caso_6_precio_decimal_con_coma_se_normaliza_a_punto():
    items = _normalizar_items([{
        "nombre_ticket": "PAN", "cantidad": 1, "unidad": "ud",
        "producto_id": None, "precio_total": "1,25", "precio_unitario": None,
        "confianza": 0.9,
    }], ids_catalogo=set())

    assert items[0]["precio_total"] == 1.25


def test_precio_no_impreso_se_queda_en_none_y_se_expone_el_derivado_aparte():
    # Punto 9 del encargo: si el ticket solo muestra el total, no inventar el
    # precio unitario. El calculo se ofrece por separado, marcado como tal.
    items = _normalizar_items([{
        "nombre_ticket": "PAN INTEGRAL", "cantidad": 2, "unidad": "ud",
        "producto_id": None, "precio_unitario": None, "precio_total": 2.98,
        "confianza": 0.9,
    }], ids_catalogo=set())

    item = items[0]
    assert item["precio_unitario"] is None
    assert item["precio_unitario_derivado"] == 1.49


def test_linea_incoherente_baja_la_confianza():
    coherente = _normalizar_items([{
        "nombre_ticket": "A", "cantidad": 2, "unidad": "ud", "producto_id": None,
        "precio_unitario": 1.25, "precio_total": 2.50, "confianza": 0.9,
    }], ids_catalogo=set())[0]
    incoherente = _normalizar_items([{
        "nombre_ticket": "A", "cantidad": 2, "unidad": "ud", "producto_id": None,
        "precio_unitario": 1.25, "precio_total": 99.0, "confianza": 0.9,
    }], ids_catalogo=set())[0]

    assert incoherente["confianza"] < coherente["confianza"]
    assert incoherente["coherencia_precio"] != "cuadra"


def test_respuesta_sin_los_campos_nuevos_sigue_funcionando():
    # Compatibilidad: un SDK antiguo (camino sin esquema) o un modelo que
    # omita los campos no debe romper el analisis del ticket.
    items = _normalizar_items([{
        "nombre_ticket": "LECHE", "cantidad": 1, "unidad": "ud", "producto_id": None,
    }], ids_catalogo=set())

    assert len(items) == 1
    assert items[0]["precio_unitario"] is None
    assert items[0]["precio_total"] is None
    assert items[0]["confianza"] == 0.5  # valor neutro, sin dato del modelo


def test_caso_7_los_totales_no_son_productos():
    # SUBTOTAL/IVA/TOTAL van en su propio objeto, no como articulos.
    totales = _normalizar_totales({"subtotal": "12,50", "impuestos": "0,50", "total": "13,00"})

    assert totales == {"subtotal": 12.50, "impuestos": 0.50, "total": 13.00}


def test_totales_ausentes_son_none():
    assert _normalizar_totales(None) == {"subtotal": None, "impuestos": None, "total": None}
