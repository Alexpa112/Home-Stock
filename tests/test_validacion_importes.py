"""Tests de validacion_importes: normalización de importes y comprobación
aritmética del ticket. Sin imagen, sin API, sin base de datos."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.validacion_importes import (
    coherencia_linea,
    confianza_item,
    normalizar_importe,
    precio_unitario_derivado,
    validar_totales,
)


# --- normalizar_importe -------------------------------------------------

def test_normaliza_los_formatos_de_importe_de_un_ticket_espanol():
    assert normalizar_importe("1,99") == 1.99
    assert normalizar_importe("1.99") == 1.99
    assert normalizar_importe("€1.99") == 1.99
    assert normalizar_importe("1,99€") == 1.99
    assert normalizar_importe("1,99 EUR") == 1.99
    assert normalizar_importe("  1,99  ") == 1.99


def test_normaliza_numeros_nativos():
    assert normalizar_importe(1.99) == 1.99
    assert normalizar_importe(2) == 2.0


def test_separador_de_millares_no_se_confunde_con_decimal():
    # Factura de mayorista: "1.250,00" son mil doscientos cincuenta euros.
    assert normalizar_importe("1.250,00") == 1250.00
    assert normalizar_importe("1 250,00") == 1250.00


def test_importe_negativo_de_un_descuento():
    assert normalizar_importe("-0,50") == -0.50


def test_ausencia_de_importe_es_none_no_cero():
    # 0 significaria "gratis"; None significa "el ticket no lo dice".
    assert normalizar_importe(None) is None
    assert normalizar_importe("") is None
    assert normalizar_importe("   ") is None
    assert normalizar_importe("sin precio") is None
    assert normalizar_importe(True) is None


# --- coherencia_linea ---------------------------------------------------

def test_linea_que_cuadra():
    coherente, motivo = coherencia_linea(2, 1.25, 2.50)
    assert coherente
    assert motivo == "cuadra"


def test_linea_que_no_cuadra_se_detecta():
    coherente, motivo = coherencia_linea(2, 1.25, 9.99)
    assert not coherente
    assert "9.99" in motivo


def test_redondeo_de_un_centimo_se_tolera():
    # 0,85 kg x 1,89 EUR/kg = 1,6065 -> el ticket imprime 1,61.
    coherente, _ = coherencia_linea(0.85, 1.89, 1.61)
    assert coherente


def test_sin_todos_los_datos_no_se_afirma_incoherencia():
    # Falta el precio unitario: no se puede concluir que haya un error.
    coherente, motivo = coherencia_linea(2, None, 2.50)
    assert coherente
    assert motivo == "sin_datos"


# --- precio_unitario_derivado -------------------------------------------

def test_precio_unitario_derivado_es_un_calculo_aparte():
    assert precio_unitario_derivado(2, 2.50) == 1.25
    assert precio_unitario_derivado(0, 2.50) is None
    assert precio_unitario_derivado(2, None) is None


# --- validar_totales ----------------------------------------------------

def test_suma_que_cuadra_con_el_total_impreso():
    items = [{"precio_total": 2.50}, {"precio_total": 1.49}]
    resultado = validar_totales(items, 3.99)

    assert resultado["comprobado"]
    assert resultado["cuadra"]
    assert resultado["suma_articulos"] == 3.99
    assert resultado["diferencia"] == 0.0


def test_suma_que_no_cuadra_se_detecta():
    # Falta un artículo: la suma se queda corta respecto al total impreso.
    items = [{"precio_total": 2.50}, {"precio_total": 1.49}]
    resultado = validar_totales(items, 10.00)

    assert resultado["comprobado"]
    assert not resultado["cuadra"]
    assert resultado["diferencia"] == -6.01


def test_no_se_comprueba_si_falta_el_importe_de_alguna_linea():
    # Con una linea sin importe la suma es incompleta por construccion:
    # su desajuste no probaria ningun error de extraccion.
    items = [{"precio_total": 2.50}, {"precio_total": None}]
    resultado = validar_totales(items, 10.00)

    assert not resultado["comprobado"]
    assert resultado["cuadra"] is None


def test_no_se_comprueba_sin_total_impreso():
    resultado = validar_totales([{"precio_total": 2.50}], None)
    assert not resultado["comprobado"]


# --- confianza_item -----------------------------------------------------

def test_incoherencia_aritmetica_penaliza_la_confianza():
    alta = confianza_item(0.95, coherente=True, hay_match_catalogo=False, tiene_precio=True)
    baja = confianza_item(0.95, coherente=False, hay_match_catalogo=False, tiene_precio=True)
    assert baja < alta


def test_confianza_se_mantiene_en_el_rango_0_1():
    assert confianza_item(1.0, True, True, True) <= 1.0
    assert confianza_item(0.0, False, False, False) >= 0.0


def test_sin_confianza_del_modelo_se_parte_de_un_valor_neutro():
    assert confianza_item(None, True, False, False) == 0.5
