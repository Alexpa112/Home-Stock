"""
Procesador de tickets v2 - Integración del parser mejorado + matcher inteligente.

Flujo:
1. OCR → texto
2. Parser mejorado → análisis contextual
3. Matcher inteligente → asignación de productos
4. Estimación de precios → validación
5. Respuesta con alternativas
"""
from typing import List, Dict, Optional
from .parser_mejorado import ParserMejorado, LineaTicketMejorada, TipoUnidad
from .matcher_inteligente import MatcherInteligente


class ProcesadorTicketsV2:
    """Procesador inteligente de tickets sin dependencias de IA."""

    def __init__(self):
        self.parser = ParserMejorado()
        self.matcher = MatcherInteligente()

    def procesar_completo(self, texto_ocr: str, db) -> List[Dict]:
        """Procesa ticket completo: OCR → análisis contextual → matching."""

        if not texto_ocr or not texto_ocr.strip():
            return []

        # 1. Parsear con análisis contextual
        lineas = self.parser.parsear(texto_ocr)

        # 2. Para cada línea, buscar en catálogo e inferir datos
        resultado = []
        for linea in lineas:
            item = self._procesar_linea(linea, db)
            resultado.append(item)

        return resultado

    def _procesar_linea(
        self,
        linea: LineaTicketMejorada,
        db
    ) -> Dict:
        """Procesa una línea del ticket."""

        # 1. Buscar en catálogo
        match = self.matcher.buscar_en_catalogo(
            linea.nombre,
            db,
            precio_total_ticket=linea.precio_total,
            cantidad_ticket=linea.cantidad
        )

        # 2. Deducir categoría si no hay match
        categoria = match["categoria"] if match else self.matcher.deducir_categoria(linea.nombre)

        # 3. Sugerir cantidad estándar
        cantidad_sugerida = self.matcher.sugerir_cantidad_estandar(linea.nombre, db)

        # 4. Estimar precio unitario
        precio_unitario = linea.precio_unitario
        if precio_unitario == 0 and linea.precio_total > 0:
            precio_unitario = linea.precio_total / linea.cantidad if linea.cantidad > 0 else 0

        # 5. Validar precio
        es_precio_valido = True
        razon_precio = "OK"
        if categoria:
            es_precio_valido, razon_precio = self.matcher.validar_precio(
                precio_unitario,
                categoria
            )

        return {
            "nombre": linea.nombre,
            "cantidad": linea.cantidad,
            "cantidad_sugerida": cantidad_sugerida,
            "unidad": linea.unidad.value,
            "cantidad_texto": linea.cantidad_texto,
            "precio_unitario": precio_unitario,
            "precio_total": linea.precio_total,
            "confianza_nombre": linea.confianza_nombre,
            "confianza_cantidad": linea.confianza_cantidad,
            "es_promocion": linea.es_promocion,
            # Datos de matching
            "producto_id": match["id"] if match else None,
            "categoria": categoria,
            "icono": match["icono"] if match else None,
            "confianza_match": match["confianza"] if match else 0,
            "alternativas": match.get("alternativas", []) if match else [],
            # Validación de precios
            "precio_valido": es_precio_valido,
            "razon_precio": razon_precio,
            # Línea original para debug
            "linea_original": linea.linea_original,
        }

    def sugerir_correccion(self, item_procesado: Dict, db) -> Dict:
        """Sugiere correcciones si confianza es baja.

        Se lee todo con .get(): este metodo recibe items de los dos motores de
        OCR (el de vision y el pipeline local) y un item al que le faltara una
        clave hacia estallar /api/tickets/analizar con un 500 en vez de
        degradar la sugerencia.
        """

        sugerencias = {
            "correcciones": [],
            "requiere_confirmacion": False
        }

        # Si confianza de match es baja, sugerir alternativas
        if item_procesado.get("confianza_match", 0) < 0.7:
            sugerencias["correcciones"].append({
                "tipo": "match_bajo",
                "mensaje": "El nombre podría no ser exacto. Revisa las alternativas.",
                "alternativas": item_procesado.get("alternativas") or []
            })
            sugerencias["requiere_confirmacion"] = True

        # Si cantidad es sospechosa
        if item_procesado.get("confianza_cantidad", 100) < 60:
            sugerencias["correcciones"].append({
                "tipo": "cantidad_dudosa",
                "mensaje": "La cantidad podría no ser clara en el ticket.",
                "sugerencia": item_procesado.get("cantidad_sugerida", item_procesado.get("cantidad"))
            })
            sugerencias["requiere_confirmacion"] = True

        # Si precio es anómalo
        if not item_procesado.get("precio_valido", True):
            sugerencias["correcciones"].append({
                "tipo": "precio_anómalo",
                "mensaje": item_procesado.get("razon_precio", "Precio fuera de rango"),
                "rango_esperado": self.matcher.rango_precios.get(
                    item_procesado.get("categoria"), (0, 100)
                )
            })
            sugerencias["requiere_confirmacion"] = True

        # Si es promoción, avisar
        if item_procesado.get("es_promocion"):
            sugerencias["correcciones"].append({
                "tipo": "promocion_detectada",
                "mensaje": "Se detectó una promoción. Verifica el precio real."
            })

        return sugerencias


def crear_respuesta_usuario(items: List[Dict], db) -> Dict:
    """Formatea respuesta para enviar al frontend."""

    procesador = ProcesadorTicketsV2()

    resultado = {
        "items": items,
        "resumen": {
            "total_items": len(items),
            "items_con_match": sum(1 for i in items if i.get("producto_id")),
            "items_sin_match": sum(1 for i in items if not i.get("producto_id")),
            "confianza_promedio": (
                sum(i.get("confianza_match", 0) for i in items) / len(items) if items else 0
            ),
            "requiere_revision": any(
                i.get("confianza_match", 0) < 0.7 or
                not i.get("precio_valido", True) or
                i.get("confianza_cantidad", 100) < 60
                for i in items
            )
        },
        "advertencias": []
    }

    # Agregar sugerencias de corrección
    for idx, item in enumerate(items):
        sugerencias = procesador.sugerir_correccion(item, db)
        if sugerencias["correcciones"]:
            item["sugerencias"] = sugerencias

    # Agregar advertencias generales
    sin_match = [i for i in items if not i.get("producto_id")]
    if len(sin_match) > len(items) * 0.3:  # Más del 30% sin match
        resultado["advertencias"].append({
            "tipo": "muchos_sin_match",
            "mensaje": f"{len(sin_match)} productos no encontrados en catálogo. Revisa manualmente."
        })

    confianza_promedio = resultado["resumen"]["confianza_promedio"]
    if confianza_promedio < 0.6:
        resultado["advertencias"].append({
            "tipo": "confianza_baja",
            "mensaje": "Confianza baja en los matches. El OCR pudo tener dificultades."
        })

    return resultado
