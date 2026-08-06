"""Regresion: dos fallos reales de ProcesadorImagen con fotos de movil.

1. _detectar_y_recortar_ticket usaba solo brillo (escala de grises + Otsu)
   para separar el papel del fondo. Con fondos de brillo parecido al papel
   pero color propio (piel, madera...) el contorno detectado era casi toda
   la foto y el recorte no aislaba el ticket. Ahora se prueba primero por
   SATURACION (HSV): el papel es practicamente acromatico (saturacion casi
   nula) aunque el fondo tenga un brillo similar.

2. procesar() aplicaba CLAHE (contraste local) directamente sobre fotos con
   ruido ISO (poca luz): CLAHE amplifica el ruido igual que el texto,
   enterrando las letras bajo "nieve" (visto con un ticket real: el recorte
   era perfecto y aun asi Tesseract leia basura). Ahora se aplica un
   medianBlur antes del CLAHE para quitar ese ruido de alta frecuencia.
"""
import sys
import os

import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr.procesador_imagen import ProcesadorImagen


def _imagen_papel_sobre_fondo_color(alto=600, ancho=600):
    """Genera un fondo con color propio (tono calido, saturacion alta) y un
    rectangulo de "papel" blanco roto (saturacion casi nula) con un brillo
    medio DELIBERADAMENTE parecido al del fondo, para que un metodo basado
    solo en brillo (escala de grises) no pueda separarlos bien."""
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    # Fondo BGR calido con saturacion alta pero brillo medio parecido al papel
    img[:, :] = (140, 190, 225)
    # "Papel": rectangulo casi blanco (saturacion casi nula), ocupa el 60%
    y0, y1 = int(alto * 0.2), int(alto * 0.8)
    x0, x1 = int(ancho * 0.2), int(ancho * 0.8)
    img[y0:y1, x0:x1] = (235, 235, 235)
    return img, (x1 - x0), (y1 - y0)


def test_recorte_aisla_papel_de_fondo_con_saturacion_alta():
    procesador = ProcesadorImagen()
    img, ancho_papel, alto_papel = _imagen_papel_sobre_fondo_color()

    recortado = procesador._detectar_y_recortar_ticket(img)

    alto_resultado, ancho_resultado = recortado.shape[:2]
    area_resultado = alto_resultado * ancho_resultado
    area_papel = ancho_papel * alto_papel
    area_original = img.shape[0] * img.shape[1]

    # El recorte debe acercarse al tamaño real del papel (con margen), no
    # quedarse con casi toda la imagen original (que es lo que pasaba antes
    # cuando el fondo tenia un brillo parecido al del papel).
    assert area_resultado < 0.7 * area_original
    assert abs(area_resultado - area_papel) < 0.35 * area_papel


def test_procesar_atenua_ruido_iso_antes_del_clahe():
    """Compara el pipeline actual (medianBlur + CLAHE) contra el pipeline
    ANTERIOR (solo CLAHE, sin medianBlur) sobre la misma foto ruidosa: el
    CLAHE por si solo amplifica contraste local (sube el ruido de alta
    frecuencia tanto como el de antes), asi que la comparacion valida no es
    "ruido de entrada vs salida final" sino "salida CON el fix vs SIN el
    fix" para la misma imagen de partida."""
    procesador = ProcesadorImagen()

    base = np.full((300, 300, 3), 235, dtype=np.uint8)
    ruido = np.random.default_rng(42).normal(0, 25, base.shape[:2])
    con_ruido = base[:, :, 0].astype(np.float64) + ruido
    con_ruido = np.clip(con_ruido, 0, 255).astype(np.uint8)
    imagen_ruidosa = cv2.cvtColor(con_ruido, cv2.COLOR_GRAY2BGR)

    ok, buf = cv2.imencode(".png", imagen_ruidosa)
    assert ok
    resultado_con_fix = procesador.procesar(buf.tobytes())

    gray = cv2.cvtColor(imagen_ruidosa, cv2.COLOR_BGR2GRAY)
    gray = procesador._redimensionar_optimo(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    resultado_sin_fix = clahe.apply(gray)

    # Sobre una zona plana (sin texto), el ruido de alta frecuencia debe
    # quedar reducido con el medianBlur previo, frente a aplicar CLAHE solo.
    variacion_con_fix = float(np.std(resultado_con_fix))
    variacion_sin_fix = float(np.std(resultado_sin_fix))
    assert variacion_con_fix < variacion_sin_fix * 0.85
