"""Limpieza del nombre del articulo y confianza de la lectura."""
from .modelos import TipoUnidad
import re


class NombresParser:
    def _limpiar_nombre(self, linea: str, cantidad_texto: str, precio_total: float) -> str:
        """Limpia nombre del producto removiendo cantidad y precio.

        Solo se elimina cantidad+unidad cuando la unidad es real (kg, l,
        ud...), o la cantidad suelta al principio de la línea. Nunca se
        elimina un número seguido de una palabra cualquiera, porque eso
        rompería el nombre del artículo (p.ej. "2 COCA COLA" -> "Cola").
        """

        # Quitar código de artículo al principio de la línea (p.ej.
        # "02728-01 OR| TOMATE FRITO..."), habitual en facturas de
        # mayorista/cash and carry: sin esto el código quedaba pegado al
        # nombre del producto.
        nombre = re.sub(
            r'^\d{4,6}-\d{1,3}\s*(?:or\|?|\|)?\s*', '', linea,
            flags=re.IGNORECASE
        )

        # Codigo de articulo / EAN al principio ("400137 MEJILLON ESCABECHE"): 5 a 13
        # digitos seguidos nunca son una cantidad.
        nombre = re.sub(r'^[\-–•*]+\s*', '', nombre)
        codigo = re.match(r'^([0-9OoIl]{4,13})\s+(?=[A-Za-záéíóúñ])', nombre)
        if codigo and sum(c.isdigit() for c in codigo.group(1)) >= 3:  # "40OOOO": ceros leidos como O
            nombre = nombre[codigo.end():]

        # Quitar precio unitario (@1.20€/kg)
        nombre = re.sub(self.regex_precio_unitario, '', nombre)

        # Quitar precios primero: si no, un precio sin el "0" inicial
        # (p.ej. ",70") deja sueltos sus dígitos y la regex de cantidad
        # los confunde con una cantidad+unidad (p.ej. "70 C").
        nombre = re.sub(self.regex_precio, '', nombre)

        # Multiplicador con el unitario ilegible al final ("LONCHAS 4x 5,9%", "BAÑO 4x2,")
        nombre = re.sub(r'\s+\d{1,2}\s*[-+%.]?\s*[xX×]{1,2}\.?[\d,.%:;\s]*$', '', nombre)

        # Quitar el multiplicador "4 x" que queda tras quitar el precio
        # (p.ej. "YOGUR NATURAL 4 x 0,55 2,20" -> "YOGUR NATURAL")
        nombre = re.sub(r'(?<![\w])\d{1,3}\s*[xX×]{1,2}(?=\s|$)', ' ', nombre)

        # Quitar la cantidad marcada con UN/UD ("2 UN")
        nombre = re.sub(self.regex_cantidad_un, ' ', nombre)

        # Restos de un multiplicador mal leido pegado a basura ("2+T4X", "4%x")
        nombre = re.sub(r'(?<=\s)[\w+%.\-]*\d[\w+%.\-]*[xX×](?=\s|$)', ' ', nombre)

        # Quitar cantidad con unidad real
        nombre = re.sub(self.regex_cantidad_unidad, '', nombre)

        # Quitar el peso suelto del principio ("1,577 MORTADELA")
        nombre = re.sub(r'^\d{1,3}[.,]\d{3}\s+(?:\d\s+)?(?=[a-záéíóúñ])', '', nombre, flags=re.IGNORECASE | re.UNICODE)

        # Quitar cantidad suelta al principio de la línea (p.ej. "2 Coca Cola")
        nombre = self.regex_cantidad_inicial.sub('', nombre)

        # Quitar marcador de promocion tipo "2x1"/"3x2" al principio
        # (p.ej. "2X1 GALLETAS MARIA" -> "Galletas Maria"); la promocion ya
        # se detecta aparte sobre la linea original, no hace falta dejarla
        # en el nombre del articulo.
        nombre = re.sub(r'^\d+\s*x\s*\d+\s*', '', nombre, flags=re.IGNORECASE)

        # Quitar unidad de precio sueltas al final (/kg, /l, /ud, €/kg, $/l)
        # que quedan tras quitar el precio unitario
        nombre = re.sub(r'\s*/\s*(kg|g|l|ml|ud|uds|kg|kilogramo|litro|unidad)\b\.?', '', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'\s*€\s*/\s*(kg|g|l|ml|ud|uds)', '', nombre, flags=re.IGNORECASE)

        # Quitar letra suelta de tipo de IVA al final (p.ej. "... A", "... B")
        # que queda huérfana tras quitar el precio cuando este no tenía
        # dígitos que la regex de cantidad pudiera arrastrar consigo.
        nombre = re.sub(r'\s+[a-záéíóúñ]\s*$', '', nombre, flags=re.UNICODE | re.IGNORECASE)

        # Quitar un importe mal leido que no casa con el formato de precio
        # (p.ej. "2,405" en vez de "2,45"): un numero con decimales al final
        # nunca es parte del nombre de un articulo.
        nombre = re.sub(r'\s+\d+[.,]\d+\s*$', '', nombre)

        # Quitar códigos numéricos sueltos al final (referencias, códigos de barras)
        nombre = re.sub(r'\s+\d+\s*$', '', nombre)

        # Quitar símbolos tabulares
        nombre = re.sub(r'\.{2,}|-{2,}', ' ', nombre)

        # Quitar espacios extras
        nombre = re.sub(r'\s+', ' ', nombre)

        # Title case
        nombre = nombre.strip().title()

        return nombre

    def _calcular_confianza_nombre(self, nombre: str) -> float:
        """Calcula confianza en el nombre extraído."""
        # Más largo = más confianza (menos probabilidad de OCR error)
        if len(nombre) < 3:
            return 40
        if len(nombre) < 5:
            return 60
        if len(nombre) < 15:
            return 85
        return 95

    def _calcular_confianza_cantidad(self, cantidad: float, unidad: TipoUnidad) -> float:
        """Calcula confianza en la cantidad extraída."""
        # Unidad explícita = más confianza
        confianza = 90 if unidad != TipoUnidad.DESCONOCIDA else 50

        # Cantidades razonables (1-99 para ud, 0.1-50 para kg/l)
        if unidad in (TipoUnidad.KILOGRAMO, TipoUnidad.LITRO):
            if 0.1 <= cantidad <= 50:
                return confianza
            return max(20, confianza - 40)
        else:
            if 1 <= cantidad <= 99:
                return confianza
            return max(20, confianza - 40)
