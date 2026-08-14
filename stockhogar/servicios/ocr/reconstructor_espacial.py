"""Reconstrucción espacial de líneas de ticket a partir de las coordenadas
por palabra que devuelve Tesseract (`image_to_data`), en vez de fiarse del
texto ya "renderizado" por `image_to_string`.

Por qué hace falta: `image_to_string` decide internamente dónde corta cada
línea y en qué orden coloca las palabras, y esa decisión no es corregible
después con regex. En tickets reales (papel arrugado, ligera inclinación
residual tras `ProcesadorImagen`, tipografías de impresora térmica) esa
segmentación interna a veces se equivoca: palabras de una misma línea visual
(p.ej. "2 LECHE ENTERA 1L" ......... "2,50") se devuelven en líneas de texto
distintas, o el orden izquierda-derecha no se respeta. El resultado aguas
abajo es justo el síntoma de "palabras sueltas"/"letras mezcladas entre
artículos".

Este módulo agrupa las palabras de `image_to_data` por proximidad vertical
(tolerando el desplazamiento típico de una foto, no una inclinación grande:
eso ya lo corrige `ProcesadorImagen._corregir_orientacion` antes de llegar
aquí) y las ordena de izquierda a derecha dentro de cada grupo. La unidad
mínima manejada es siempre la PALABRA con su caja (nunca un carácter suelto),
tal y como la entrega Tesseract.

Uso: `reconstruir_lineas(datos)` donde `datos` es el dict que devuelve
`pytesseract.image_to_data(..., output_type=pytesseract.Output.DICT)`.
`lineas_a_texto(lineas)` produce un texto con un salto de línea por línea
reconstruida, compatible con `ParserMejorado.parsear()` (que ya espera texto
separado por "\\n" y no necesita cambios).
"""
import statistics
from dataclasses import dataclass, field
from typing import List


# Tesseract devuelve conf=-1 en las entradas estructurales (marcadores de
# bloque/párrafo/línea sin palabra propia) y en huecos sin texto. No se filtra
# por valor de confianza: una palabra real pero borrosa puede tener confianza
# baja y seguiría siendo la única información disponible sobre ese hueco del
# ticket; descartarla sería inventar una ausencia de dato, no corregir un error.
_UMBRAL_TOLERANCIA_MINIMO_PX = 6
_FACTOR_TOLERANCIA_ALTURA = 0.6


@dataclass(frozen=True)
class Palabra:
    """Una palabra tal y como la entrega Tesseract, con su caja y confianza.

    Es la unidad mínima que maneja este módulo: nunca se parte en caracteres.
    """
    texto: str
    izquierda: int
    arriba: int
    ancho: int
    alto: int
    confianza: float

    @property
    def derecha(self) -> int:
        return self.izquierda + self.ancho

    @property
    def abajo(self) -> int:
        return self.arriba + self.alto

    @property
    def centro_y(self) -> float:
        return self.arriba + self.alto / 2

    @property
    def centro_x(self) -> float:
        return self.izquierda + self.ancho / 2


@dataclass
class LineaReconstruida:
    """Una línea visual del ticket: palabras agrupadas por altura y
    ordenadas de izquierda a derecha."""
    palabras: List[Palabra] = field(default_factory=list)
    numero: int = 0

    @property
    def texto(self) -> str:
        return " ".join(p.texto for p in self.palabras)

    @property
    def confianza_media(self) -> float:
        confianzas = [p.confianza for p in self.palabras if p.confianza >= 0]
        return statistics.fmean(confianzas) if confianzas else 0.0

    @property
    def y_centro(self) -> float:
        return statistics.fmean(p.centro_y for p in self.palabras) if self.palabras else 0.0

    @property
    def izquierda(self) -> int:
        return min((p.izquierda for p in self.palabras), default=0)

    @property
    def derecha(self) -> int:
        return max((p.derecha for p in self.palabras), default=0)


