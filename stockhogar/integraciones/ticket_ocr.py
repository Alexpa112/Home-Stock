"""
Lectura de tickets de compra con OCR local, sin conexion a internet: motor
neuronal (RapidOCR, ver ocr_rapid.py) y, si no esta disponible o lee mal,
Tesseract. La deteccion de articulo/cantidad es heuristica y aproximada: la
pantalla de revision de la app siempre deja corregir el resultado a mano antes de
tocar el stock.
"""
import logging
import os
import re
import statistics
from concurrent.futures import ThreadPoolExecutor

import cv2
import pytesseract
from PIL import Image

from . import ocr_rapid
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


# Relectura de lineas dudosas (Tesseract). A veces devuelve basura (confianza ~0)
# para una linea corta y perfectamente legible, p.ej. "2 x 1,85" -> "ZA A OS",
# justo la que da la cantidad de un articulo. El umbral interno de Tesseract
# sobre el gris con CLAHE falla ahi; binarizar (Otsu) SOLO ese recorte y leerlo
# como una unica linea lo resuelve. No se binariza la pagina entera porque con
# la fuente de punto de las impresoras termicas rompe los trazos (ver
# ProcesadorImagen.procesar).
_CONFIANZA_LINEA_DUDOSA = 45
_MEJORA_MINIMA_RELECTURA = 15
_MAX_RELECTURAS = 12
# Las relecturas de linea son procesos Tesseract independientes: se lanzan en paralelo
# (antes una detras de otra, ~0,3 s cada una y 2 por linea).
_HILOS_RELECTURA = max(1, min(4, os.cpu_count() or 1))
# Cada Tesseract usa OpenMP; con varios a la vez y todos con 4 hilos se estorban.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
_TIMEOUT_RELECTURA_S = 5


_RE_PRECIO_AL_FINAL = re.compile(r"\d[.,]\d{2}\s*(?:€|eur)?\s*[A-Za-z]?\s*$", re.IGNORECASE)
_MAX_LINEAS_RECUPERADAS = 6
_FACTOR_HUECO = 1.7          # un hueco > 1,7 pasos de linea es que falta alguna
_FRACCION_LINEA_TRUNCADA = 0.8


def _puntuar_lectura(texto, confianza):
    """Calidad de una lectura de linea: confianza de Tesseract mas premio por
    acabar en un importe valido, que es lo que tiene una linea de articulo."""
    return confianza + (25 if _RE_PRECIO_AL_FINAL.search(texto) else 0)


def _leer_recorte(gris, arriba, abajo, izquierda, derecha):
    """Segunda lectura de una franja del ticket probando dos tratamientos:
    binarizada (Otsu) y ampliada en gris. Devuelve (texto, confianza) de la
    mejor, o None. Nunca lanza."""
    try:
        alto, ancho = gris.shape[:2]
        arriba, izquierda = max(0, arriba), max(0, izquierda)
        abajo, derecha = min(alto, abajo), min(ancho, derecha)
        recorte = gris[arriba:abajo, izquierda:derecha]
        if recorte.size == 0:
            return None
        variantes = []
        _, otsu = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variantes.append(cv2.copyMakeBorder(otsu, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255))
        grande = cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        variantes.append(cv2.copyMakeBorder(grande, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255))
        mejor = None
        for variante in variantes:
            datos = pytesseract.image_to_data(
                Image.fromarray(variante), lang="spa", config="--psm 7",
                timeout=_TIMEOUT_RELECTURA_S, output_type=pytesseract.Output.DICT,
            )
            palabras = [
                (t.strip(), float(c)) for t, c in zip(datos["text"], datos["conf"])
                if t and t.strip() and float(c) >= 0
            ]
            if not palabras:
                continue
            texto = " ".join(t for t, _ in palabras)
            confianza = sum(c for _, c in palabras) / len(palabras)
            if mejor is None or _puntuar_lectura(texto, confianza) > _puntuar_lectura(*mejor):
                mejor = (texto, confianza)
        return mejor
    except Exception:
        return None


