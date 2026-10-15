"""
Parser mejorado de tickets con análisis contextual.

Características:
- Detección de estructuras de tabla
- Análisis de contexto de cantidades/precios
- Limpieza inteligente de errores OCR
- Normalización de unidades
- Detección de promociones
"""
import re

from rapidfuzz import fuzz
import unicodedata
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


def _sin_tildes(texto: str) -> str:
    """Quita diacríticos (á->a, ñ->n...) para comparar palabras clave sin
    depender de que el OCR acierte los acentos."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


class TipoUnidad(Enum):
    """Tipos de unidades detectadas en tickets."""
    UNIDAD = "ud"
    KILOGRAMO = "kg"
    GRAMO = "g"
    LITRO = "l"
    MILILITRO = "ml"
    PAQUETE = "paq"
    DESCONOCIDA = "desconocida"


@dataclass
class LineaTicketMejorada:
    """Línea mejorada con más contexto."""
    nombre: str
    cantidad: float
    unidad: TipoUnidad
    cantidad_texto: str  # "2 kg", "1.5 l", etc.
    precio_unitario: float = 0
    precio_total: float = 0
    confianza_nombre: float = 100
    confianza_cantidad: float = 100
    es_promocion: bool = False
    linea_original: str = ""
    descuento: float = 0  # importe descontado de precio_total (lineas "Desc. -0,30")


class ParserMejorado:
    """Parser contextual y robusto para tickets complicados."""

    def __init__(self):
        # Mapeo de variantes a unidades estándar
        self.unidades_map = {
            "kg": TipoUnidad.KILOGRAMO,
            "kilo": TipoUnidad.KILOGRAMO,
            "kilos": TipoUnidad.KILOGRAMO,
            "g": TipoUnidad.GRAMO,
            "gr": TipoUnidad.GRAMO,
            "gramo": TipoUnidad.GRAMO,
            "gramos": TipoUnidad.GRAMO,
            "l": TipoUnidad.LITRO,
            "lt": TipoUnidad.LITRO,
            "litro": TipoUnidad.LITRO,
            "litros": TipoUnidad.LITRO,
            "ml": TipoUnidad.MILILITRO,
            "mililitro": TipoUnidad.MILILITRO,
            "mililitros": TipoUnidad.MILILITRO,
            "paq": TipoUnidad.PAQUETE,
            "paquete": TipoUnidad.PAQUETE,
            "paquetes": TipoUnidad.PAQUETE,
            "pack": TipoUnidad.PAQUETE,
            "packs": TipoUnidad.PAQUETE,
            "ud": TipoUnidad.UNIDAD,
            "u": TipoUnidad.UNIDAD,
            "unidad": TipoUnidad.UNIDAD,
            "unidades": TipoUnidad.UNIDAD,
            "uds": TipoUnidad.UNIDAD,
            "pz": TipoUnidad.UNIDAD,
            "piezas": TipoUnidad.UNIDAD,
            "pieza": TipoUnidad.UNIDAD,
        }

        # Palabras que indican promoción
        self.palabras_promocion = {
            "oferta", "promo", "descuento", "rebaja", "2x1", "3x2", "dto",
            "rebajado", "superdescuento", "liquidación", "outlet"
        }

        # Palabras ignorar (no son productos)
        # NOTA: "oferta" y "promocion" se usan aquí para detectar líneas que SOLO
        # hablen del cierre de compra o fidelización, pero pueden aparecer como
        # parte del nombre del producto (p.ej. "Oferta Leche Desnatada"), así que
        # no pueden estar aquí para filtrar líneas genéricamente. Se detectan
        # aparte con _es_linea_detalle_sin_nombre() si no queda nombre real.
        self.palabras_ignorar = {
            "total", "subtotal", "importe", "pago", "cambio", "efectivo",
            "tarjeta", "visa", "mastercard", "ticket", "factura", "recibo",
            "iva", "irpf", "impuesto", "fecha", "hora", "tienda",
            "operador", "atencion", "cliente", "gracias", "vuelvo", "cuenta",
            "www", "http", "email", "tlf", "telefono", "cif", "nif", "empresa", "domicilio",
            "devolucion", "cambios", "garantia", "descuento",
            "puntos", "puntuacion", "codigo", "lote", "lotes",
            # Fidelización / programas de puntos
            "fidelidad", "fidelizacion", "monedero", "socio", "socia",
            "ha ganado", "ganado", "acumulado", "acumulados", "saldo",
            "recompensa", "recompensas", "vale descuento", "cheque descuento",
            "ahorro acumulado", "supercompra", "mi club", "club carrefour", "tarjeta club", "carrefour pass",
            "n. socio", "nº socio", "num. socio",
            # Otros idiomas (la app se usa en en/pt/fr/it/de/ca/gl): cierre de compra,
            # impuestos, cabeceras de columna y cortesia. Palabra COMPLETA.
            "cash", "change", "tax", "gst", "vat", "sst", "rounding", "amount", "qty", "price",
            "invoice", "receipt", "cashier", "terminal", "balance", "received",
            "thank", "thanks", "refundable", "returnable", "salesperson", "summary",
            "especes", "monnaie", "rendu", "tva", "merci", "caisse", "caissier", "somme",
            "troco", "numerario", "multibanco", "obrigado", "contribuinte", "pagamento", "entregue",
            "summe", "mwst", "ruckgeld", "rueckgeld", "danke", "kasse", "gegeben", "steuer", "betrag",
            "zahlung", "totale", "subtotale", "contanti", "grazie", "scontrino", "importo", "cassa",
            "efectiu", "canvi", "gràcies", "impost",
        }

        # Las palabras de control se buscan COMPLETAS, no como subcadena: con
        # `palabra in linea` la "iva" del impuesto descartaba toda linea con
        # "OLIVA" (el aceite de oliva, de los articulos mas comunes), y "caja",
        # "hora", "club", "pago" o "cuenta" se llevaban por delante "CAJA
        # HUEVOS", "CHORIZO CLUB"... Plural opcional ("descuentos", "puntos").
        self._regex_palabras_ignorar = self._compilar_palabras(self.palabras_ignorar)
        self._regex_palabras_promocion = self._compilar_palabras(self.palabras_promocion)
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

    def _normalizar_decimal(self, linea: str) -> str:
        linea = self._regex_peso_con_espacio.sub(r'\1', linea)
        linea = re.sub(r'(?i)\b(?:rm|eur|usd)\s*(?=\d)', ' ', linea)  # "RM1.25" 
        # "7.0 0", "6.0 0": el OCR separa la ultima cifra decimal del resto
        linea = re.sub(r'(?<![\d.,])(\d{1,5}[.,]\d)\s(\d)(?![\d.,])', r'\1\2', linea)
        return self._regex_decimal_mal_leido.sub(',', linea)

    _regex_articulo_con_descuento = re.compile(
        r'^(?P<art>.*?\d[.,]\d{2})\s+(?P<desc>(?:desc\.?|dto\.?|descuento)\s*[-−–]\s*\d{1,4}[.,]\d{2}.*)$', re.IGNORECASE
    )

    def _separar_descuento_en_linea(self, linea: str) -> List[str]:
        """"LECHE 0,89 Desc. -0,10" -> el articulo y, aparte, su descuento."""
        m = self._regex_articulo_con_descuento.match(linea)
        return [m.group('art'), m.group('desc')] if m else [linea]

    def parsear(self, texto: str) -> List[LineaTicketMejorada]:
        """Parsea ticket complejo y extrae líneas con contexto."""
        if not texto or not texto.strip():
            return []

        lineas_raw = texto.split('\n')
        # Una linea de ticket no pasa de unos 100 caracteres: recortar evita que un
        # texto basura enorme dispare las expresiones regulares.
        lineas_limpias = [p for l in lineas_raw if l.strip() for p in self._separar_descuento_en_linea(l.strip()[:200])]
        lineas_limpias = lineas_limpias[:600]  # ningun ticket real llega a tantas lineas

        # Detectar estructura (tabla vs lista)
        es_tabla = self._detectar_tabla(lineas_limpias)

        # Detectar dónde termina la sección de productos (tras TOTAL/CAMBIO/
        # TARJETA suele venir el pie del ticket: fidelización, marketing, etc.)
        fin_productos = self._detectar_fin_productos(lineas_limpias)

        # Detectar dónde empieza la sección de productos (antes suele venir la
        # cabecera: nombre de tienda, dirección, CIF, teléfono, fecha/hora).
        inicio_productos = self._detectar_inicio_productos(lineas_limpias)
        if inicio_productos >= fin_productos:
            # El "primer articulo" cayo despues del cierre: la deteccion se equivoco.
            inicio_productos = self._detectar_inicio_productos(lineas_limpias, usar_primera_fila=False)

        productos = []
        pendiente_fila = None
        for idx, linea in enumerate(lineas_limpias):
            if idx < inicio_productos:
                continue
            if idx >= fin_productos:
                break
            linea = self._normalizar_decimal(linea)
            detalle = self.regex_detalle_multiplicador.fullmatch(linea)
            if detalle and productos:
                # "4 x 0,55" en su propio renglon (Lidl): la cantidad y el
                # precio unitario del articulo anterior. No tiene letras, asi
                # que _es_linea_valida la descartaria.
                anterior = productos[-1]
                anterior.cantidad = float(detalle.group(1))
                anterior.unidad = TipoUnidad.UNIDAD
                anterior.cantidad_texto = f"{anterior.cantidad:g} ud"
                anterior.precio_unitario = self._parsear_precio(detalle.group(2))
                continue
            # "Desc. -0,30", "PROMO LIDL PLUS -0,50", "DTO. 0,30": no es un articulo, es un
            # descuento del articulo anterior (se resta de su importe).
            descuento = self._importe_de_descuento(linea)
            if descuento and productos:
                anterior = productos[-1]
                if anterior.precio_total and descuento <= anterior.precio_total + 0.005:
                    anterior.precio_total = round(anterior.precio_total - descuento, 2)
                    anterior.descuento = round(anterior.descuento + descuento, 2)
                continue
            fila = self.regex_fila_numerica.match(linea)
            sin_unidades = re.sub(r'\b(?:nos|pcs?|set|sets|units?|ea|pkt)\b', ' ', linea, flags=re.IGNORECASE)
            if fila and not re.search(r'[A-Za-záéíóúñ]{3,}', sin_unidades) and re.search(r'\d{4,}|[xX*]|\d+[.,]\d{2}\s+\d+[.,]\d{2}', linea):
                precios_fila = [self._parsear_precio(x) for x in re.findall(r'\d+[.,]\d{1,2}', linea[fila.start(2):])]
                total = precios_fila[-1] if precios_fila else 0
                cantidad = float(fila.group(1).replace(',', '.')) if fila.group(1) else None
                # Con dos precios unitarios ("80.00 84.80": sin y con impuesto) vale el que
                # multiplicado por la cantidad da el importe; por defecto, el mas cercano al importe.
                unitarios = precios_fila[:-1] or [total]
                unitario = unitarios[-1]
                if cantidad is not None:
                    unitario = next((u for u in reversed(unitarios) if abs(cantidad * u - total) <= 0.02 + 0.005 * cantidad), unitario)
                else:
                    cantidad = float(round(total / unitario)) if unitario else 1.0
                if (cantidad >= 1 and unitario > 0 and total > 0
                        and abs(cantidad * unitario - total) <= 0.02 + 0.005 * cantidad):
                    if productos and productos[-1].precio_total and abs(productos[-1].precio_total - total) <= 0.02:
                        # "2 x 1,85 3,70" tras "PAN 3,70": es el detalle del articulo anterior
                        anterior = productos[-1]
                        anterior.cantidad, anterior.unidad = cantidad, TipoUnidad.UNIDAD
                        anterior.cantidad_texto = f"{cantidad:g} ud"
                        anterior.precio_unitario = unitario
                        continue
                    # El nombre esta en las lineas de encima: el ultimo articulo sin importe
                    # (las lineas intermedias son codigos: se quedan sin importe y se descartan).
                    destino = self._elegir_nombre_para_fila(productos[-3:])
                    if destino is not None:
                        destino.cantidad, destino.unidad = cantidad, TipoUnidad.UNIDAD
                        destino.cantidad_texto = f"{cantidad:g} ud"
                        destino.precio_unitario, destino.precio_total = unitario, total
                        continue
                    pendiente_fila = (cantidad, unitario, total)  # nombre en la linea de DEBAJO
                    continue
            peso = self.regex_detalle_peso.fullmatch(linea)
            if peso and productos:
                anterior = productos[-1]
                anterior.cantidad = float(peso.group(1).replace(',', '.'))
                anterior.unidad = self.unidades_map.get(peso.group(2).lower(), TipoUnidad.UNIDAD)
                anterior.cantidad_texto = f"{anterior.cantidad:g} {anterior.unidad.value}"
                if peso.group(3):
                    anterior.precio_unitario = self._parsear_precio(peso.group(3))
                continue
            solo_precio = self.regex_solo_precio.fullmatch(linea)
            if solo_precio and productos and not productos[-1].precio_total:
                productos[-1].precio_total = self._parsear_precio(solo_precio.group(1))
                continue
            if self._es_linea_valida(linea):
                # Pasar contexto (línea anterior/siguiente)
                contexto_anterior = lineas_limpias[idx - 1] if idx > 0 else ""
                contexto_siguiente = lineas_limpias[idx + 1] if idx < len(lineas_limpias) - 1 else ""

                producto = self._extraer_producto(
                    linea,
                    contexto_anterior,
                    contexto_siguiente,
                    es_tabla
                )
                if producto and producto.nombre:
                    if self._es_linea_detalle_sin_nombre(producto.nombre):
                        # Segunda linea de un articulo vendido por peso (p.ej.
                        # "TOMATE PERA KG" seguido de "0,850 kg 1,89 EUR/kg
                        # 1,61"): no es un producto nuevo, es el peso/precio
                        # del articulo de la linea anterior. Sin esto se creaba
                        # un producto fantasma tipo "Eur/Kg".
                        if productos:
                            anterior = productos[-1]
                            anterior.cantidad = producto.cantidad
                            anterior.unidad = producto.unidad
                            anterior.cantidad_texto = producto.cantidad_texto
                            if producto.precio_unitario:
                                anterior.precio_unitario = producto.precio_unitario
                                if producto.precio_total:
                                    anterior.precio_total = producto.precio_total
                            elif producto.precio_total:
                                # Un solo precio en la linea de detalle: si el
                                # renglon anterior ya traia el importe, este es
                                # el unitario ("1,89 EUR/kg", "4 x 0,55"); pisar
                                # el total con el unitario falseaba el precio.
                                if anterior.precio_total:
                                    anterior.precio_unitario = producto.precio_total
                                else:
                                    anterior.precio_total = producto.precio_total
                    elif (not self._es_nombre_sin_producto(producto.nombre)
                          and not self._nombre_es_basura(producto.nombre)):
                        if pendiente_fila and not producto.precio_total:
                            # La fila numerica iba ANTES del nombre ("1072 1 80.00 80.00" / "ENGINE OIL")
                            producto.cantidad, producto.unidad = pendiente_fila[0], TipoUnidad.UNIDAD
                            producto.cantidad_texto = f"{pendiente_fila[0]:g} ud"
                            producto.precio_unitario, producto.precio_total = pendiente_fila[1], pendiente_fila[2]
                        pendiente_fila = None
                        productos.append(producto)

        # Filtrar duplicados y limpiar
        return self._postprocesar(productos)

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

    _regex_descuento_negativo = re.compile(r'(?<![\d,.])[-−–]\s*(\d{1,4}[.,]\d{2})\s*(?:€|eur)?\s*[A-Za-z]?\s*$')
    _regex_palabra_descuento = re.compile(
        r'^\W*(?:desc\.?|dto\.?|descuento|promo|promoci[oó]n|oferta|cup[oó]n|ahorro|lidl\s+plus)\b', re.IGNORECASE
    )

    _regex_palabras_de_descuento = re.compile(
        r'\b(?:desc|dto|descuento|promo|promoci[oó]n|oferta|cup[oó]n|ahorro|lidl|plus|total|compra|x)\b\.?', re.IGNORECASE
    )

    def _importe_de_descuento(self, linea: str) -> float:
        """Importe (positivo) si la linea es un descuento, o 0.

        Con signo menos al final ("Desc. -0,30", "PROMO LIDL PLUS -0,50") lo es siempre.
        Sin signo ("DTO. 0,30") solo si, quitadas las palabras de descuento y los numeros, no
        queda ningun nombre: "OFERTA LECHE DESNATADA 1,20" es un ARTICULO (el nombre lo
        delata), no un descuento."""
        linea = self._normalizar_decimal(linea)
        m = self._regex_descuento_negativo.search(linea)
        if m:
            return self._parsear_precio(m.group(1))
        if self._regex_palabra_descuento.match(linea):
            precios = self.regex_precio.findall(linea)
            resto = self._regex_palabras_de_descuento.sub(' ', linea)
            if precios and not re.search(r'[A-Za-záéíóúñ]{3,}', resto):
                return self._parsear_precio(precios[-1][0])
        return 0

    @staticmethod
    def _es_codigo(nombre: str) -> bool:
        """"EZ10HD05 -", "WA45 2A": una referencia, no el nombre de un articulo."""
        piezas = [p for p in re.split(r'[\s\-/]+', nombre) if p]
        # sin ninguna palabra de 3+ letras seguidas: "Pan 5" o "Vitamina C 1000" son articulos
        return (len(piezas) <= 2 and any(c.isdigit() for c in nombre)
                and not re.search(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}', nombre))

    def _elegir_nombre_para_fila(self, candidatos):
        """De las ultimas lineas SIN importe, la que es el nombre del articulo: no un
        codigo, y la que mas letras tiene (el nombre, no una linea de direccion
        suelta); a igualdad, la mas cercana a la fila numerica."""
        sin_importe = [q for q in candidatos if not q.precio_total and not self._es_codigo(q.nombre)]
        if not sin_importe:
            return None
        return max(reversed(sin_importe), key=lambda q: sum(c.isalpha() for c in q.nombre))

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

    def _es_nombre_sin_producto(self, nombre_limpio: str) -> bool:
        """True si el nombre solo contiene ruido de promocion o descuento."""
        tokens = [t for t in self._regex_tokens.split(nombre_limpio.lower()) if t]
        utiles = [
            t for t in tokens
            if len(t) > 1
            and t not in self._PALABRAS_SIN_PRODUCTO
            and not self._regex_token_prescindible.fullmatch(t)
        ]
        return not utiles

    def _es_linea_detalle_sin_nombre(self, nombre_limpio: str) -> bool:
        """True si, tras limpiar cantidad/precio, no queda nombre de producto
        real (p.ej. "Eur/Kg", "Eur", "Kg"): la linea solo aportaba el
        peso/precio de la linea anterior, no es un articulo en si misma."""
        nombre = nombre_limpio.strip()
        if len(nombre) < 3:
            return not self._es_palabra_de_producto(nombre.lower())  # "Te" es un articulo
        if self._regex_nombre_vacio.fullmatch(nombre):
            return True
        # Residuos de una linea "0,850 kg x 1,89 EUR/kg" (que queda en "X Eur")
        # o de un OCR torcido ("Eur/Kkg", ". Eur", "Eur )"): si todo lo que
        # queda son divisas, unidades o el "x", no hay nombre de producto.
        tokens = [t for t in self._regex_tokens.split(nombre.lower()) if t and not t.isdigit()]
        return all(self._es_ruido_de_detalle(t) for t in tokens)

    _RUIDO_DETALLE = ("eur", "euro", "euros", "usd", "kg", "g", "gr", "l", "lt", "ml", "ud", "uds", "x", "por")

    @classmethod
    def _es_ruido_de_detalle(cls, token: str) -> bool:
        if token in cls._RUIDO_DETALLE:
            return True
        # Variantes de OCR de "eur"/"kg" ("kkg", "eu", "ekg"), solo en tokens cortos.
        return len(token) <= 4 and max(fuzz.ratio(token, ref) for ref in ("eur", "kg", "euro")) >= 75

    def _nombre_es_basura(self, nombre: str) -> bool:
        """True si el "nombre" es ruido de OCR (sombras, bordes, grano) y no un
        articulo: casi sin letras, hecho de fragmentos de 1-2 letras, o con
        repeticiones imposibles en castellano ("Nnnnan", "Coocoooe")."""
        letras = [c for c in nombre if c.isalpha()]
        if len(letras) < 3:
            # un articulo real de dos letras ("Té") no es ruido
            return not (len(letras) == 2 and self._es_palabra_de_producto("".join(letras).lower()))
        # Palabras separadas por espacios/puntuacion, pero "€ @ $ | !" y los
        # digitos DENTRO de la palabra cuentan como parte de ella: son lo que
        # el OCR pone en lugar de las letras ("L€CH€", "T0MAT€5"). Una palabra
        # es creible si tiene >=3 caracteres, buena parte de letras y no
        # repite una letra 3 veces seguidas.
        tokens = [t for t in re.split(r"[^\w€@$|!]+", nombre.lower()) if t]

        def parece_palabra(t):
            return (
                len(t) >= 3
                and sum(c.isalpha() for c in t) >= 0.4 * len(t)
                and not re.search(r"([^\W\d_])\1\1", t)
            )

        palabras = [t for t in tokens if parece_palabra(t)]
        if not palabras:
            return True
        if sum(len(t) for t in palabras) < 0.5 * sum(len(t) for t in tokens):
            return True
        return False

    @staticmethod
    def _compilar_palabras(palabras) -> "re.Pattern":
        """Regex que reconoce cualquiera de `palabras` como palabra completa
        (o frase completa), con "s"/"es" final opcional."""
        alternativas = "|".join(re.escape(p) for p in sorted(palabras, key=len, reverse=True))
        letra = "a-záéíóúñü"
        return re.compile(
            rf"(?<![{letra}])(?:{alternativas})(?:es|s)?(?![{letra}])",
            re.IGNORECASE | re.UNICODE,
        )

    def _es_linea_valida(self, linea: str) -> bool:
        """Valida si la línea contiene un producto potencial."""
        if len(linea) < 3:
            return False

        linea_lower = linea.lower()

        # Ignorar líneas de control
        if self._regex_palabras_ignorar.search(linea_lower):
            return False

        # "CAJA 03  OP 12" es el puesto de cobro, pero "HUEVOS XL CAJA 6" o "CAJA
        # CERVEZA 12,50" son articulos: solo se descarta si no lleva importe.
        if re.search(r'\bcaja\b', linea_lower) and not self.regex_precio.search(linea):
            return False

        # Debe tener al menos 3 letras (no necesariamente consecutivas)
        # Esto permite detectar "T0m@t€5" como válido (tiene t, m, t)
        if len([c for c in linea if c.isalpha()]) < 3:
            # ... salvo un articulo de dos letras que existe ("TE 1,50"): solo si lleva importe
            return bool(self.regex_precio.search(linea)) and any(
                len(t) == 2 and self._es_palabra_de_producto(t.lower()) for t in re.findall(r'[^\W\d_]+', linea)
            )

        return True

    def _extraer_producto(
        self,
        linea: str,
        contexto_anterior: str,
        contexto_siguiente: str,
        es_tabla: bool
    ) -> LineaTicketMejorada:
        """Extrae producto con análisis contextual."""

        # 1. Extraer cantidad y unidad
        cantidad, unidad, cantidad_texto = self._extraer_cantidad_y_unidad(
            linea, contexto_anterior, contexto_siguiente
        )

        # 2. Extraer precios
        precio_unitario, precio_total = self._extraer_precios(linea, contexto_siguiente)

        # 2b. Cuadrar cantidad e importes: cantidad x unitario = total. Si el OCR
        # leyo mal el digito de la cantidad ("1" por "4"), el cociente lo delata.
        cantidad, unidad, cantidad_texto, precio_unitario = self._conciliar_cantidad_e_importes(
            linea, cantidad, unidad, cantidad_texto, precio_unitario, precio_total
        )

        # 3. Limpiar nombre
        nombre = self._limpiar_nombre(linea, cantidad_texto, precio_total)

        # 4. Detectar promoción (sobre la linea original: el marcador tipo
        # "2x1"/"3x2" se limpia del nombre en el paso anterior y dejaria de
        # detectarse si se buscara ya sobre el nombre limpio)
        es_promo = bool(self._regex_palabras_promocion.search(linea))

        # 5. Calcular confianza
        conf_nombre = self._calcular_confianza_nombre(nombre)
        conf_cantidad = self._calcular_confianza_cantidad(cantidad, unidad)

        return LineaTicketMejorada(
            nombre=nombre,
            cantidad=cantidad,
            unidad=unidad,
            cantidad_texto=cantidad_texto,
            precio_unitario=precio_unitario,
            precio_total=precio_total,
            confianza_nombre=conf_nombre,
            confianza_cantidad=conf_cantidad,
            es_promocion=es_promo,
            linea_original=linea
        )

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

    # Palabras de cierre/cortesia/impuestos que, aunque el OCR las escriba mal
    # ("Totai", "Totqty", "Sub Tal", "Discounl"), identifican una linea que NO es un
    # articulo. Se comparan con tolerancia sobre cada palabra del nombre.
    _PALABRAS_CONTROL_FUZZY = (
        "total", "subtotal", "discount", "rounding", "change", "balance", "summary", "tendered",
        "amount", "invoice", "receipt", "cashier", "thank", "payment", "customer", "member", "voucher",
        "points", "gst", "tax", "cambio", "efectivo", "tarjeta", "descuento", "importe",
        "gracias", "factura", "iva", "troco", "totale", "summe", "especes", "monnaie", "totqty", "qty",
    )

    @staticmethod
    def _es_palabra_de_producto(palabra: str) -> bool:
        """True si la palabra es una palabra real de articulos (tarta, especias, recambio):
        esas NUNCA se confunden con una palabra de cierre mal leida."""
        try:
            from .diccionario import obtener, _raiz
            return _raiz(_sin_tildes(palabra.lower())) in obtener()._vocabulario
        except Exception:
            return False

    def _es_linea_de_cierre_fuzzy(self, nombre: str) -> bool:
        palabras = [w for w in re.split(r'[^a-záéíóúñ]+', nombre.lower()) if len(w) >= 3]
        if not palabras or len(palabras) > 4:
            return False
        # Solo la PRIMERA palabra (o las dos primeras unidas): "Totai", "Totqty", "Sub Tal".
        # Una palabra parecida en mitad del nombre ("Arroz Redondo" ~ "redondeo") no cuenta,
        # ni una palabra que ya es de un articulo real ("Tarta" ~ "tarjeta").
        for w in (palabras[0], "".join(palabras[:2])):
            if w in self._PALABRAS_CONTROL_FUZZY:
                return True
            if len(w) < 4 or self._es_palabra_de_producto(w):
                continue
            for c in self._PALABRAS_CONTROL_FUZZY:
                if abs(len(w) - len(c)) <= 2 and fuzz.ratio(w, c) >= 78:
                    return True
        return any(
            len(palabras) <= 2 and "".join(palabras).startswith(c) and len("".join(palabras)) <= len(c) + 5
            for c in ("total", "subtotal", "discount")
        )

    def _postprocesar(self, productos: List[LineaTicketMejorada]) -> List[LineaTicketMejorada]:
        """Post-procesamiento: quita lineas de cierre y funde las repetidas."""
        resultado = []
        por_nombre = {}
        for prod in productos:
            if self._es_linea_de_cierre_fuzzy(prod.nombre):
                continue
            if not prod.precio_total and self._es_codigo(prod.nombre):
                continue  # "EZ10HD05 -": la referencia de un articulo, no otro articulo
            clave = prod.nombre.lower().strip()
            previo = por_nombre.get(clave)
            if previo is None:
                por_nombre[clave] = prod
                resultado.append(prod)
            elif previo.unidad == prod.unidad and (prod.precio_total or 0) > 0:
                # La misma linea dos veces en el ticket ("PAN" y otra vez "PAN", o dos
                # pesadas de platano): se compraron las dos, no es un duplicado del OCR.
                # Se suman cantidad e importe.
                previo.cantidad = round(previo.cantidad + prod.cantidad, 3)
                previo.cantidad_texto = f"{previo.cantidad:g} {previo.unidad.value}"
                previo.precio_total = round((previo.precio_total or 0) + prod.precio_total, 2)
        return resultado
