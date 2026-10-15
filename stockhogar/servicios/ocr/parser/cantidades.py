"""Cantidad, unidad e importes de una linea de articulo."""
from .modelos import TipoUnidad
import re
from typing import Tuple


class CantidadesParser:
    def _extraer_cantidad_y_unidad(
        self,
        linea: str,
        contexto_anterior: str,
        contexto_siguiente: str
    ) -> Tuple[float, TipoUnidad, str]:
        """Extrae cantidad y unidad con contexto.

        Solo se reconoce como cantidad+unidad un número seguido de una
        unidad real (kg, l, ud...), nunca de una palabra cualquiera:
        si no, un formato tipo "2 COCA COLA" confundiría "COCA" con la
        unidad y se comería la primera palabra del nombre del artículo.
        """

        patron_numero_unidad = (
            r'(\d+[.,]?\d*)\s*(' + '|'.join(
                sorted(self.unidades_map.keys(), key=len, reverse=True)
            ) + r')\b\.?'
        )

        # Cantidad-por-peso/volumen: solo cuenta si el numero+unidad va AL
        # PRINCIPIO de la linea (p.ej. "0,850 kg 1,89 EUR/kg 1,61"). Si no se
        # exige esa posicion, un formato "2 LECHE PASCUAL 1L" o "3 COCA COLA
        # 1,5L" confundia el tamaño del envase (1L, 1,5L) impreso en el
        # nombre con la cantidad realmente comprada, y el "2"/"3" del
        # principio de la linea se perdia.
        match_inicio = re.match(patron_numero_unidad, linea, re.UNICODE | re.IGNORECASE)
        if match_inicio:
            try:
                cantidad = float(match_inicio.group(1).replace(',', '.'))
                unidad_str = match_inicio.group(2).lower().strip('.')
                unidad = self.unidades_map.get(unidad_str, TipoUnidad.UNIDAD)
                return cantidad, unidad, f"{cantidad} {unidad.value}"
            except ValueError:
                pass

        # "1,577 MORTADELA 8,20" (Consum): columna de cantidad con tres decimales y sin
        # unidad. Un peso impreso asi ("0,850", "1,577") es siempre kg: ninguna
        # cantidad de unidades lleva tres decimales.
        match_peso_suelto = re.match(r'(\d{1,3}[.,]\d{3})\s+(?:\d\s+)?(?=[a-záéíóúñ])', linea, re.IGNORECASE | re.UNICODE)
        if match_peso_suelto:
            cantidad = float(match_peso_suelto.group(1).replace(',', '.'))
            if cantidad > 0:
                return cantidad, TipoUnidad.KILOGRAMO, f"{cantidad:g} kg"

        # Cantidad suelta al principio de la línea (p.ej. "2 COCA COLA 1,80",
        # "3 COCA COLA 1,5L") -> cantidad = ese número, sea cual sea la
        # unidad de envase que aparezca despues en el nombre.
        match_inicial = self.regex_cantidad_inicial.match(linea)
        if match_inicial:
            try:
                cantidad = float(match_inicial.group(1))
                if cantidad > 0:
                    return cantidad, TipoUnidad.UNIDAD, f"{cantidad:g} ud"
            except ValueError:
                pass

        # Peso a granel con tres decimales y unidad ("ATUN 3U 1,310 KG"): es lo
        # comprado, aunque el nombre lleve un "3U" de envase.
        peso_granel = re.search(r'(?<![\d,.])(\d{1,3}[.,]\d{3})\s*(kg|g|l|ml)\b', linea, re.IGNORECASE)
        if peso_granel:
            cantidad = float(peso_granel.group(1).replace(',', '.'))
            unidad = self.unidades_map.get(peso_granel.group(2).lower(), TipoUnidad.UNIDAD)
            if cantidad > 0:
                return cantidad, unidad, f"{cantidad:g} {unidad.value}"

        # "DETERGENTE LIQ  2 UN  11,98": cantidad marcada con UN/UD tras el nombre.
        match_un = self.regex_cantidad_un.search(linea)
        if match_un:
            cantidad = float(match_un.group(1))
            if cantidad > 0:
                return cantidad, TipoUnidad.UNIDAD, f"{cantidad:g} ud"

        # "QUESO LONCHAS 4x 5,9% 23,76": el importe unitario salio mal leido pero el
        # "4x" y el total se leen. Solo con un importe valido al final de la linea.
        flexible = re.search(r'(?<![\d,.])(\d{1,2})\s*[-+%.]?\s*[xX×]{1,2}\.?\s*(?=\d+\s*[.,:;%]\s*\d?\D)', linea)
        if flexible and re.search(r'\d[.,]\d{2}\s*(?:€|eur)?\s*[A-Za-z]?\s*$', linea, re.IGNORECASE):
            cantidad = float(flexible.group(1))
            if cantidad >= 2:
                return cantidad, TipoUnidad.UNIDAD, f"{cantidad:g} ud"

        # "YOGUR NATURAL  4 x 0,55  2,20" o la linea de detalle "4 x 0,55":
        # el multiplicador manda sobre el tamano de envase del nombre.
        multiplicador = self.regex_multiplicador.search(linea)
        if multiplicador:
            cantidad = float(multiplicador.group(1))
            if cantidad > 0:
                return cantidad, TipoUnidad.UNIDAD, f"{cantidad:g} ud"

        # "PAN DE MOLDE  2  1,85  3,70": Tesseract pierde a menudo la "x" suelta
        # de "2 x 1,85". Si hay un entero seguido de dos importes y N x unitario
        # cuadra con el total, la cantidad es N (no hay otra lectura posible).
        implicita = self.regex_cantidad_implicita.search(linea)
        if implicita:
            n = float(implicita.group(1))
            unitario = self._parsear_precio(implicita.group(2))
            total = self._parsear_precio(implicita.group(3))
            if n >= 2 and unitario > 0 and abs(n * unitario - total) <= 0.02 + 0.005 * n:
                return n, TipoUnidad.UNIDAD, f"{n:g} ud"

        # Un "1L", "1,5L", "500G" o "1KG" dentro del nombre es el TAMANO DEL ENVASE,
        # no lo comprado: la cantidad comprada la indica siempre el ticket (columna
        # de unidades, "N x", "N UN"...) y, si no consta, es 1 ud. Solo es una
        # cantidad real un peso/volumen vendido a granel: el que trae tres
        # decimales ("0,850 kg") o va con su precio por unidad ("/kg", "x 1,89").
        match = re.search(patron_numero_unidad, linea, re.UNICODE | re.IGNORECASE)

        if match:
            cantidad_str = match.group(1).replace(',', '.')
            unidad_str = match.group(2).lower().strip('.')
            a_granel = (
                re.fullmatch(r'\d+\.\d{3}', cantidad_str) is not None
                or re.search(r'/\s*(kg|g|l|ml)\b|(?:€|eur)\s*/', linea[match.end():], re.IGNORECASE)
                or re.search(r'[xX×]\s*\d+[.,]\d{2}', linea[match.end():])
            )
            if a_granel:
                try:
                    cantidad = float(cantidad_str)
                    if cantidad <= 0:
                        return 1.0, TipoUnidad.UNIDAD, "1 ud"
                    unidad = self.unidades_map.get(unidad_str, TipoUnidad.UNIDAD)
                    cantidad_texto = f"{cantidad} {unidad.value}"
                    return cantidad, unidad, cantidad_texto
                except ValueError:
                    pass

        # Si no hay patrón explícito, asumir 1 unidad
        return 1.0, TipoUnidad.UNIDAD, "1 ud"

    def _conciliar_cantidad_e_importes(self, linea, cantidad, unidad, cantidad_texto, p_unit, p_total):
        """cantidad x unitario = total. Solo para unidades (un peso lleva precio
        por kilo y no se cuadra asi). Devuelve (cantidad, unidad, texto, unitario)."""
        if unidad != TipoUnidad.UNIDAD:
            return cantidad, unidad, cantidad_texto, p_unit
        precios = [self._parsear_precio(m[0]) for m in re.findall(self.regex_precio, linea)]
        if len(precios) < 2:
            return cantidad, unidad, cantidad_texto, p_unit
        unitario, total = precios[-2], precios[-1]
        if unitario <= 0 or total <= 0:
            return cantidad, unidad, cantidad_texto, p_unit
        k = round(total / unitario)
        if 1 <= k <= 99 and abs(k * unitario - total) <= 0.02 + 0.005 * k:
            if k != cantidad:
                cantidad = float(k)
                cantidad_texto = f"{k:g} ud"
            return cantidad, unidad, cantidad_texto, unitario
        # No cuadra: uno de los dos importes esta mal leido. Con cantidad conocida,
        # el unitario es el que se deduce del total (el ultimo y mas fiable).
        if cantidad >= 2:
            return cantidad, unidad, cantidad_texto, round(total / cantidad, 2)
        return cantidad, unidad, cantidad_texto, p_unit

    def _extraer_precios(self, linea: str, contexto_siguiente: str) -> Tuple[float, float]:
        """Extrae precio unitario y total."""

        precios = re.findall(self.regex_precio, linea)
        precio_unitario = 0
        precio_total = 0

        if precios:
            # Último precio es probablemente el total
            precio_total = self._parsear_precio(precios[-1][0])

            # Si hay dos precios, el primero es unitario
            if len(precios) > 1:
                precio_unitario = self._parsear_precio(precios[0][0])

        # Buscar precio unitario con @ (@1.50€/kg)
        match_unitario = self.regex_precio_unitario.search(linea)
        if match_unitario:
            precio_unitario = self._parsear_precio(match_unitario.group(1))

        return precio_unitario, precio_total
