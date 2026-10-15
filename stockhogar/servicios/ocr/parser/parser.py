"""ParserMejorado: orquesta las piezas del parser de tickets."""
from .cantidades import CantidadesParser
from .lineas import ClasificadorLineas
from .modelos import LineaTicketMejorada, TipoUnidad
from .nombres import NombresParser
from .patrones import PatronesParser
from .secciones import SeccionesParser
from .vocabulario import VocabularioParser
import re
from typing import List


class ParserMejorado(VocabularioParser, PatronesParser, SeccionesParser, ClasificadorLineas, CantidadesParser, NombresParser):
    """Parser de tickets de supermercado (varios formatos y cadenas). Las piezas viven en modulos tematicos."""

    def __init__(self):
        self._cargar_vocabulario()
        self._cargar_patrones()

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
