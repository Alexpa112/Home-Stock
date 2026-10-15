"""Clasificacion de lineas: articulo, control, detalle, codigo o descuento."""
from .modelos import _sin_tildes
import re
from rapidfuzz import fuzz
from typing import List


class ClasificadorLineas:
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

    @staticmethod
    def _es_palabra_de_producto(palabra: str) -> bool:
        """True si la palabra es una palabra real de articulos (tarta, especias, recambio):
        esas NUNCA se confunden con una palabra de cierre mal leida."""
        try:
            from ..diccionario import obtener, _raiz
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

    def _separar_descuento_en_linea(self, linea: str) -> List[str]:
        """"LECHE 0,89 Desc. -0,10" -> el articulo y, aparte, su descuento."""
        m = self._regex_articulo_con_descuento.match(linea)
        return [m.group('art'), m.group('desc')] if m else [linea]
