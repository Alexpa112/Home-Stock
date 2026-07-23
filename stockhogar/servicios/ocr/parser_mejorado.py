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
        self.regex_precio = re.compile(
            r'(\d+[.,]\d{2})\s*(€|\$)?',
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

        Todo lo que aparece después de la última mención a total/pago/cambio
        se considera pie de ticket y se descarta del parseo de productos.
        """
        palabras_cierre = {
            "total", "subtotal", "cambio", "tarjeta", "efectivo", "pago",
            "importe", "visa", "mastercard",
        }
        ultimo_idx = -1
        for idx, linea in enumerate(lineas):
            linea_lower = linea.lower()
            if any(p in linea_lower for p in palabras_cierre):
                ultimo_idx = idx

        if ultimo_idx == -1:
            return len(lineas)
        return ultimo_idx + 1

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

        # 4. Detectar promoción
        es_promo = any(p in nombre.lower() for p in self.palabras_promocion)

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

        # Patrón: número + unidad real (kg, l, ud, paq...)
        match = re.search(
            r'(\d+[.,]?\d*)\s*(' + '|'.join(
                sorted(self.unidades_map.keys(), key=len, reverse=True)
            ) + r')\b\.?',
            linea,
            re.UNICODE | re.IGNORECASE
        )

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

        # Sin unidad explícita: mirar si hay una cantidad suelta al
        # principio de la línea (p.ej. "2 COCA COLA 1,80" -> cantidad 2)
        match_inicial = self.regex_cantidad_inicial.match(linea)
        if match_inicial:
            try:
                cantidad = float(match_inicial.group(1))
                if cantidad > 0:
                    return cantidad, TipoUnidad.UNIDAD, f"{cantidad:g} ud"
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

        # Quitar cantidad con unidad real
        nombre = re.sub(self.regex_cantidad_unidad, '', nombre)

        # Quitar cantidad suelta al principio de la línea (p.ej. "2 Coca Cola")
        nombre = self.regex_cantidad_inicial.sub('', nombre)

        # Quitar precios
        nombre = re.sub(self.regex_precio, '', nombre)

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
