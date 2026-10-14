"""
Lectura de tickets de compra con OCR local (Tesseract), sin conexion a
internet. La deteccion de articulo/cantidad es heuristica y aproximada:
la pantalla de revision de la app siempre deja corregir el resultado a mano
antes de tocar el stock.
"""
import re

import cv2
import pytesseract
from PIL import Image

from ..servicios.ocr.procesador_imagen import ProcesadorImagen
from ..servicios.ocr.reconstructor_espacial import reconstruir_lineas, lineas_a_texto

_procesador_imagen = ProcesadorImagen()

PALABRAS_IGNORAR = [
    "total", "subtotal", "iva", "cambio", "efectivo", "tarjeta", "ticket",
    "factura", "simplificada", "cif", "nif", "gracias", "caja", "operador",
    "fecha", "hora", "www", "http", "atencion", "cliente", "devolucion",
    "importe", "descuento", "puntos", "calle", "avda", "avenida", "s.a",
    "s.l", "polígono", "poligono", "telefono", "teléfono",
]

RE_PRECIO_FINAL = re.compile(r"[\d]{1,3}[.,]\d{2}\s*(€|eur)?\s*$", re.IGNORECASE)
RE_CANTIDAD_INICIO = re.compile(r"^(\d+)\s*[xX]\s*(.+)$")
RE_CANTIDAD_FINAL = re.compile(r"^(.+?)\s+(\d+)\s*(ud|uds|u|unid)\.?$", re.IGNORECASE)


# Relectura de lineas dudosas. A veces Tesseract devuelve basura (confianza ~0)
# para una linea corta y perfectamente legible, p.ej. "2 x 1,85" -> "ZA A OS",
# justo la que da la cantidad de un articulo. El umbral interno de Tesseract
# sobre el gris con CLAHE falla ahi; binarizar (Otsu) SOLO ese recorte y leerlo
# como una unica linea lo resuelve. No se binariza la pagina entera porque con
# la fuente de punto de las impresoras termicas rompe los trazos (ver
# ProcesadorImagen.procesar).
_CONFIANZA_LINEA_DUDOSA = 45
_MEJORA_MINIMA_RELECTURA = 15
_MAX_RELECTURAS = 8
_TIMEOUT_RELECTURA_S = 5


def _releer_linea(gris, linea):
    """Devuelve (texto, confianza_media) de una segunda lectura de la linea, o
    None si no se pudo. Nunca lanza: es una mejora opcional."""
    try:
        alto, ancho = gris.shape[:2]
        margen = 14
        arriba = max(0, min(p.arriba for p in linea.palabras) - margen)
        abajo = min(alto, max(p.abajo for p in linea.palabras) + margen)
        izquierda = max(0, linea.izquierda - margen)
        # Las palabras dudosas suelen ser mas estrechas que el texto real.
        derecha = min(ancho, linea.derecha + int(ancho * 0.15))
        recorte = gris[arriba:abajo, izquierda:derecha]
        if recorte.size == 0:
            return None
        _, binaria = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binaria = cv2.copyMakeBorder(binaria, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
        datos = pytesseract.image_to_data(
            Image.fromarray(binaria), lang="spa", config="--psm 7",
            timeout=_TIMEOUT_RELECTURA_S, output_type=pytesseract.Output.DICT,
        )
        palabras = [
            (t.strip(), float(c)) for t, c in zip(datos["text"], datos["conf"])
            if t and t.strip() and float(c) >= 0
        ]
        if not palabras:
            return None
        return " ".join(t for t, _ in palabras), sum(c for _, c in palabras) / len(palabras)
    except Exception:
        return None


def _texto_con_relectura(lineas, gris):
    textos = [linea.texto for linea in lineas]
    dudosas = [
        i for i, linea in enumerate(lineas)
        if linea.palabras and linea.confianza_media < _CONFIANZA_LINEA_DUDOSA
    ][:_MAX_RELECTURAS]
    for i in dudosas:
        relectura = _releer_linea(gris, lineas[i])
        if relectura and relectura[1] >= lineas[i].confianza_media + _MEJORA_MINIMA_RELECTURA:
            textos[i] = relectura[0]
    return "\n".join(textos)


def extraer_texto(ruta_imagen):
    with open(ruta_imagen, "rb") as f:
        imagen_bytes = f.read()

    # Reescalado a ancho óptimo (2000px) + corrección de orientación +
    # escala de grises + CLAHE: sin esto Tesseract corría sobre la foto
    # completa del móvil (varios MP) en color, con "spa+eng" (doble modelo de
    # idioma), lo que disparaba el tiempo de lectura del ticket muy por
    # encima de los 20s objetivo.
    imagen_procesada = _procesador_imagen.procesar(imagen_bytes)
    imagen = Image.fromarray(imagen_procesada)
    try:
        # timeout: fotos con mucho ruido de fondo pueden disparar el tiempo
        # de segmentación de Tesseract a varios minutos; pytesseract mata el
        # proceso al superar el límite (a diferencia del SIGKILL de gunicorn
        # por --timeout, que deja el tesseract original huérfano consumiendo
        # CPU indefinidamente).
        #
        # image_to_data (no image_to_string): se necesita la caja de cada
        # palabra para reconstruir las líneas por coordenadas en vez de
        # fiarse del renderizado interno de Tesseract, que en tickets reales
        # (arrugas, inclinación residual, fuente de impresora térmica) a
        # veces corta una misma línea visual en varias líneas de texto o
        # descoloca el orden de las palabras. Ver reconstructor_espacial.py.
        datos = pytesseract.image_to_data(
            imagen, lang="spa", config="--psm 6", timeout=45,
            output_type=pytesseract.Output.DICT,
        )
        lineas = reconstruir_lineas(datos)
        return _texto_con_relectura(lineas, imagen_procesada)
    except RuntimeError:
        raise RuntimeError(
            "La foto tardó demasiado en procesarse. Prueba con más luz, "
            "menos reflejos o recortando la imagen para que solo salga el ticket."
        )


def _limpiar_precio(linea):
    return RE_PRECIO_FINAL.sub("", linea).strip(" -\t")


def _es_linea_util(linea):
    if len(linea) < 3:
        return False
    minuscula = linea.lower()
    if any(palabra in minuscula for palabra in PALABRAS_IGNORAR):
        return False
    if not re.search(r"[a-zA-ZÀ-ÿ]{3,}", linea):
        return False
    return True


def analizar_lineas(texto):
    items = []
    for linea_bruta in texto.splitlines():
        linea = linea_bruta.strip()
        if not _es_linea_util(linea):
            continue
        linea = _limpiar_precio(linea)
        if not linea:
            continue

        m_inicio = RE_CANTIDAD_INICIO.match(linea)
        m_final = RE_CANTIDAD_FINAL.match(linea)
        if m_inicio:
            cantidad, nombre = int(m_inicio.group(1)), m_inicio.group(2)
        elif m_final:
            nombre, cantidad = m_final.group(1), int(m_final.group(2))
        else:
            cantidad, nombre = 1, linea

        nombre = nombre.strip(" -.:").title()
        if len(nombre) < 3:
            continue
        items.append({"nombre": nombre, "cantidad": cantidad, "unidad": "ud"})
    return items


def procesar_ticket(ruta_imagen):
    texto = extraer_texto(ruta_imagen)
    return analizar_lineas(texto)