def _paso_de_linea(lineas):
    pasos = sorted(b.y_centro - a.y_centro for a, b in zip(lineas, lineas[1:]) if b.y_centro > a.y_centro)
    if len(pasos) < 3:
        return None
    return pasos[len(pasos) // 2]


def _recuperar_lineas_perdidas(lineas, gris):
    """Tesseract a veces se salta una linea entera (suele ser la de detalle
    "4 x 7,77" que da la cantidad). Un hueco mayor que ~1,7 pasos de linea la
    delata: se lee esa franja y se insertan las lineas halladas."""
    paso = _paso_de_linea(lineas)
    if not paso or not lineas:
        return []
    ancho = gris.shape[1]
    huecos = []
    for a, b in zip(lineas, lineas[1:]):
        hueco = b.y_centro - a.y_centro
        if hueco <= paso * _FACTOR_HUECO or hueco > paso * 4:
            continue
        faltan = max(1, round(hueco / paso) - 1)
        huecos += [a.y_centro + hueco * k / (faltan + 1) for k in range(1, faltan + 1)]
        if len(huecos) >= _MAX_LINEAS_RECUPERADAS:
            break
    if not huecos:
        return []
    with ThreadPoolExecutor(max_workers=_HILOS_RELECTURA) as pool:
        lecturas = list(pool.map(lambda y: _leer_recorte(gris, int(y - paso * 0.6), int(y + paso * 0.6), 0, ancho), huecos))
    return [(y, l[0]) for y, l in zip(huecos, lecturas) if l and l[1] >= 30 and len(l[0]) >= 3]


def _lineas_truncadas(lineas):
    """Indices de lineas de articulo que parecen cortadas por la derecha (sin
    importe y mucho mas cortas que las lineas con importe)."""
    con_importe = [l.derecha for l in lineas if _RE_PRECIO_AL_FINAL.search(l.texto)]
    if len(con_importe) < 3:
        return []
    referencia = statistics.median(con_importe)
    indices_importe = [i for i, l in enumerate(lineas) if _RE_PRECIO_AL_FINAL.search(l.texto)]
    primero, ultimo = indices_importe[0], indices_importe[-1]
    return [
        i for i, l in enumerate(lineas)
        if primero < i < ultimo and l.derecha < referencia * _FRACCION_LINEA_TRUNCADA
        and not _RE_PRECIO_AL_FINAL.search(l.texto) and re.search(r"[A-Za-z]{3}", l.texto)
    ]


_CONFIANZA_BASURA = 35
_RATIO_ALNUM_BASURA = 0.5


def _es_basura(texto, confianza_media):
    """Linea que no es texto del ticket: bordes, sombras, rayas de separacion
    ("¡ +. ..b..“<XL£. noe ono.."). Se reconoce por tener muy pocos caracteres
    alfanumericos o una confianza muy baja SIN ningun importe: una linea con un
    importe legible nunca se descarta."""
    # Una linea con numeros (fecha, cajero, "Total Qty 1 80 91", un importe mal
    # leido...) es texto real aunque el OCR la lea fea: solo se descarta lo que
    # no tiene ni dos digitos.
    if _RE_PRECIO_AL_FINAL.search(texto) or re.search(r"\d[.,]\d{2}", texto) or sum(c.isdigit() for c in texto) >= 2:
        return False
    sin_espacios = re.sub(r"\s", "", texto)
    if not sin_espacios:
        return True
    alnum = sum(c.isalnum() for c in sin_espacios)
    if alnum < 3 or alnum / len(sin_espacios) <= _RATIO_ALNUM_BASURA:
        return True
    # Una linea de texto real tiene palabras (3+ letras); el ruido son trozos
    # sueltos de 1-2 caracteres y signos.
    piezas = texto.split()
    if len(piezas) >= 5:
        palabras = [p for p in piezas if sum(c.isalpha() for c in p) >= 3 and sum(not c.isalnum() for c in p) <= 1]
        if len(palabras) / len(piezas) < 0.35:
            return True
    # Una raya de guiones leida como letras ("PIDA PAPA AAA PAPA PA AA"): casi todas
    # las "palabras" son cortas o repiten una o dos letras.
    if len(piezas) >= 6:
        pobres = [p for p in piezas if len(p) <= 2 or len(set(p.lower())) <= 2]
        if len(pobres) / len(piezas) >= 0.6:
            return True
    return confianza_media < _CONFIANZA_BASURA and alnum < 6


def _texto_con_relectura(lineas, gris):
    textos = [linea.texto for linea in lineas]
    ancho = gris.shape[1]
    dudosas = [
        i for i, linea in enumerate(lineas)
        if linea.palabras and linea.confianza_media < _CONFIANZA_LINEA_DUDOSA
    ]
    candidatas = list(dict.fromkeys(dudosas + _lineas_truncadas(lineas)))[:_MAX_RELECTURAS]
    margen = 14

    def _releer(i):
        linea = lineas[i]
        return _leer_recorte(
            gris, min(p.arriba for p in linea.palabras) - margen,
            max(p.abajo for p in linea.palabras) + margen, linea.izquierda - margen, ancho,
        )

    with ThreadPoolExecutor(max_workers=_HILOS_RELECTURA) as pool:
        lecturas = list(pool.map(_releer, candidatas))
    for i, lectura in zip(candidatas, lecturas):
        linea = lineas[i]
        if lectura and (
            _puntuar_lectura(*lectura) >= _puntuar_lectura(linea.texto, linea.confianza_media) + _MEJORA_MINIMA_RELECTURA
        ):
            textos[i] = lectura[0]
    # Lineas que Tesseract se salto: se insertan en su sitio por altura.
    perdidas = _recuperar_lineas_perdidas(lineas, gris)
    elementos = [(l.y_centro, t, _es_basura(t, l.confianza_media)) for l, t in zip(lineas, textos)]
    elementos += [(y, t, _es_basura(t, 100)) for y, t in perdidas]
    return "\n".join(t for _, t, basura in sorted(elementos, key=lambda e: e[0]) if not basura)


# Segunda pasada con la imagen suavizada: ver ProcesadorImagen.procesar.
_PSM = 6
_CONFIANZA_PRIMERA_PASADA = 90
_SUAVIZADO_SEGUNDA_PASADA = 2.5


_MEJORA_MINIMA_SEGUNDA_PASADA = 4
_RE_IMPORTE_SUELTO = re.compile(r"(?<![\d.,])\d{1,5}[.,]\d{2}(?!\d)")


def _contar_importes(lineas):
    return sum(len(_RE_IMPORTE_SUELTO.findall(l.texto)) for l in lineas)


def _leer_pagina(gris):
    """Una pasada de Tesseract sobre la pagina: (lineas, confianza media por
    caracter). image_to_data (no image_to_string): se necesita la caja de cada
    palabra para reconstruir las lineas por coordenadas (ver
    reconstructor_espacial)."""
    datos = pytesseract.image_to_data(
        Image.fromarray(gris), lang="spa", config=f"--psm {_PSM}", timeout=45,
        output_type=pytesseract.Output.DICT,
    )
    lineas = reconstruir_lineas(datos)
    pesos = [(len(p.texto), p.confianza) for l in lineas for p in l.palabras if p.confianza >= 0]
    total = sum(n for n, _ in pesos)
    return lineas, (sum(n * c for n, c in pesos) / total if total else 0.0)


logger = logging.getLogger(__name__)
# Con menos importes que esto la lectura neuronal se considera fallida y se prueba Tesseract.
_MIN_IMPORTES_MOTOR_NEURONAL = 2


def _texto_con_motor_neuronal(imagen_bytes):
    """Lectura con RapidOCR. Devuelve (texto, importes_leidos) o None si el motor
    no esta o falla: el escaner entonces sigue con Tesseract."""
    if os.environ.get("DREAME_OCR") == "tesseract" or not ocr_rapid.disponible():
        return None
    try:
        imagen = _procesador_imagen.procesar_para_motor_neuronal(imagen_bytes)
        lineas = ocr_rapid.leer_lineas(imagen)
    except Exception:
        logger.warning("Fallo del motor neuronal de OCR; se usara Tesseract", exc_info=True)
        return None
    textos = [(l.y_centro, l.texto, _es_basura(l.texto, l.confianza_media)) for l in lineas]
    texto = "\n".join(t for _, t, basura in textos if not basura)
    return texto, _contar_importes(lineas)


def _importes_en_texto(texto):
    return len(_RE_IMPORTE_SUELTO.findall(texto or ""))


def extraer_texto(ruta_imagen):
    with open(ruta_imagen, "rb") as f:
        imagen_bytes = f.read()

    neuronal = _texto_con_motor_neuronal(imagen_bytes)
    if neuronal is not None and neuronal[1] >= _MIN_IMPORTES_MOTOR_NEURONAL:
        return neuronal[0]
    try:
        texto = _texto_con_tesseract(imagen_bytes)
    except RuntimeError:
        # Tesseract tardo demasiado: si el motor neuronal leyo algo, vale mas que un error.
        if neuronal is not None and neuronal[0].strip():
            return neuronal[0]
        raise
    # El motor neuronal leyo POCO (menos de 2 importes) y Tesseract tambien: gana el que
    # haya leido mas importes (a igualdad, el neuronal, que es el mas fiable).
    if neuronal is not None and _importes_en_texto(neuronal[0]) >= _importes_en_texto(texto):
        return neuronal[0]
    return texto


def _texto_con_tesseract(imagen_bytes):
    # Reescalado a ancho óptimo (2000px) + corrección de orientación +
    # escala de grises + CLAHE: sin esto Tesseract corría sobre la foto
    # completa del móvil (varios MP) en color, con "spa+eng" (doble modelo de
    # idioma), lo que disparaba el tiempo de lectura del ticket muy por
    # encima de los 20s objetivo.
    gris = _procesador_imagen.procesar(imagen_bytes)
    try:
        # timeout: fotos con mucho ruido de fondo pueden disparar el tiempo
        # de segmentación de Tesseract a varios minutos; pytesseract mata el
        # proceso al superar el límite (a diferencia del SIGKILL de gunicorn
        # por --timeout, que deja el tesseract original huérfano consumiendo
        # CPU indefinidamente).
        lineas, confianza = _leer_pagina(gris)
        if confianza < _CONFIANZA_PRIMERA_PASADA:
            # Lectura floja (impresion de puntos, foto borrosa): segunda pasada con
            # la imagen suavizada. La confianza de Tesseract NO sirve para elegir
            # (en recibos reales subia mientras se perdian la mitad de los importes):
            # gana la pasada que lee MAS importes, y solo si empatan, la de mas confianza.
            try:
                gris2 = _procesador_imagen.procesar(imagen_bytes, suavizado=_SUAVIZADO_SEGUNDA_PASADA)
                lineas2, confianza2 = _leer_pagina(gris2)
                n1, n2 = _contar_importes(lineas), _contar_importes(lineas2)
                if n2 > n1 or (n2 == n1 and confianza2 >= confianza + _MEJORA_MINIMA_SEGUNDA_PASADA):
                    lineas, gris = lineas2, gris2
            except RuntimeError:
                pass  # la segunda pasada es opcional: se queda la primera
        return _texto_con_relectura(lineas, gris)
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
