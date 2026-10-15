"""Vocabulario del parser: unidades, palabras de promocion y de control que no son articulos."""
from .modelos import TipoUnidad
import re


class VocabularioParser:
    def _cargar_vocabulario(self):
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
