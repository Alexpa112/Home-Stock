"""Cuadre de un ticket leido con OCR local contra el TOTAL impreso.

Un OCR local se equivoca en digitos sueltos ("4" por "1", un importe cortado).
El total del pie del ticket es la comprobacion mas fiable que hay: la suma de
los articulos tiene que dar ese total. Aqui se usa para dos cosas:

1. Avisar (advertencia + dato `cuadre`) cuando no cuadra, para que el usuario
   mire el ticket antes de aceptar.
2. Corregir lo que solo admite UNA solucion: la cantidad de un articulo cuyo
   precio unitario esta leido y con la que, y solo con la que, la suma sale
   exacta, o el importe de la unica linea sin importe. Cada correccion queda
   marcada en el articulo (`corregido_por_total`) para que se vea.

Nunca se toca un articulo si hay mas de una forma de cuadrar: ahi se avisa y
se deja al usuario.
"""
import re
from typing import Dict, List, Optional, Tuple

from .validacion_importes import validar_totales

_RE_LINEA_TOTAL = re.compile(r"\b(total|suma)\b", re.IGNORECASE)
_RE_NO_ES_EL_TOTAL = re.compile(
    r"subtotal|ahorro|descuent|dto|iva|impuesto|art[ií]culos|\bart\b|puntos|cambio|entregado|promoci", re.IGNORECASE
)
_RE_IMPORTE_FINAL = re.compile(r"(\d{1,6}[.,]\d{2})\s*(?:€|eur)?\s*[A-Za-z]?\s*$", re.IGNORECASE)
_TOLERANCIA = 0.02


def extraer_total_impreso(texto: str) -> Optional[float]:
    """Importe de la linea TOTAL del ticket, o None si no se lee con claridad.

    Si hay varias lineas "total" validas se toma la de mayor importe (el total a
    pagar es mayor que cualquier parcial)."""
    candidatos = []
    for linea in (texto or "").splitlines():
        if not _RE_LINEA_TOTAL.search(linea) or _RE_NO_ES_EL_TOTAL.search(linea):
            continue
        m = _RE_IMPORTE_FINAL.search(linea.strip())
        if m:
            try:
                candidatos.append(float(m.group(1).replace(",", ".")))
            except ValueError:
                continue
    return max(candidatos) if candidatos else None


def _importe(item: Dict) -> Optional[float]:
    valor = item.get("precio_total")
    return float(valor) if valor else None


def cuadrar_con_total(items: List[Dict], texto: str) -> Tuple[List[Dict], Optional[dict]]:
    """Devuelve (items, cuadre). `cuadre` es None si el ticket no trae total."""
    total = extraer_total_impreso(texto)
    if total is None or not items:
        return items, None

    importes = [_importe(i) for i in items]
    sin_importe = [k for k, v in enumerate(importes) if v is None]

    # Una unica linea sin importe: ese hueco es lo que falta para llegar al total.
    if len(sin_importe) == 1:
        k = sin_importe[0]
        resto = round(total - sum(v for v in importes if v is not None), 2)
        if resto > 0:
            items[k]["precio_total"] = resto
            items[k]["corregido_por_total"] = "importe"
            importes[k] = resto

    if all(v is not None for v in importes):
        diferencia = round(sum(importes) - total, 2)
        # Con menos de 3 articulos casi cualquier diferencia "se arregla" cambiando
        # una cantidad (y suele ser que falta una linea): ahi solo se avisa.
        if abs(diferencia) > _TOLERANCIA and len(items) >= 3:
            # Una cantidad mal leida: solo si UN articulo lo arregla y ninguno mas.
            soluciones = []
            for k, item in enumerate(items):
                unitario = item.get("precio_unitario") or 0
                if unitario <= 0 or item.get("unidad") != "ud":
                    continue
                necesario = round(importes[k] - diferencia, 2)
                n = round(necesario / unitario)
                if n >= 1 and abs(n * unitario - necesario) <= _TOLERANCIA and n != item.get("cantidad"):
                    soluciones.append((k, n, necesario))
            if len(soluciones) == 1:
                k, n, necesario = soluciones[0]
                items[k]["cantidad"] = float(n)
                items[k]["cantidad_texto"] = f"{n:g} ud"
                items[k]["cantidad_sugerida"] = float(n)
                items[k]["precio_total"] = necesario
                items[k]["corregido_por_total"] = "cantidad"

    resumen = validar_totales(
        [{"precio_total": _importe(i)} for i in items], total
    )
    return items, resumen