def _palabras_desde_datos_tesseract(datos: dict) -> List[Palabra]:
    """Convierte el dict de `image_to_data` en una lista de `Palabra`,
    descartando solo las entradas sin texto (marcadores estructurales de
    Tesseract), nunca por confianza."""
    palabras = []
    n = len(datos.get("text", []))
    for i in range(n):
        texto = (datos["text"][i] or "").strip()
        if not texto:
            continue
        try:
            confianza = float(datos["conf"][i])
        except (TypeError, ValueError, KeyError):
            confianza = -1.0
        try:
            palabras.append(Palabra(
                texto=texto,
                izquierda=int(datos["left"][i]),
                arriba=int(datos["top"][i]),
                ancho=int(datos["width"][i]),
                alto=int(datos["height"][i]),
                confianza=confianza,
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return palabras


def reconstruir_lineas(datos: dict) -> List[LineaReconstruida]:
    """Agrupa las palabras de `image_to_data` en líneas visuales.

    Algoritmo: ordena todas las palabras por centro vertical y va
    encadenando en la misma línea cada palabra cuyo centro esté a menos de
    `tolerancia` píxeles del de la ÚLTIMA palabra añadida a la línea actual
    (no de la media del grupo): así una línea con ligera inclinación
    residual (el centro Y va subiendo/bajando poco a poco de izquierda a
    derecha) se mantiene unida sin dejar que dos líneas próximas pero
    distintas se fundan por deriva del promedio.

    La tolerancia se calcula a partir de la altura tipográfica mediana de la
    página (no un valor fijo en píxeles), para funcionar igual con tickets
    fotografiados a distintas resoluciones/tamaños de letra.
    """
    palabras = _palabras_desde_datos_tesseract(datos)
    if not palabras:
        return []

    alturas = [p.alto for p in palabras if p.alto > 0]
    alto_tipico = statistics.median(alturas) if alturas else 20
    tolerancia = max(alto_tipico * _FACTOR_TOLERANCIA_ALTURA, _UMBRAL_TOLERANCIA_MINIMO_PX)

    ordenadas = sorted(palabras, key=lambda p: p.centro_y)

    grupos: List[List[Palabra]] = [[ordenadas[0]]]
    for palabra in ordenadas[1:]:
        grupo_actual = grupos[-1]
        y_referencia = grupo_actual[-1].centro_y
        if palabra.centro_y - y_referencia <= tolerancia:
            grupo_actual.append(palabra)
        else:
            grupos.append([palabra])

    lineas = []
    for idx, grupo in enumerate(grupos):
        grupo_ordenado = sorted(grupo, key=lambda p: p.izquierda)
        lineas.append(LineaReconstruida(palabras=grupo_ordenado, numero=idx))
    return lineas


def lineas_a_texto(lineas: List[LineaReconstruida]) -> str:
    """Serializa las líneas reconstruidas a texto separado por saltos de
    línea, listo para `ParserMejorado.parsear()` (que ya trabaja línea a
    línea y no necesita cambios)."""
    return "\n".join(linea.texto for linea in lineas)


def dibujar_debug(imagen_bgr, lineas: List[LineaReconstruida]):
    """Dibuja sobre una copia de la imagen (array BGR de OpenCV) la caja de
    cada palabra y el número de línea detectada, para depurar visualmente
    por qué el sistema se equivoca en un ticket concreto.

    No se usa en el pipeline normal de escaneo (coste de CPU y de E/S
    innecesario en producción); es una utilidad para inspección manual o
    tests. Requiere cv2, que ya es dependencia del proyecto
    (`ProcesadorImagen`), y se importa aquí en vez de a nivel de módulo para
    no obligar a cargarlo cuando solo se usa `reconstruir_lineas`.
    """
    import cv2

    salida = imagen_bgr.copy()
    for linea in lineas:
        for palabra in linea.palabras:
            cv2.rectangle(
                salida,
                (palabra.izquierda, palabra.arriba),
                (palabra.derecha, palabra.abajo),
                (0, 200, 0), 1,
            )
        if linea.palabras:
            primera = linea.palabras[0]
            cv2.putText(
                salida, f"L{linea.numero}",
                (max(primera.izquierda - 25, 0), max(primera.arriba, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1,
            )
    return salida
