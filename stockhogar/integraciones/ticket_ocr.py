"""
Lectura de tickets de compra con OCR local (Tesseract), sin conexion a
internet. La deteccion de articulo/cantidad es heuristica y aproximada:
la pantalla de revision de la app siempre deja corregir el resultado a mano
antes de tocar el stock.
"""
import re

import pytesseract
from PIL import Image

from ..servicios.ocr.procesador_imagen import ProcesadorImagen

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
        return pytesseract.image_to_string(imagen, lang="spa", config="--psm 6", timeout=45)
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
