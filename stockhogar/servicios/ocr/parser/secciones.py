"""Donde empiezan y acaban los articulos de un ticket (cabecera, tabla, cierre)."""
from .modelos import _sin_tildes
import re
from typing import List


class SeccionesParser:
    def _detectar_tabla(self, lineas: List[str]) -> bool:
        """Detecta si el ticket está en formato tabla (columnas alineadas)."""
        # Contar líneas con múltiples espacios o símbolos tabulares
        lineas_tabulares = sum(
            1 for linea in lineas
            if '  ' in linea or '\t' in linea or re.search(r'\s{2,}', linea)
        )
        return lineas_tabulares > len(lineas) * 0.3

    def _detectar_fin_productos(self, lineas: List[str]) -> int:
        """Detecta el índice a partir del cual el ticket ya no contiene
        productos, sino el cierre de la compra (total, forma de pago, cambio)
        y el pie de página (fidelización, marketing, publicidad).

        Se usa la PRIMERA línea que marca el cierre de la compra (total,
        forma de pago, cambio): a partir de ahí ya no hay más productos.
        Usar la última ocurrencia es incorrecto porque el pie de ticket
        (fidelización/marketing) suele repetir esas mismas palabras
        ("Solicita tu tarjeta física", "NUM. TOTAL ART. VENDIDOS"), lo que
        desplazaría el corte hasta el final y dejaría pasar todo el pie.
        """
        regex_cierre_fuerte = re.compile(
            r'\b(total|subtotal|tot|cambio|tarjeta|efectivo|visa|mastercard)\b',
            re.IGNORECASE | re.UNICODE
        )
        regex_cierre_debil = re.compile(r'\b(importe|pago|suma)\b', re.IGNORECASE | re.UNICODE)
        regex_encabezado_tabla = re.compile(
            r'(descripcion|articulo|cantidad|cant|precio|p\.unit|total|qty|price|amount|desc|description|u\.?price|u/p)\b',
            re.IGNORECASE | re.UNICODE
        )

        for idx, linea in enumerate(lineas):
            # Si la línea contiene múltiples palabras típicas de encabezado de tabla,
            # es la cabecera, no el cierre. Saltarla.
            si_es_encabezado = len(regex_encabezado_tabla.findall(linea)) >= 2
            if si_es_encabezado:
                continue

            if regex_cierre_fuerte.search(linea):
                return idx
            if regex_cierre_debil.search(linea) and self.regex_precio.search(linea):
                return idx

        return len(lineas)

    def _detectar_inicio_productos(self, lineas: List[str], usar_primera_fila: bool = True) -> int:
        """Detecta el índice a partir del cual empiezan los productos,
        saltando la cabecera del ticket (nombre de tienda, dirección,
        CIF/NIF, teléfono, fecha/hora), que no contiene productos.

        Se considera cabecera toda línea inicial que no tenga un precio
        (##,## €) ni una cantidad con unidad, y que además "parezca"
        cabecera (contiene CIF/NIF, teléfono, código postal o palabras
        típicas de dirección/razón social). Se limita la búsqueda a las
        primeras 30 líneas para no comerse todo el ticket si el OCR no
        detecta precios (facturas de mayorista tipo "cash and carry"
        traen cabecera larga: razón social, CIF, cajero/hora, y encima la
        fila de encabezados de columna antes de la primera línea real).
        """
        limite = min(len(lineas), 30)

        # ¿Tiene el documento estructura de ticket (con precios) o es una
        # lista pelada de productos? Distingue el nombre de la tienda de la
        # primera linea (que no lleva precio, como el resto de la cabecera) del
        # primer articulo de una lista escrita a mano (donde NINGUNA linea
        # lleva precio). Sin esta distincion habia que elegir entre colar el
        # nombre de la tienda como producto o perder el primer articulo de la
        # lista.
        hay_precios = any(self.regex_precio.search(linea) for linea in lineas[:limite])

        # Fila de encabezados de columna de una factura formal
        # ("Descripción del Artículo ... Cantidad ... Precio"): marca sin
        # ambigüedad que los productos empiezan en la línea SIGUIENTE. Se
        # comprueba en una pasada aparte, antes del bucle de abajo, porque
        # ese bucle puede devolver un índice anterior (su propio fallback
        # "primera línea que no parece cabecera") antes de llegar siquiera
        # a la fila de encabezados si la cabecera es larga.
        for idx in range(limite):
            linea_lower = lineas[idx].lower()
            if "descripcion" in _sin_tildes(linea_lower) and (
                "articulo" in _sin_tildes(linea_lower) or "cantidad" in linea_lower
            ):
                return idx + 1

        # Primera FILA DE ARTICULO (importe al final de una linea que no es de control):
        # todo lo anterior es cabecera, en cualquier idioma. Si esa fila no trae nombre
        # (solo "1 x 5,20 5,20"), el nombre es la linea de encima.
        if hay_precios and usar_primera_fila:
            for idx in range(limite):
                linea = self._normalizar_decimal(lineas[idx])
                if (self._regex_importe_final.search(linea)
                        and (self._es_linea_valida(linea) or self.regex_fila_numerica.match(linea))
                        and not self._es_linea_de_cierre_fuzzy(re.sub(r'^[\d\s]+', '', linea))
                        and not re.match(r'\s*(?:sub\W*)?total', linea, re.IGNORECASE)
                        and not self.regex_cif_nif.search(linea) and not self.regex_telefono.search(linea)):
                    solo_nombre = re.sub(r'\b(?:eur|kg|kilos?|gr?|ml|l|ud|uds|un|unid|rm|nos|pcs?|set|sets|units?|ea|pkt|sr|zr)\b', ' ', linea, flags=re.IGNORECASE)
                    sin_nombre = len(re.findall(r'[a-záéíóúñ]{3,}', solo_nombre, re.IGNORECASE)) == 0
                    if sin_nombre and idx > 0:
                        # El nombre va ENCIMA de la fila numerica (hasta dos lineas: nombre y
                        # codigo); si lo que hay encima es la cabecera de columnas, va debajo.
                        inicio = idx
                        for atras in (1, 2, 3):
                            k = idx - atras
                            if k < 0:
                                break
                            previa = lineas[k]
                            if self.regex_detalle_peso.fullmatch(self._normalizar_decimal(previa).strip()):
                                inicio = k  # "1,088 kg x 14,50/kg": el nombre va aun mas arriba
                                continue
                            es_nombre = (len(re.findall(r'[a-záéíóúñ]{3,}', previa, re.IGNORECASE)) >= 1
                                         and self._es_linea_valida(previa))
                            if ((es_nombre or self._es_codigo(previa))
                                    and not self._regex_importe_final.search(previa)
                                    and not self.regex_cif_nif.search(previa)
                                    and not self.regex_telefono.search(previa)):
                                inicio = k
                            else:
                                break
                        return inicio
                    return idx
            # sin ninguna fila de articulo clara: se cae al metodo de siempre

        for idx in range(limite):
            linea = lineas[idx]
            linea_lower = linea.lower()

            tiene_precio = bool(self.regex_precio.search(linea))
            tiene_cantidad = bool(self.regex_cantidad_unidad.search(linea))
            if tiene_precio or tiene_cantidad:
                return idx

            es_cabecera = (
                bool(self.regex_cif_nif.search(linea)) or
                bool(self.regex_telefono.search(linea)) or
                bool(self.regex_cod_postal.search(linea)) or
                any(p in linea_lower for p in self.palabras_cabecera)
            )
            if not es_cabecera and (idx > 0 or not hay_precios):
                # Línea que no parece cabecera ni tiene precio/cantidad: puede
                # ser un producto cuyo precio no leyó el OCR. La primera línea
                # se protege salvo que el documento no tenga precios en ningún
                # sitio, porque en un ticket casi siempre es el nombre de la
                # tienda.
                return idx

        return limite
