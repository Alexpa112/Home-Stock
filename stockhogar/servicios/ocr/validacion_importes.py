"""Normalización de importes y validación matemática de un ticket.

Separado del motor de OCR a propósito: son reglas de aritmética y de formato
que no dependen de qué motor leyó el documento (Claude Vision o Tesseract), y
así se pueden probar sin imagen ni API.

Dos responsabilidades:

1. Normalizar importes escritos de todas las formas que aparecen en un ticket
   español ("1,99", "€1.99", "1,99 EUR") a un float, conservando el texto
   original para depuración.
2. Comprobar la coherencia aritmética de lo extraído: que
   `cantidad x precio_unitario` cuadre con `precio_total`, y que la suma de
   los artículos cuadre con el total impreso del ticket. Sirve como señal de
   confianza, NO para rellenar huecos: un precio que no está impreso se queda
   en None. Derivarlo sería inventar un dato que el documento no da.
"""
import math
import re
from typing import List, Optional, Tuple

# Tolerancia al comparar importes. Los tickets redondean a 2 decimales por
# línea, así que la suma acumula error: se admite 1 céntimo por artículo más
# un margen fijo, en vez de exigir igualdad exacta.
_TOLERANCIA_LINEA = 0.02
_TOLERANCIA_FIJA_TOTAL = 0.05
_TOLERANCIA_POR_ARTICULO = 0.01

# Un importe puede venir con símbolo delante o detrás, con el código de
# divisa, y con coma o punto decimal. El separador de millares (raro en un
# ticket de supermercado, habitual en una factura de mayorista) se retira
# antes de convertir.
_RE_IMPORTE = re.compile(
    r"""
    (?P<signo>-)?\s*
    (?:[€$]|eur|usd)?\s*
    (?P<numero>\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)
    \s*(?:[€$]|eur|usd)?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalizar_importe(valor) -> Optional[float]:
    """Convierte un importe a float, o None si no hay importe legible.

    Devuelve None (no 0) cuando el dato no consta: un 0 significaría "es
    gratis", que es una afirmación distinta de "el ticket no lo dice".
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None

    texto = str(valor).strip()
    if not texto:
        return None

    match = _RE_IMPORTE.search(texto)
    if not match:
        return None

    numero = match.group("numero")
    # Separador de millares: se quita antes de decidir el decimal. Un punto o
    # espacio seguido de exactamente 3 dígitos que no es el final de la cadena
    # es millares ("1.250,00"); el último separador con 1-2 decimales es el
    # decimal real.
    numero = re.sub(r"[.\s](?=\d{3}(?:[.,]|$))", "", numero)
    numero = numero.replace(",", ".")

    try:
        resultado = float(numero)
    except ValueError:
        return None
    if not math.isfinite(resultado):
        return None
    if match.group("signo"):
        resultado = -resultado
    return round(resultado, 2)


def coherencia_linea(
    cantidad: Optional[float],
    precio_unitario: Optional[float],
    precio_total: Optional[float],
) -> Tuple[bool, str]:
    """¿Cuadra `cantidad x precio_unitario` con `precio_total`?

    Devuelve (coherente, motivo). Si falta alguno de los tres datos no se
    puede afirmar que haya un error, así que se considera coherente con el
    motivo "sin_datos": la ausencia de un precio no es una incoherencia.
    """
    if cantidad is None or precio_unitario is None or precio_total is None:
        return True, "sin_datos"
    if cantidad <= 0:
        return True, "sin_datos"

    esperado = cantidad * precio_unitario
    # La tolerancia escala con el importe: en una línea de 200 € el redondeo
    # a 2 decimales del precio unitario por kilo se amplifica al multiplicar.
    tolerancia = max(_TOLERANCIA_LINEA, abs(esperado) * 0.01)
    if abs(esperado - precio_total) <= tolerancia:
        return True, "cuadra"
    return False, f"esperado {esperado:.2f} != total {precio_total:.2f}"


def precio_unitario_derivado(
    cantidad: Optional[float], precio_total: Optional[float]
) -> Optional[float]:
    """Precio unitario que se deduce de cantidad y total.

    NO se usa para rellenar `precio_unitario` (si el ticket no lo imprime, se
    queda en None: ver el docstring del módulo). Se expone aparte para
    mostrarlo como dato derivado en depuración y para la pantalla de revisión,
    donde queda claro que es un cálculo y no una lectura.
    """
    if cantidad is None or precio_total is None or cantidad <= 0:
        return None
    return round(precio_total / cantidad, 2)


def validar_totales(items: List[dict], total_ticket: Optional[float]) -> dict:
    """Compara la suma de los importes de los artículos con el total impreso.

    Solo se pronuncia si hay total impreso y TODOS los artículos traen
    importe: si falta el importe de alguna línea, la suma es incompleta por
    construcción y su desajuste no prueba ningún error de extracción.
    """
    totales_articulos = [i.get("precio_total") for i in items]
    con_importe = [t for t in totales_articulos if t is not None]
    suma = round(sum(con_importe), 2) if con_importe else None

    if total_ticket is None or not items or len(con_importe) != len(items):
        return {
            "comprobado": False,
            "suma_articulos": suma,
            "total_ticket": total_ticket,
            "diferencia": None,
            "cuadra": None,
        }

    diferencia = round(suma - total_ticket, 2)
    tolerancia = _TOLERANCIA_FIJA_TOTAL + _TOLERANCIA_POR_ARTICULO * len(items)
    return {
        "comprobado": True,
        "suma_articulos": suma,
        "total_ticket": total_ticket,
        "diferencia": diferencia,
        "cuadra": abs(diferencia) <= tolerancia,
    }


def confianza_item(
    confianza_modelo: Optional[float],
    coherente: bool,
    hay_match_catalogo: bool,
    tiene_precio: bool,
) -> float:
    """Combina las señales disponibles en una confianza 0..1 por artículo.

    La confianza que reporta el modelo es el punto de partida (o 0.5 si no la
    da); a partir de ahí, la incoherencia aritmética penaliza fuerte porque es
    evidencia objetiva de que algo se leyó mal, mientras que el match con el
    catálogo y tener precio suman poco: son indicios, no pruebas.
    """
    if confianza_modelo is None:
        base = 0.5
    else:
        base = max(0.0, min(1.0, float(confianza_modelo)))

    if not coherente:
        base -= 0.35
    if hay_match_catalogo:
        base += 0.05
    if tiene_precio:
        base += 0.05

    return round(max(0.0, min(1.0, base)), 3)
