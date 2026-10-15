"""Lector de tickets con RapidOCR (modelos PP-OCRv4 en ONNX, 100 % local).

Por que existe: Tesseract (modelo `spa` rapido) lee mal los importes de un
ticket de impresora termica fotografiado o escaneado en baja resolucion. Sobre
250 recibos REALES (SROIE) lee el 88 % de las lineas y el 90 % de los importes;
RapidOCR el 95 % y el 97 %, y en menos tiempo. Los modelos van DENTRO del paquete
pip (no se descarga nada en ejecucion) y corre en CPU, sin red.

Si el paquete no esta instalado (p. ej. una Raspberry Pi de 32 bits, sin
`onnxruntime`), `disponible()` devuelve False y el escaner usa solo Tesseract.
"""
import logging
import os
import re
import threading

from ..servicios.ocr.reconstructor_espacial import LineaReconstruida, Palabra, reconstruir_lineas

logger = logging.getLogger(__name__)

_motor = None
_cerrojo = threading.Lock()
_no_disponible = False
# Hilos de ONNX: una Raspberry Pi de 4 nucleos no debe quedarse sin CPU para el resto.
def _entero_de_entorno(nombre, defecto):
    """Una variable mal escrita ("dos", vacia) no debe impedir arrancar la app."""
    try:
        return max(1, int(os.environ.get(nombre, defecto)))
    except (TypeError, ValueError):
        return defecto


_HILOS = _entero_de_entorno("DREAME_OCR_HILOS", 2)
# El clasificador de angulo (gira cada linea 180 grados si esta del reves) cuesta tiempo en cada
# linea; la foto ya se endereza antes (orientacion EXIF y deteccion del papel).
_USAR_CLASIFICADOR = os.environ.get("DREAME_OCR_CLS", "0") == "1"
# Lecturas simultaneas: gunicorn atiende varias peticiones a la vez y cada lectura usa
# ~200 MB y varios hilos. Las demas esperan su turno (el limite de peticiones por
# usuario ya acota la cola) en vez de agotar la memoria de una Raspberry Pi.
_CONCURRENCIA = _entero_de_entorno("DREAME_OCR_CONCURRENCIA", 2)
_turno = threading.BoundedSemaphore(_CONCURRENCIA)


def disponible() -> bool:
    global _no_disponible
    if _no_disponible:
        return False
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        _no_disponible = True
        return False


def _obtener_motor():
    global _motor, _no_disponible
    if _motor is None:
        with _cerrojo:
            if _motor is None:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                    _motor = RapidOCR(
                        det_intra_op_num_threads=_HILOS, rec_intra_op_num_threads=_HILOS,
                        cls_intra_op_num_threads=1,
                    )
                except Exception:
                    logger.exception("No se pudo iniciar RapidOCR; se usara Tesseract")
                    _no_disponible = True
                    raise
    return _motor


_FACTOR_PASO_ESPACIO = 1.55


def _con_espacios(texto, cajas):
    """El modelo (entrenado sobre todo con texto chino) une a menudo las palabras:
    "YONGFATTENTERPRISE". Pero entrega la caja de CADA caracter. Un ticket se
    imprime casi siempre con paso fijo: entre dos caracteres consecutivos hay un
    paso de ~1 ancho de celda, y un espacio es un hueco de ~2. Se compara la
    distancia entre CENTROS con la mediana de la linea (comparar el hueco libre
    falla: una "l" o una "i" dejan mucho aire sin que haya espacio)."""
    if len(cajas) != len(texto) or len(texto) < 4:
        return texto
    centros = [(c[0][0] + c[1][0]) / 2 for c in cajas]
    pasos = sorted(b - a for a, b in zip(centros, centros[1:]) if b - a > 0)
    if not pasos:
        return texto
    tipico = pasos[len(pasos) // 2]
    salida = [texto[0]]
    for i in range(1, len(texto)):
        if texto[i] != " " and texto[i - 1] != " " and centros[i] - centros[i - 1] > _FACTOR_PASO_ESPACIO * tipico:
            salida.append(" ")
        salida.append(texto[i])
    return "".join(salida)


# Sin tocar los multipacks "6X1L", "2X5G": el digito tras "NxX" es un tamano.
_RE_DIGITO_ENTRE_LETRAS = re.compile(r"(?<!\d[xX])(?<=[A-Za-z])([015])(?=[A-Za-z])")
_DIGITO_A_LETRA = {"0": "O", "1": "I", "5": "S"}


def _arreglar_confusiones(texto):
    """"BR0C0LI", "QUE5O": el modelo lee a menudo O como 0 o S como 5 DENTRO de una
    palabra. Un digito rodeado de letras en una palabra es una letra mal leida
    (un tamano como "1L" o "500G" no tiene letras a los dos lados)."""
    return _RE_DIGITO_ENTRE_LETRAS.sub(lambda m: _DIGITO_A_LETRA[m.group(1)], texto)


def leer_lineas(imagen_bgr):
    """Lee la imagen (BGR, uint8) y devuelve lineas reconstruidas por altura.

    Cada deteccion de RapidOCR (un trozo de texto con su caja) se trata como una
    "palabra": la columna de importes suele salir como un trozo aparte en la
    misma fila que el nombre, y `reconstruir_lineas` los junta por coordenadas."""
    motor = _obtener_motor()
    with _turno:
        resultado, _ = motor(imagen_bgr, use_cls=_USAR_CLASIFICADOR, return_word_box=True)
    if not resultado:
        return []
    datos = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    for elemento in resultado:
        caja, texto, confianza = elemento[0], elemento[1], elemento[2]
        if len(elemento) > 3 and elemento[3]:
            texto = _con_espacios(texto, elemento[3])
        texto = _arreglar_confusiones(texto)
        xs = [p[0] for p in caja]
        ys = [p[1] for p in caja]
        datos["text"].append(texto)
        datos["conf"].append(float(confianza) * 100)
        datos["left"].append(int(min(xs)))
        datos["top"].append(int(min(ys)))
        datos["width"].append(int(max(xs) - min(xs)))
        datos["height"].append(int(max(ys) - min(ys)))
    return reconstruir_lineas(datos)
