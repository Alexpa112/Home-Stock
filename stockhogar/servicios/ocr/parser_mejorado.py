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
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


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
        self.palabras_ignorar = {
            "total", "subtotal", "importe", "pago", "cambio", "efectivo",
            "tarjeta", "visa", "mastercard", "ticket", "factura", "recibo",
            "iva", "irpf", "impuesto", "fecha", "hora", "tienda", "caja",
            "operador", "atencion", "cliente", "gracias", "vuelvo", "cuenta",
            "www", "http", "email", "tlf", "telefono", "cif", "nif", "empresa", "domicilio",
            "devolucion", "cambios", "garantia", "oferta", "promocion", "descuento",
            "puntos", "puntuacion", "codigo", "lote", "lotes",
            # Fidelización / programas de puntos
            "fidelidad", "fidelizacion", "monedero", "socio", "socia",
            "ha ganado", "ganado", "acumulado", "acumulados", "saldo",
            "recompensa", "recompensas", "vale descuento", "cheque descuento",
            "ahorro acumulado", "club", "supercompra", "mi club", "carrefour pass",
            "n. socio", "nº socio", "num. socio",
        }

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
            r'(?<![A-Za-záéíóúñ])(\d*[.,]\d{2})(?!\d)\s*(€|\$)?',
            re.IGNORECASE
        )
        self.regex_precio_unitario = re.compile(
            r'@\s*(\d+[.,]\d+)\s*(€|\/kg|\/l|\/ud)?',
            re.IGNORECASE
        )

        # Patrones típicos de cabecera (nombre de tienda, dirección, CIF, teléfono)
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
        }

        # Cantidad "suelta" al principio de la línea (p.ej. "2 COCA COLA 1,80"):
        # un entero corto seguido de espacio y letra, típico de tickets donde
        # la cantidad va delante del nombre del artículo sin unidad explícita.
        self.regex_cantidad_inicial = re.compile(
            r'^(\d{1,3})\s+(?=[a-záéíóúñ])',
            re.IGNORECASE | re.UNICODE
        )

    def parsear(self, texto: str) -> List[LineaTicketMejorada]:
        """Parsea ticket complejo y extrae líneas con contexto."""
        if not texto or not texto.strip():
            return []

        lineas_raw = texto.split('\n')
        lineas_limpias = [l.strip() for l in lineas_raw if l.strip()]

        # Detectar estructura (tabla vs lista)
        es_tabla = self._detectar_tabla(lineas_limpias)

        # Detectar dónde termina la sección de productos (tras TOTAL/CAMBIO/
        # TARJETA suele venir el pie del ticket: fidelización, marketing, etc.)
        fin_productos = self._detectar_fin_productos(lineas_limpias)

        # Detectar dónde empieza la sección de productos (antes suele venir la
        # cabecera: nombre de tienda, dirección, CIF, teléfono, fecha/hora).
        inicio_productos = self._detectar_inicio_productos(lineas_limpias)

        productos = []
        for idx, linea in enumerate(lineas_limpias):
            if idx < inicio_productos:
                continue
            if idx >= fin_productos:
                break
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
                    else:
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
        regex_cierre = re.compile(
            r'\b(total|subtotal|tot|cambio|tarjeta|efectivo|pago|importe|'
            r'visa|mastercard)\b',
            re.IGNORECASE | re.UNICODE
        )
        # Además de la palabra clave, se exige un importe en euros en la
        # misma línea: la cabecera de la tabla de productos ("Descripción
        # P. Unit Importe") también contiene "importe" pero sin ningún
        # precio, y sin esta condición se detectaba como cierre ANTES de
        # llegar a los productos (0 items detectados pese a que el OCR
        # leía el ticket perfectamente bien).
        for idx, linea in enumerate(lineas):
            if regex_cierre.search(linea) and self.regex_precio.search(linea):
                return idx

        return len(lineas)

    def _detectar_inicio_productos(self, lineas: List[str]) -> int:
        """Detecta el índice a partir del cual empiezan los productos,
        saltando la cabecera del ticket (nombre de tienda, dirección,
        CIF/NIF, teléfono, fecha/hora), que no contiene productos.

        Se considera cabecera toda línea inicial que no tenga un precio
        (##,## €) ni una cantidad con unidad, y que además "parezca"
        cabecera (contiene CIF/NIF, teléfono, código postal o palabras
        típicas de dirección/razón social). Se limita la búsqueda a las
        primeras 12 líneas para no comerse todo el ticket si el OCR no
        detecta precios.
        """
        limite = min(len(lineas), 12)
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
            if not es_cabecera and idx > 0:
                # Primera línea que no parece cabecera ni tiene precio/cantidad:
                # puede ser un producto sin precio detectado por el OCR, o el
                # nombre de la tienda (idx 0, casi siempre cabecera). A partir
                # de la segunda línea, si no es claramente cabecera, se asume
                # que ya empiezan los productos.
                return idx

        return limite

    _regex_nombre_vacio = re.compile(r'^(eur|usd|€|\$)?\s*/?\s*(kg|g|l|ml|ud|uds)\.?$', re.IGNORECASE)

    def _es_linea_detalle_sin_nombre(self, nombre_limpio: str) -> bool:
        """True si, tras limpiar cantidad/precio, no queda nombre de producto
        real (p.ej. "Eur/Kg", "Kg"): la linea solo aportaba el peso/precio de
        la linea anterior, no es un articulo en si misma."""
        nombre = nombre_limpio.strip()
        if len(nombre) < 3:
            return True
        return bool(self._regex_nombre_vacio.fullmatch(nombre))

    def _es_linea_valida(self, linea: str) -> bool:
        """Valida si la línea contiene un producto potencial."""
        if len(linea) < 3:
            return False

        linea_lower = linea.lower()

        # Ignorar líneas de control
        if any(palabra in linea_lower for palabra in self.palabras_ignorar):
            return False

        # Debe tener al menos 3 letras consecutivas
        if not re.search(r'[a-záéíóúñ]{3,}', linea, re.UNICODE | re.IGNORECASE):
            return False

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

        # 3. Limpiar nombre
        nombre = self._limpiar_nombre(linea, cantidad_texto, precio_total)

        # 4. Detectar promoción (sobre la linea original: el marcador tipo
        # "2x1"/"3x2" se limpia del nombre en el paso anterior y dejaria de
        # detectarse si se buscara ya sobre el nombre limpio)
        es_promo = any(p in linea.lower() for p in self.palabras_promocion)

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

        # Sin cantidad al principio: buscar número + unidad real en
        # cualquier parte de la línea (p.ej. "LECHE ENTERA 1L", "ARROZ SOS
        # 1KG" -> el tamaño del envase es la única cantidad disponible).
        match = re.search(patron_numero_unidad, linea, re.UNICODE | re.IGNORECASE)

        if match:
            cantidad_str = match.group(1).replace(',', '.')
            unidad_str = match.group(2).lower().strip('.')

            try:
                cantidad = float(cantidad_str)
                unidad = self.unidades_map.get(unidad_str, TipoUnidad.UNIDAD)
                cantidad_texto = f"{cantidad} {unidad.value}"
                return cantidad, unidad, cantidad_texto
            except ValueError:
                pass

        # Si no hay patrón explícito, asumir 1 unidad
        return 1.0, TipoUnidad.UNIDAD, "1 ud"

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
            return float(precio_str)
        except ValueError:
            return 0

    def _limpiar_nombre(self, linea: str, cantidad_texto: str, precio_total: float) -> str:
        """Limpia nombre del producto removiendo cantidad y precio.

        Solo se elimina cantidad+unidad cuando la unidad es real (kg, l,
        ud...), o la cantidad suelta al principio de la línea. Nunca se
        elimina un número seguido de una palabra cualquiera, porque eso
        rompería el nombre del artículo (p.ej. "2 COCA COLA" -> "Cola").
        """

        # Quitar precio unitario (@1.20€/kg)
        nombre = re.sub(self.regex_precio_unitario, '', linea)

        # Quitar precios primero: si no, un precio sin el "0" inicial
        # (p.ej. ",70") deja sueltos sus dígitos y la regex de cantidad
        # los confunde con una cantidad+unidad (p.ej. "70 C").
        nombre = re.sub(self.regex_precio, '', nombre)

        # Quitar cantidad con unidad real
        nombre = re.sub(self.regex_cantidad_unidad, '', nombre)

        # Quitar cantidad suelta al principio de la línea (p.ej. "2 Coca Cola")
        nombre = self.regex_cantidad_inicial.sub('', nombre)

        # Quitar marcador de promocion tipo "2x1"/"3x2" al principio
        # (p.ej. "2X1 GALLETAS MARIA" -> "Galletas Maria"); la promocion ya
        # se detecta aparte sobre la linea original, no hace falta dejarla
        # en el nombre del articulo.
        nombre = re.sub(r'^\d+\s*x\s*\d+\s*', '', nombre, flags=re.IGNORECASE)

        # Quitar letra suelta de tipo de IVA al final (p.ej. "... A", "... B")
        # que queda huérfana tras quitar el precio cuando este no tenía
        # dígitos que la regex de cantidad pudiera arrastrar consigo.
        nombre = re.sub(r'\s+[a-záéíóúñ]\s*$', '', nombre, flags=re.UNICODE | re.IGNORECASE)

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

    def _postprocesar(self, productos: List[LineaTicketMejorada]) -> List[LineaTicketMejorada]:
        """Post-procesamiento: filtrar duplicados, limpiar."""

        # Eliminar productos duplicados (mismo nombre normalizado)
        nombres_vistos = set()
        resultado = []

        for prod in productos:
            nombre_norm = prod.nombre.lower().strip()
            if nombre_norm not in nombres_vistos:
                nombres_vistos.add(nombre_norm)
                resultado.append(prod)

        return resultado
