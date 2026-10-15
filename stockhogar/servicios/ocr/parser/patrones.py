"""Expresiones regulares del parser y conversion de importes."""
import re


class PatronesParser:
    def _cargar_patrones(self):
        # "4 x 0,55", "6X0.42": multiplicador de cantidad delante de un precio
        # (formato de Carrefour/Lidl: "YOGUR NATURAL   4 x 0,55   2,20"). Exige
        # decimales detras para no confundirlo con la promocion "2x1".
        self.regex_multiplicador = re.compile(r'(?<![\d,.])(\d{1,3})\s*[-+%.]?\s*[xX×]{1,2}\s*(?=\d+[.,]\d{2})')

        # Regex mejorados
        self.regex_cantidad = re.compile(
            r'(\d+[.,]?\d*)\s*([a-záéíóúñ\.]+)',
            re.IGNORECASE | re.UNICODE
        )
        # (?!\d) al final: sin el, un peso con 3 decimales (p.ej. "0,850 kg",
        # habitual en articulos a granel) se leia como precio "0,85" mas un
        # "0" suelto, y ese "0,85" espurio se colaba como precio_unitario
        # real (ver _extraer_precios) en vez de descartarse.
        self.regex_precio = re.compile(
            r'(?<![A-WYZa-wyzáéíóúñ])(\d*[.,]\d{2})(?!\d)\s*(€|\$)?',  # la x de "2x1,50" no pega el precio al nombre
            re.IGNORECASE
        )
        self.regex_precio_unitario = re.compile(
            r'@\s*(\d+[.,]\d+)\s*(€|\/kg|\/l|\/ud)?',
            re.IGNORECASE
        )

        self.regex_cantidad_implicita = re.compile(
            r'(?<![\d,.])(\d{1,2})\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})(?!\d)'
        )
        self.regex_detalle_multiplicador = re.compile(
            r'(\d{1,3})\s*[xX×]{1,2}\s*(\d+[.,]\d{2})\s*(?:€|eur)?', re.IGNORECASE
        )

        # "DETERGENTE LIQ  2 UN  11,98" (Alcampo, Eroski, Consum): la cantidad va
        # tras el nombre, marcada con UN/UD/UDS, y delante del importe.
        self.regex_cantidad_un = re.compile(
            r'(?<![\d,.])(\d{1,3})\s*(?:un|uds?|u|unid(?:ades)?)\b\.?(?=\s+\d+[.,]\d{2}|\s*$)',
            re.IGNORECASE
        )
        # "1,088 kg x 14,50/kg" en su propio renglon (Aldi, Dia): peso y precio por kilo
        # del articulo anterior.
        self.regex_detalle_peso = re.compile(
            r'(\d+[.,]\d{1,3})\s*(kg|g|l|ml)\s*[xX×]?\s*(?:(\d+[.,]\d{2})\s*(?:€|eur)?\s*(?:/\s*(?:kg|g|l|ml|ud))?)?',
            re.IGNORECASE
        )
        # Renglon con solo un importe ("15,78"): el precio del articulo anterior cuando
        # el nombre y el peso ocupan un renglon y el importe cae en el siguiente.
        self.regex_solo_precio = re.compile(r'(\d+[.,]\d{2})\s*(?:€|eur)?\s*[A-Za-z]?')

        # Fila numerica de un articulo cuyo NOMBRE va en otra linea (facturas de
        # cash & carry, ferreterias, tickets en varias lineas):
        #   "9557031100236 1 X 3.02 3.02"   o   "1072 1 80.00 80.00 80.00"
        # codigo opcional, cantidad, uno o dos importes unitarios y el importe final.
        self.regex_fila_numerica = re.compile(
            r'^\s*(?:\d{4,14}\s+)?(?:(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:nos|pcs?|set|sets|units?|ea|pkt|x|\*)?\s*[xX*]?\s+)?((?:\d+[.,]\d{1,2}\s+)*)(\d+[.,]\d{2})\s*[*A-Za-z]{0,2}\s*$',
            re.IGNORECASE,
        )

        # Patrones típicos de cabecera (nombre de tienda, dirección, CIF, teléfono)
        self._regex_importe_final = re.compile(
            r'\d[.,]\d{2}\s*(?:€|eur|rm)?\s*[A-Za-z]{0,2}\s*(?:\*|\d{1,2}\s*%)?\s*$', re.IGNORECASE
        )
        self.regex_cif_nif = re.compile(r'\b[A-Z]\d{7,8}[A-Z0-9]?\b')
        self.regex_telefono = re.compile(r'\b\d{9}\b')
        self.regex_cod_postal = re.compile(r'\b\d{5}\b')

        # Cantidad con unidad real (kg, l, ud...), a diferencia de
        # regex_cantidad que acepta cualquier palabra tras el número
        # (útil para no confundir "28100 Alcobendas" con una cantidad).
        unidades_alt = '|'.join(sorted(self.unidades_map.keys(), key=len, reverse=True))
        self.regex_cantidad_unidad = re.compile(
            r'\d+[.,]?\d*\s*(?:' + unidades_alt + r')\b\.?',
            re.IGNORECASE | re.UNICODE
        )
        self.palabras_cabecera = {
            "s.a.", "s.l.", "s.a", "s.l", "sl", "sa", "s.coop", "avda", "avenida",
            "c/", "calle", "polígono", "poligono", "cif", "nif", "tel", "telefono",
            "teléfono", "fax", "www", "http", ".com", ".es",
            "supermercado", "tienda", "mercado", "shop", "comercio", "empresa",
            "domicilio", "dirección", "dir", "provincia", "piso", "planta",
            "plaza", "paseo", "ronda", "camino", "carretera", "ctra", "polígono", "pol.", "travesía",
        }

        # Cantidad "suelta" al principio de la línea (p.ej. "2 COCA COLA 1,80"):
        # un entero corto seguido de espacio y letra, típico de tickets donde
        # la cantidad va delante del nombre del artículo sin unidad explícita.
        self.regex_cantidad_inicial = re.compile(
            r'^(\d{1,3})\s+(?=[a-záéíóúñ])',
            re.IGNORECASE | re.UNICODE
        )

    # Importe con ":" o ";" en lugar de la coma decimal ("2:45", "1;85"): la
    # fuente de punto de las impresoras termicas hace que el OCR lea la coma
    # como dos puntos. Se aplica SOLO a las lineas de la zona de productos (una
    # hora como "18:32" esta en la cabecera, que ya queda fuera).
    _regex_decimal_mal_leido = re.compile(r'(?<=\d)[:;](?=\d{2}(?!\d))')

    # "1, 853kg", "0, 885 kg": el OCR separa la coma del peso.
    _regex_peso_con_espacio = re.compile(r'(?<=\d)([,.])\s+(?=\d{3}\s*(?:kg|g|l|ml)\b)', re.IGNORECASE)

    _regex_articulo_con_descuento = re.compile(
        r'^(?P<art>.*?\d[.,]\d{2})\s+(?P<desc>(?:desc\.?|dto\.?|descuento)\s*[-−–]\s*\d{1,4}[.,]\d{2}.*)$', re.IGNORECASE
    )

    _regex_descuento_negativo = re.compile(r'(?<![\d,.])[-−–]\s*(\d{1,4}[.,]\d{2})\s*(?:€|eur)?\s*[A-Za-z]?\s*$')

    _regex_palabra_descuento = re.compile(
        r'^\W*(?:desc\.?|dto\.?|descuento|promo|promoci[oó]n|oferta|cup[oó]n|ahorro|lidl\s+plus)\b', re.IGNORECASE
    )

    _regex_palabras_de_descuento = re.compile(
        r'\b(?:desc|dto|descuento|promo|promoci[oó]n|oferta|cup[oó]n|ahorro|lidl|plus|total|compra|x)\b\.?', re.IGNORECASE
    )

    # Ambos grupos son opcionales a proposito: tras limpiar el nombre puede
    # quedar solo la divisa ("Eur", cuando la limpieza ya se ha llevado el
    # "/kg" de "1,89 EUR/kg"), solo la unidad ("Kg") o la combinacion
    # ("Eur/Kg"). Los tres casos significan lo mismo: no queda nombre.
    _regex_nombre_vacio = re.compile(
        r'^(eur|usd|€|\$)?\s*/?\s*(kg|g|l|ml|ud|uds)?\.?$', re.IGNORECASE
    )

    # Palabras que acompañan a un producto pero no nombran ninguno. No pueden
    # estar en `palabras_ignorar` (eso descartaria la linea entera y con ella
    # articulos reales como "OFERTA LECHE DESNATADA 1L"), asi que se filtran
    # aqui: si al quitarlas no queda nada, la linea era solo el aviso de la
    # promocion o el descuento.
    _PALABRAS_SIN_PRODUCTO = {
        "oferta", "ofertas", "promocion", "promociones", "promo", "dto",
        "descuento", "descuentos", "rebaja", "rebajas", "ahorro", "ahorras",
        "cupon", "vale", "regalo", "gratis", "unidad", "unidades", "und",
    }

    _regex_tokens = re.compile(r'[^0-9a-záéíóúñü]+', re.IGNORECASE | re.UNICODE)

    _regex_token_prescindible = re.compile(r'\d+\s*x\s*\d+|\d+', re.IGNORECASE)

    _RUIDO_DETALLE = ("eur", "euro", "euros", "usd", "kg", "g", "gr", "l", "lt", "ml", "ud", "uds", "x", "por")

    # Palabras de cierre/cortesia/impuestos que, aunque el OCR las escriba mal
    # ("Totai", "Totqty", "Sub Tal", "Discounl"), identifican una linea que NO es un
    # articulo. Se comparan con tolerancia sobre cada palabra del nombre.
    _PALABRAS_CONTROL_FUZZY = (
        "total", "subtotal", "discount", "rounding", "change", "balance", "summary", "tendered",
        "amount", "invoice", "receipt", "cashier", "thank", "payment", "customer", "member", "voucher",
        "points", "gst", "tax", "cambio", "efectivo", "tarjeta", "descuento", "importe",
        "gracias", "factura", "iva", "troco", "totale", "summe", "especes", "monnaie", "totqty", "qty",
    )

    def _normalizar_decimal(self, linea: str) -> str:
        linea = self._regex_peso_con_espacio.sub(r'\1', linea)
        linea = re.sub(r'(?i)\b(?:rm|eur|usd)\s*(?=\d)', ' ', linea)  # "RM1.25" 
        # "7.0 0", "6.0 0": el OCR separa la ultima cifra decimal del resto
        linea = re.sub(r'(?<![\d.,])(\d{1,5}[.,]\d)\s(\d)(?![\d.,])', r'\1\2', linea)
        return self._regex_decimal_mal_leido.sub(',', linea)

    def _parsear_precio(self, precio_str: str) -> float:
        """Convierte string de precio a float."""
        precio_str = precio_str.replace('€', '').replace('$', '').strip()
        precio_str = precio_str.replace(',', '.')
        try:
            valor = float(precio_str)
        except ValueError:
            return 0
        # Un importe de ticket nunca es infinito ni astronomico (texto basura).
        return valor if valor < 10_000_000 else 0
