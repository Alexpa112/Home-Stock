"""
Matcher inteligente sin IA - razonamiento local puro.

Características:
- Análisis de similitud ponderada (nombre + categoría + precio)
- Deducción de categorías por patrones
- Estimación de precios unitarios
- Sugerencia de cantidades estándar
- Aprendizaje histórico de patrones
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from collections import Counter

from .catalogo import catalogo_del_hogar

# Centinela: None es un hogar_id valido de 'sin hogar', asi que no sirve para
# distinguir 'cache vacia' de 'cache del hogar None'.
_SIN_CACHE = object()

try:
    from .parser_mejorado import TipoUnidad
except ImportError:
    # Fallback para imports standalone
    from parser_mejorado import TipoUnidad


class MatcherInteligente:
    """Matcher contextual que razona sobre productos."""

    def __init__(self):
        # Diccionarios de palabras clave por categoría (muy expandido)
        self.palabras_categoria = {
            "Alimentación": [
                "pan", "leche", "queso", "yogur", "cereales", "pasta", "arroz",
                "harina", "azúcar", "sal", "aceite", "vinagre", "salsa",
                "mermelada", "miel", "chocolate", "galletas", "barrita", "snack",
                "frutos", "fruto", "fruta", "verdura", "hortaliza"
            ],
            "Frutas y Verduras": [
                "manzana", "plátano", "naranja", "limón", "fresa", "uva",
                "kiwi", "piña", "melón", "sandía", "melocotón",
                "tomate", "lechuga", "cebolla", "patata", "zanahoria",
                "calabacín", "berenjena", "pepino", "pimiento", "brócoli",
                "coliflor", "ajo", "cebollino", "perejil", "lechuga", "espinaca"
            ],
            "Carnes y Pescados": [
                "pollo", "pavo", "cerdo", "ternera", "cordero", "jamón",
                "pechuga", "costilla", "filete", "carne", "embutido",
                "salchichón", "mortadela", "chorizo", "fuet", "jamón",
                "pescado", "salmón", "trucha", "merluza", "bacalao",
                "camarones", "langostino", "marisco", "mejillón", "ostra"
            ],
            "Bebidas": [
                "agua", "café", "té", "zumo", "refresco", "vino", "cerveza",
                "champagne", "sidra", "batido", "leche", "jugo", "bebida",
                "gaseosa", "limonada", "horchata", "smoothie", "licor"
            ],
            "Limpieza": [
                "detergente", "jabón", "limpiador", "desinfectante", "gel",
                "lejía", "limpiahogar", "quitalmanchas", "suavizante",
                "deshollinador", "desatascador", "alambre", "estropajo"
            ],
            "Higiene y Cuidado Personal": [
                "papel", "pañuelos", "toallitas", "desodorante", "champú",
                "jabón", "gel", "crema", "loción", "cepillo", "pasta dental",
                "enjuague", "toalla", "servilleta", "tampones", "compresas",
                "pañales", "toallitas húmedas", "desinfectante"
            ],
            "Congelados": [
                "congelado", "helado", "fruta congelada", "verdura congelada",
                "pizza", "hamburguesa", "croqueta", "gamba", "filete", "nugget"
            ],
            "Bebé y Niños": [
                "pañal", "toallita", "biberón", "chupete", "papilla",
                "leche infantil", "fortimel", "nutribén", "nestlé"
            ],
            "Mascotas": [
                "pienso", "comida", "perro", "gato", "pájaro", "pez",
                "juguete", "correa", "collar", "arenero", "comida mascota"
            ],
        }

        # Palabras indicadoras de tamaño/cantidad
        self.indicadores_cantidad = {
            "mini": 0.5,
            "pequeño": 0.5,
            "mediano": 1,
            "grande": 2,
            "extra": 1.5,
            "familia": 1.5,
            "pack": 1,
            "lote": 1,
            "caja": 1,
            "bote": 1,
            "frasco": 1,
            "botella": 1,
            "bidón": 5,
        }

        # Precios típicos por categoría (para validación)
        self.rango_precios = {
            "Bebidas": (0.5, 3.0),
            "Carnes y Pescados": (2.0, 15.0),
            "Frutas y Verduras": (0.5, 5.0),
            "Higiene y Cuidado Personal": (0.5, 5.0),
            "Congelados": (1.0, 8.0),
            "Limpieza": (0.5, 3.0),
            "Mascotas": (1.0, 10.0),
            "Bebé y Niños": (1.0, 20.0),
        }

        # Catálogo cacheado por instancia: el mismo MatcherInteligente
        # procesa todas las líneas de un ticket, así que sin esta caché se
        # repetía el mismo SELECT completo de productos por cada línea.
        # La clave lleva el hogar_id (A-1): antes la caché era del catálogo
        # GLOBAL, así que las "alternativas" que se devolvían al cliente
        # podían ser productos de otros hogares.
        self._cache_catalogo = None
        self._cache_hogar_id = _SIN_CACHE

    def buscar_en_catalogo(
        self,
        nombre_ocr: str,
        db,
        precio_total_ticket: float = 0,
        cantidad_ticket: float = 0,
        hogar_id=None,
    ) -> Optional[Dict]:
        """Busca producto en catálogo con razonamiento inteligente.

        Args:
            nombre_ocr: Nombre extraído del OCR
            db: Conexión a BD
            precio_total_ticket: Precio del producto en el ticket (para validar)
            cantidad_ticket: Cantidad en el ticket (para estimar unitario)

        Returns:
            Dict con producto + confianza + sugerencias
        """

        if not nombre_ocr or len(nombre_ocr.strip()) < 2:
            return None

        # 1. Obtener catálogo del hogar (cacheado para todo el ticket).
        # Sin hogar_id no se devuelve nada: es preferible no emparejar a
        # emparejar contra el catálogo de otra familia (A-1).
        if hogar_id is None:
            return None
        if self._cache_hogar_id != hogar_id:
            self._cache_catalogo = catalogo_del_hogar(db, hogar_id)
            self._cache_hogar_id = hogar_id
        productos = self._cache_catalogo

        if not productos:
            return None

        # 2. Calcular similitud ponderada para cada producto
        coincidencias = []
        for prod in productos:
            similitud = self._calcular_similitud_ponderada(
                nombre_ocr,
                prod["nombre"],
                prod["categoria"]
            )

            if similitud > 0.4:  # Umbral mínimo
                precio_unitario = self._estimar_precio_unitario(
                    prod,
                    precio_total_ticket,
                    cantidad_ticket
                )

                coincidencias.append({
                    "producto": prod,
                    "similitud": similitud,
                    "precio_unitario": precio_unitario,
                    "precio_estimado": precio_total_ticket if precio_total_ticket > 0 else None
                })

        if not coincidencias:
            return None

        # 3. Ordenar por similitud
        coincidencias.sort(key=lambda x: x["similitud"], reverse=True)
        mejor = coincidencias[0]

        return {
            "id": mejor["producto"]["id"],
            "nombre": mejor["producto"]["nombre"],
            "categoria": mejor["producto"]["categoria"],
            "icono": mejor["producto"]["icono"],
            "confianza": min(mejor["similitud"], 1.0),
            "precio_unitario_estimado": mejor["precio_unitario"],
            "alternativas": [
                {
                    "id": m["producto"]["id"],
                    "nombre": m["producto"]["nombre"],
                    "similitud": m["similitud"]
                }
                for m in coincidencias[1:4]  # Top 3 alternativas
            ]
        }

    # Cifras que el OCR confunde con letras en un nombre de producto.
    _CONFUSIONES_OCR = {'0': 'o', '1': 'i', '5': 's', '8': 'b'}

    def _normalizar_para_comparar(self, nombre: str) -> str:
        """Deja el nombre en una forma comparable pese al ruido del OCR.

        Quita diacríticos y cualquier carácter que no sea alfanumérico (el OCR
        mete "€", "@" y similares dentro de las palabras) y deshace las
        confusiones cifra/letra típicas. Se aplica a los DOS lados de la
        comparación: normalizar solo el texto del ticket lo alejaría del
        catálogo en vez de acercarlo.
        """
        import unicodedata

        sin_tildes = ''.join(
            c for c in unicodedata.normalize('NFKD', nombre.lower())
            if not unicodedata.combining(c)
        )
        limpio = ''.join(
            self._CONFUSIONES_OCR.get(c, c) if c.isalnum() else ' '
            for c in sin_tildes
        )
        return ' '.join(limpio.split())

    def _calcular_similitud_ponderada(
        self,
        nombre_ocr: str,
        nombre_catalogo: str,
        categoria: str
    ) -> float:
        """Calcula similitud con múltiples factores.

        Factores:
        - Parecido del texto completo (45%), tomando el mejor entre el nombre
          tal cual y el normalizado contra el ruido del OCR.
        - Palabras en común (35%), que capta los nombres con las palabras en
          otro orden ("Leche entera Pascual" / "Pascual leche entera"), donde
          la comparación carácter a carácter puntúa mal.
        - Palabras clave de la categoría (20%).

        La ponderación se mantiene deliberadamente conservadora: por encima
        del umbral el artículo se da por existente y al confirmar el ticket el
        stock se suma a ESE producto, así que una coincidencia falsa es peor
        que dejarlo como artículo nuevo para que el usuario lo revise.
        """

        ocr_normalizado = self._normalizar_para_comparar(nombre_ocr)
        catalogo_normalizado = self._normalizar_para_comparar(nombre_catalogo)
        catalogo_lower = nombre_catalogo.lower()

        similitud_directa = SequenceMatcher(
            None, nombre_ocr.lower(), catalogo_lower
        ).ratio()
        similitud_normalizada = SequenceMatcher(
            None, ocr_normalizado, catalogo_normalizado
        ).ratio()
        similitud_texto = max(similitud_directa, similitud_normalizada)

        palabras_ocr = set(ocr_normalizado.split())
        palabras_catalogo = set(catalogo_normalizado.split())
        total_palabras = len(palabras_ocr | palabras_catalogo)
        similitud_palabras = (
            len(palabras_ocr & palabras_catalogo) / total_palabras
            if total_palabras else 0
        )

        palabras_categoria = set(self.palabras_categoria.get(categoria, []))
        coincidencia_categoria = (
            len(palabras_ocr & palabras_categoria) / len(palabras_categoria)
            if palabras_categoria else 0
        )

        return (
            similitud_texto * 0.45 +
            similitud_palabras * 0.35 +
            coincidencia_categoria * 0.20
        )

    def deducir_categoria(self, nombre: str) -> Optional[str]:
        """Deduce categoría por palabras clave."""

        nombre_lower = nombre.lower()

        # Contar coincidencias por categoría
        puntuaciones = {}
        for categoria, palabras in self.palabras_categoria.items():
            coincidencias = sum(
                1 for palabra in palabras
                if palabra in nombre_lower
            )
            if coincidencias > 0:
                puntuaciones[categoria] = coincidencias

        if puntuaciones:
            # Retornar categoría con más coincidencias
            return max(puntuaciones, key=puntuaciones.get)

        return None

    def sugerir_cantidad_estandar(self, nombre: str, db=None) -> float:
        """Sugiere cantidad estándar basada en nombre.

        Prioridad: indicador de tamaño en el nombre > cantidad_defecto
        aprendida en historial_articulos > 1.0 por defecto.
        """

        nombre_lower = nombre.lower()

        # Buscar indicadores
        for indicador, multiplicador in self.indicadores_cantidad.items():
            if indicador in nombre_lower:
                return multiplicador

        if db is not None:
            historico = self.obtener_historico_compras(db, nombre, limite=1)
            if historico:
                return historico[0]["cantidad_defecto"]

        return 1.0

    def _estimar_precio_unitario(
        self,
        producto: Dict,
        precio_total: float,
        cantidad: float
    ) -> float:
        """Estima precio unitario de forma inteligente.

        Estrategia:
        1. Si tenemos precio_total y cantidad, calcular
        2. Si no, buscar histórico de compras
        3. Si no, usar promedio de categoría
        """

        if precio_total > 0 and cantidad > 0:
            return precio_total / cantidad

        # No hay ningún campo de precio en el esquema (productos, articulos_lista,
        # historial_articulos): sin esa columna no hay histórico de precios que
        # consultar. Requeriría una migración de BD antes de poder estimarlo aquí.
        return 0

    def validar_precio(
        self,
        precio: float,
        categoria: str
    ) -> Tuple[bool, str]:
        """Valida si el precio es razonable para la categoría."""

        if precio <= 0:
            return True, "Precio no especificado"

        rango = self.rango_precios.get(categoria, (0, 100))

        if precio < rango[0]:
            return False, f"Muy bajo para {categoria}: {rango[0]}€-{rango[1]}€"
        if precio > rango[1]:
            return False, f"Muy alto para {categoria}: {rango[0]}€-{rango[1]}€"

        return True, "OK"

    def obtener_historico_compras(self, db, nombre: str, limite: int = 10) -> List[Dict]:
        """Obtiene histórico de compras para este producto."""

        # Buscar en historial_articulos (aprendizaje de nombre/icono/categoria/cantidad)
        historico = db.execute(
            """
            SELECT nombre, cantidad_defecto, unidad, categoria, icono
            FROM historial_articulos
            WHERE nombre LIKE ?
            ORDER BY fecha_actualizacion DESC
            LIMIT ?
            """,
            (f"%{nombre}%", limite)
        ).fetchall()

        return [dict(row) for row in historico] if historico else []
