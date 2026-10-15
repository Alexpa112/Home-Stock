"""Cuadre de un ticket leido con OCR local contra el TOTAL impreso.

Un OCR local se equivoca en digitos sueltos ("4" por "1", un importe cortado).
El total del pie del ticket es la comprobacion mas fiable que hay: la suma de
los articulos tiene que dar ese total. Aqui se usa para dos cosas:

1. Avisar (advertencia + dato `cuadre`) cuando no cuadra, para que el usuario
   mire el ticket antes de aceptar.
2. Rellenar el importe de la UNICA linea que no lo trae (lo que falta para llegar
   al total). Queda marcado en el articulo (`corregido_por_total`).

No se corrigen cantidades a partir del total: una linea que falte en el ticket
hace que "encaje" casi cualquier cantidad (se vio: un 2 pasaba a 5). La
cantidad ya se cuadra linea a linea en el parser (cantidad x unitario = importe).
"""
import re
from typing import Dict, List, Optional, Tuple

from .validacion_importes import validar_totales

_RE_LINEA_TOTAL = re.compile(r"\b(total|suma)\b", re.IGNORECASE)
_RE_NO_ES_EL_TOTAL = re.compile(
    r"subtotal|ahorro|descuent|dto|iva|impuesto|art[ií]culos|\bart\b|puntos|cambio|entregado|promoci|efectivo|tarjeta|sigue|visa", re.IGNORECASE
)
_RE_IMPORTE_FINAL = re.compile(r"(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,6}[.,]\d{2})\s*(?:€|eur)?\s*[A-Za-z]?\s*$", re.IGNORECASE)
_TOLERANCIA = 0.02
# Solo se quita una linea que PARECE de cierre ("Sub Totai", "Iva", "Efectivo"): un
# articulo cualquiera con ese importe es mas probable que sea un importe mal leido en otro.
# Tambien una "linea" con cifras en el nombre ("Tda0421 Caja 03 12/10/26"): un ticket, no un articulo.
_RE_PARECE_LINEA_DE_CIERRE = re.compile(
    r"sub|tot|iva|impuest|pago|cambio|efectivo|tarjeta|entreg|base|cuota|suma|visa", re.IGNORECASE
)


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
                importe = m.group(1)
                if re.search(r"\.\d{3},", importe):  # 1.234,56 (separador de miles)
                    importe = importe.replace(".", "")
                candidatos.append(float(importe.replace(",", ".")))
            except ValueError:
                continue
    return max(candidatos) if candidatos else None


def _importe(item: Dict) -> Optional[float]:
    valor = item.get("precio_total")
    return float(valor) if valor else None


def _quitar_lineas_que_no_son_articulos(items: List[Dict], total: float) -> List[Dict]:
    """Si la suma SUPERA el total, algo que no es un articulo se ha colado (un
    subtotal, un importe de impuestos, un "pago"). Se quita solo si hay UNA forma de
    cuadrar quitando una linea sin reconocer, y el exceso es de 1 EUR o mas (un exceso
    menor suele ser un descuento sin aplicar, no una linea de mas)."""
    importes = [_importe(i) for i in items]
    if any(v is None for v in importes):
        return items
    exceso = round(sum(importes) - total, 2)
    if exceso < 1.0:
        return items
    candidatos = [
        k for k, item in enumerate(items)
        if abs(importes[k] - exceso) <= _TOLERANCIA
        and item.get("origen_nombre") not in ("catalogo", "hogar")
        and not item.get("producto_id")
        and (_RE_PARECE_LINEA_DE_CIERRE.search(item.get("nombre") or "") or re.search(r"\d", item.get("nombre") or ""))
    ]
    if len(candidatos) != 1:
        return items
    k = candidatos[0]
    return [i for n, i in enumerate(items) if n != k]


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

    items = _quitar_lineas_que_no_son_articulos(items, total)
    importes = [_importe(i) for i in items]

    resumen = validar_totales(
        [{"precio_total": _importe(i)} for i in items], total
    )
    return items, resumen
