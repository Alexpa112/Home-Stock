"""Parsea texto de ticket y extrae productos y cantidades."""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class LineaTicket:
    """Representa una línea de producto en un ticket."""

    nombre: str
    cantidad: float = 1
    cantidad_texto: str = ""
    precio_unitario: float = 0
    precio_total: float = 0
    confianza: float = 100


class ParseadorTicket:
    """Parsea texto de ticket y extrae información de productos.

    - Identifica líneas de producto
    - Extrae cantidades (kg, unidades, etc.)
    - Reconoce precios
    - Maneja múltiples formatos
    """

    def __init__(self):
        # Regex para detectar cantidades
        self.regex_cantidad = re.compile(
            r"(\d+[.,]?\d*)\s*(kg|g|l|ml|ud|unidad|unidades|piezas|pz|x)",
            re.IGNORECASE,
        )

        # Regex para detectar precios (€, $, etc.)
        self.regex_precio = re.compile(
            r"([\$€¢]?\s*\d+[.,]\d{2})\s*(€|\$)?", re.IGNORECASE
        )

        # Palabras a ignorar (típicas de tickets)
        self.palabras_ignorar = {
            "total",
            "subtotal",
            "impuesto",
            "iva",
            "descuento",
            "oferta",
            "promoción",
            "cambio",
            "efectivo",
            "tarjeta",
            "pago",
            "fecha",
            "hora",
            "tienda",
            "ticket",
            "recibo",
        }

    def parsear(self, texto: str) -> List[LineaTicket]:
        """Parsea texto y extrae líneas de productos.

        Args:
            texto: Texto OCR del ticket

        Returns:
            List[LineaTicket]: Productos detectados
        """
        lineas = texto.split("\n")
        productos = []

        for linea in lineas:
            linea = linea.strip()
            if not linea or len(linea) < 3:
                continue

            # Ignorar líneas de control
            if any(palabra in linea.lower() for palabra in self.palabras_ignorar):
                continue

            # Intentar extraer producto
            producto = self._extraer_producto(linea)
            if producto and producto.nombre:
                productos.append(producto)

        return productos

    def _extraer_producto(self, linea: str) -> LineaTicket:
        """Extrae información de una línea de producto."""
        # Buscar cantidad
        cantidad, cantidad_texto = self._extraer_cantidad(linea)

        # Buscar precio
        precios = re.findall(self.regex_precio, linea)
        precio_total = self._parsear_precio(precios[-1][0]) if precios else 0

        # Limpiar línea para obtener nombre
        nombre = self._limpiar_nombre_producto(linea)

        return LineaTicket(
            nombre=nombre,
            cantidad=cantidad,
            cantidad_texto=cantidad_texto,
            precio_total=precio_total,
        )

    def _extraer_cantidad(self, linea: str) -> Tuple[float, str]:
        """Extrae cantidad de la línea."""
        match = self.regex_cantidad.search(linea)
        if match:
            cantidad_str = match.group(1).replace(",", ".")
            try:
                cantidad = float(cantidad_str)
                return cantidad, match.group(0)
            except ValueError:
                pass

        return 1, ""

    def _parsear_precio(self, precio_str: str) -> float:
        """Convierte string de precio a float."""
        # Limpiar
        precio_str = precio_str.replace("€", "").replace("$", "").strip()
        precio_str = precio_str.replace(",", ".")

        try:
            return float(precio_str)
        except ValueError:
            return 0

    def _limpiar_nombre_producto(self, linea: str) -> str:
        """Extrae nombre limpio del producto."""
        # Quitar símbolos de alineación (puntos, guiones repetidos)
        linea = re.sub(r"\.{2,}", " ", linea)  # Puntos: .......... -> espacio
        linea = re.sub(r"-{2,}", " ", linea)   # Guiones: -------- -> espacio

        # Quitar información de precio por unidad (@1.20€/kg, @0.50€, etc.)
        linea = re.sub(r"\s+@\s*[\d.,€\$\s/]*(?=\s|$)", " ", linea, flags=re.IGNORECASE)

        # Quitar precios y también información de unidad de precio (/kg, €/kg, etc.)
        linea = re.sub(self.regex_precio, "", linea)
        linea = re.sub(r"/\s*(kg|g|l|ml|ud|unidad)", "", linea, flags=re.IGNORECASE)

        # Quitar cantidades
        linea = re.sub(self.regex_cantidad, "", linea)

        # Quitar números al final (códigos, cantidad mal parseada)
        linea = re.sub(r"\s+\d+\s*$", "", linea)

        # Quitar espacios múltiples
        linea = re.sub(r"\s+", " ", linea)

        return linea.strip()
