"""Genera stockhogar/static/icons/mantenimiento.gif: escena animada de
"obras" (senal de stop + conos + operario cavando con una pala) para la
pantalla de mantenimiento de Dreame!, en estilo flat moderno.

Tecnica: se dibuja cada frame en RGBA a 4x resolucion (supersampling) y se
reescala con LANCZOS para conseguir bordes suavizados (antialiasing real,
sombras difuminadas, etc.) en vez de los bordes duros de ImageDraw. Como el
GIF no soporta canal alfa, al final se compone todo sobre un color clave, se
calcula UNA paleta a partir de todos los frames apilados (para que el indice
"transparente" sea el mismo en todos) y se cuantiza cada frame contra esa
misma paleta.

Uso: venv/Scripts/python.exe scripts/generar_gif_mantenimiento.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ESCALA = 4
# Espacio de diseño (donde estan pensadas todas las coordenadas de las
# funciones dibuja_*). La resolucion final del GIF es mayor (ver
# SALIDA_ANCHO/SALIDA_ALTO) para que se vea nitido al mostrarse mas grande
# en pantalla, pero el "layout" de la escena no cambia.
ANCHO, ALTO = 320, 220
ANCHO_SS, ALTO_SS = ANCHO * ESCALA, ALTO * ESCALA
SALIDA_ESCALA = 2
SALIDA_ANCHO, SALIDA_ALTO = ANCHO * SALIDA_ESCALA, ALTO * SALIDA_ESCALA
FRAMES = 28
DURACION_MS = 80

# Colores de marca (ver stockhogar/static/style.css: --accent, --warn, --danger).
NARANJA = (181, 85, 26)
NARANJA_CLARO = (222, 141, 84)
BLANCO = (255, 255, 255)
GRIS_OSCURO = (43, 38, 32)
ROJO = (193, 68, 58)
ROJO_OSCURO = (150, 50, 44)
AMARILLO = (238, 178, 44)
AMARILLO_OSCURO = (198, 143, 30)
PIEL = (222, 168, 128)
MONO = (74, 90, 112)
MONO_OSCURO = (54, 66, 84)
REFLECTANTE = (238, 210, 90)
GRIS_PALA = (191, 194, 199)
GRIS_PALA_OSCURO = (146, 149, 155)
MARRON_MANGO = (134, 89, 52)
TIERRA = (109, 78, 51)
TIERRA_CLARA = (140, 101, 66)
SOMBRA = (20, 15, 10)

FUENTE_STOP = None
for candidato in ("arialbd.ttf",):
    try:
        FUENTE_STOP = ImageFont.truetype(candidato, 17 * ESCALA)
        break
    except OSError:
        continue
if FUENTE_STOP is None:
    FUENTE_STOP = ImageFont.load_default()


def ease_dentro_fuera(t):
    """Suaviza 0..1..0 (t normalizado en un ciclo) para que el movimiento
    acelere/frene en los extremos en vez de ir a velocidad constante."""
    return 0.5 - 0.5 * math.cos(t * math.pi)


def sombra_elipse(draw, cx, cy, rx, ry, opacidad=95):
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*SOMBRA, opacidad))


def dibuja_suelo(draw):
    y = ALTO_SS - 20 * ESCALA
    draw.rectangle([0, y, ANCHO_SS, y + 5 * ESCALA], fill=(*GRIS_OSCURO, 255))
    draw.rectangle([0, y + 5 * ESCALA, ANCHO_SS, ALTO_SS], fill=(*MONO_OSCURO, 60))


def dibuja_stop(draw, cx, cy, radio):
    cx, cy, radio = cx * ESCALA, cy * ESCALA, radio * ESCALA
    poste_ancho = 5 * ESCALA
    draw.rounded_rectangle(
        [cx - poste_ancho / 2, cy + radio * 0.55, cx + poste_ancho / 2, ALTO_SS - 20 * ESCALA],
        radius=poste_ancho / 2, fill=(*GRIS_OSCURO, 255),
    )
    octagono = [(cx + math.cos(math.radians(22.5 + i * 45)) * radio,
                 cy + math.sin(math.radians(22.5 + i * 45)) * radio) for i in range(8)]
    draw.polygon(octagono, fill=(*ROJO_OSCURO, 255))
    octagono_i = [(cx + math.cos(math.radians(22.5 + i * 45)) * (radio - 5 * ESCALA),
                   cy + math.sin(math.radians(22.5 + i * 45)) * (radio - 5 * ESCALA)) for i in range(8)]
    draw.polygon(octagono_i, fill=(*ROJO, 255))
    octagono_borde = [(cx + math.cos(math.radians(22.5 + i * 45)) * (radio - 9 * ESCALA),
                        cy + math.sin(math.radians(22.5 + i * 45)) * (radio - 9 * ESCALA)) for i in range(8)]
    draw.polygon(octagono_borde, outline=(*BLANCO, 255), width=int(3.2 * ESCALA))
    texto = "STOP"
    caja = draw.textbbox((0, 0), texto, font=FUENTE_STOP)
    aw, ah = caja[2] - caja[0], caja[3] - caja[1]
    draw.text((cx - aw / 2 - caja[0], cy - ah / 2 - caja[1] - ESCALA), texto, font=FUENTE_STOP, fill=(*BLANCO, 255))


def dibuja_cono(draw, cx, base_y, altura, ancho_base, sombra=True):
    cx, base_y = cx * ESCALA, base_y * ESCALA
    altura, ancho_base = altura * ESCALA, ancho_base * ESCALA
    if sombra:
        sombra_elipse(draw, cx, base_y + 3 * ESCALA, ancho_base * 0.62, 5 * ESCALA, 70)
    punta = (cx, base_y - altura)
    base_izq = (cx - ancho_base / 2, base_y)
    base_der = (cx + ancho_base / 2, base_y)
    draw.polygon([punta, base_izq, base_der], fill=(*NARANJA, 255))
    draw.polygon([punta, (cx, base_y - altura * 0.15), base_der], fill=(*NARANJA_CLARO, 130))
    for frac, alto_franja in ((0.4, 0.15), (0.66, 0.17)):
        y = base_y - altura * frac
        medio_ancho = ancho_base / 2 * (1 - frac) + 3 * ESCALA
        draw.polygon([
            (cx - medio_ancho, y + altura * alto_franja / 2),
            (cx + medio_ancho, y + altura * alto_franja / 2),
            (cx + medio_ancho * 0.8, y - altura * alto_franja / 2),
            (cx - medio_ancho * 0.8, y - altura * alto_franja / 2),
        ], fill=(*BLANCO, 255))
    base_h = altura * 0.18
    draw.rounded_rectangle(
        [cx - ancho_base / 2 - 5 * ESCALA, base_y, cx + ancho_base / 2 + 5 * ESCALA, base_y + base_h],
        radius=2 * ESCALA, fill=(*GRIS_OSCURO, 255),
    )


def capsula(draw, p1, p2, ancho, color, alpha=255):
    r = ancho / 2
    draw.line([p1, p2], fill=(*color, alpha), width=int(ancho))
    draw.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=(*color, alpha))
    draw.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=(*color, alpha))


def dibuja_monticulo(draw, cx, base_y):
    cx, base_y = cx * ESCALA, base_y * ESCALA
    sombra_elipse(draw, cx, base_y + 5 * ESCALA, 20 * ESCALA, 4 * ESCALA, 60)
    draw.ellipse([cx - 18 * ESCALA, base_y - 6 * ESCALA, cx + 18 * ESCALA, base_y + 7 * ESCALA], fill=(*TIERRA, 255))
    draw.ellipse([cx - 13 * ESCALA, base_y - 9 * ESCALA, cx + 6 * ESCALA, base_y + 1 * ESCALA], fill=(*TIERRA_CLARA, 255))


def dibuja_particulas(draw, cx, pala_y, intensidad):
    if intensidad <= 0:
        return
    cx, pala_y = cx * ESCALA, pala_y * ESCALA
    for i, (dx, dy, r) in enumerate(((-14, -30, 3), (2, -38, 2.4), (16, -26, 3.2))):
        alpha = int(220 * intensidad)
        x, y = cx + dx * ESCALA, pala_y + dy * ESCALA
        rad = r * ESCALA * (0.6 + 0.4 * intensidad)
        draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(*TIERRA_CLARA, alpha))


def dibuja_operario(draw, cx, pies_y, t):
    """t en [0,1): ciclo completo de cavar. El brazo se mueve siempre por el
    lado delantero (derecha) del cuerpo -de arriba a abajo y vuelta- para que
    nunca cruce por delante de la cara; el agachado y las particulas de
    tierra usan la misma fase para que el "impacto" ocurra cuando la pala
    esta mas abajo (t=0.5)."""
    fase_golpe = 0.5 - 0.5 * math.cos(2 * math.pi * t)  # 0 arriba -> 1 abajo -> 0 arriba
    angulo_brazo = math.radians(-70 + fase_golpe * 140)
    agache_px = fase_golpe * 5 * ESCALA

    cx_px, pies_y_px = cx * ESCALA, pies_y * ESCALA
    bamboleo = math.sin(t * 2 * math.pi) * 1.2 * ESCALA

    cadera_y = pies_y_px - 42 * ESCALA + agache_px
    hombro_y = cadera_y - 26 * ESCALA + agache_px * 0.4
    cabeza_y = hombro_y - 15 * ESCALA

    sombra_elipse(draw, cx_px, pies_y_px + 2 * ESCALA, 22 * ESCALA, 5 * ESCALA, 90)

    # Piernas (capsulas para bordes redondeados)
    capsula(draw, (cx_px - 6 * ESCALA, pies_y_px), (cx_px - 6 * ESCALA + bamboleo, cadera_y), 6.5 * ESCALA, MONO_OSCURO)
    capsula(draw, (cx_px + 6 * ESCALA, pies_y_px), (cx_px + 6 * ESCALA + bamboleo, cadera_y), 6.5 * ESCALA, MONO_OSCURO)
    # Botas
    for signo in (-1, 1):
        bx = cx_px + signo * 6 * ESCALA
        draw.ellipse([bx - 6 * ESCALA, pies_y_px - 3 * ESCALA, bx + 6 * ESCALA, pies_y_px + 4 * ESCALA],
                     fill=(*GRIS_OSCURO, 255))

    # Torso con "squash": se achata un poco al agacharse
    achate = 1 - fase_golpe * 0.16
    alto_torso = 30 * ESCALA * achate
    draw.rounded_rectangle(
        [cx_px - 13 * ESCALA + bamboleo, cadera_y - alto_torso, cx_px + 13 * ESCALA + bamboleo, cadera_y + 5 * ESCALA],
        radius=8 * ESCALA, fill=(*MONO, 255),
    )
    draw.rounded_rectangle(
        [cx_px - 13 * ESCALA + bamboleo, cadera_y - alto_torso * 0.55,
         cx_px + 13 * ESCALA + bamboleo, cadera_y - alto_torso * 0.4],
        radius=3 * ESCALA, fill=(*REFLECTANTE, 255),
    )

    # Brazo trasero (queda debajo del torso, se dibuja antes de la cabeza)
    hombro_tras = (cx_px - 11 * ESCALA + bamboleo, hombro_y + 3 * ESCALA)
    capsula(draw, hombro_tras, (hombro_tras[0] - 3 * ESCALA, hombro_tras[1] + 16 * ESCALA), 6 * ESCALA, MONO)

    # Cabeza + casco
    cx_cabeza = cx_px + bamboleo
    draw.ellipse([cx_cabeza - 10 * ESCALA, cabeza_y - 10 * ESCALA, cx_cabeza + 10 * ESCALA, cabeza_y + 10 * ESCALA],
                 fill=(*PIEL, 255))
    draw.pieslice(
        [cx_cabeza - 12.5 * ESCALA, cabeza_y - 17 * ESCALA, cx_cabeza + 12.5 * ESCALA, cabeza_y + 3 * ESCALA],
        180, 360, fill=(*AMARILLO, 255),
    )
    draw.rounded_rectangle(
        [cx_cabeza - 13.5 * ESCALA, cabeza_y - 2.5 * ESCALA, cx_cabeza + 13.5 * ESCALA, cabeza_y + 1 * ESCALA],
        radius=2 * ESCALA, fill=(*AMARILLO_OSCURO, 255),
    )

    # Brazo delantero + pala
    hombro_del = (cx_px + 15 * ESCALA + bamboleo, hombro_y + 3 * ESCALA)
    mano = (hombro_del[0] + math.cos(angulo_brazo) * 24 * ESCALA, hombro_del[1] + math.sin(angulo_brazo) * 24 * ESCALA)
    capsula(draw, hombro_del, mano, 6 * ESCALA, PIEL)

    dir_pala = (math.cos(angulo_brazo), math.sin(angulo_brazo))
    punta_pala = (mano[0] + dir_pala[0] * 32 * ESCALA, mano[1] + dir_pala[1] * 32 * ESCALA)
    capsula(draw, mano, punta_pala, 3.2 * ESCALA, MARRON_MANGO)
    perp = (-dir_pala[1], dir_pala[0])
    ancho_hoja = 8 * ESCALA
    p1 = (punta_pala[0] + perp[0] * ancho_hoja, punta_pala[1] + perp[1] * ancho_hoja)
    p2 = (punta_pala[0] - perp[0] * ancho_hoja, punta_pala[1] - perp[1] * ancho_hoja)
    p3 = (punta_pala[0] + dir_pala[0] * 15 * ESCALA, punta_pala[1] + dir_pala[1] * 15 * ESCALA)
    draw.polygon([p1, p2, p3], fill=(*GRIS_PALA, 255), outline=(*GRIS_PALA_OSCURO, 255), width=int(1.2 * ESCALA))

    # Particulas de tierra saltando justo cuando la pala esta mas abajo
    intensidad_impacto = max(0.0, (fase_golpe - 0.75) * 4)
    if intensidad_impacto > 0:
        dibuja_particulas(draw, cx + 30, pies_y - 4, min(1.0, intensidad_impacto))


def genera_frame(i):
    t = i / FRAMES
    img = Image.new("RGBA", (ANCHO_SS, ALTO_SS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    dibuja_suelo(draw)
    dibuja_stop(draw, 46, 62, 34)
    dibuja_monticulo(draw, 210, 202)
    dibuja_cono(draw, 268, 200, 50, 34)
    dibuja_cono(draw, 296, 200, 40, 28)
    dibuja_operario(draw, 165, 200, t)
    return img


def genera():
    frames_alta_res = [genera_frame(i) for i in range(FRAMES)]

    # Reescalado con LANCZOS conservando el canal alfa (no se compone sobre
    # ningun color de fondo antes de reescalar): asi el borde de cada forma
    # se difumina hacia "transparente", no hacia un color clave, y no deja
    # un halo con el color clave alrededor de las figuras. Se reescala a
    # SALIDA_ANCHO/SALIDA_ALTO (mayor que el espacio de diseno) para que el
    # GIF se vea nitido al mostrarse mas grande en pantallas anchas.
    frames_rgba = [f.resize((SALIDA_ANCHO, SALIDA_ALTO), Image.LANCZOS) for f in frames_alta_res]

    UMBRAL_ALFA = 128  # por debajo: transparente; por encima: opaco
    INDICE_TRANSPARENTE = 255

    # Paleta unica calculada sobre los pixeles OPACOS de todos los frames a
    # la vez, para que el mismo color use siempre el mismo indice.
    opacos_por_frame = []
    tira_filas = []
    for f in frames_rgba:
        arr = np.asarray(f, dtype=np.int32)
        opaco = arr[:, :, 3] >= UMBRAL_ALFA
        opacos_por_frame.append(opaco)
        tira_filas.append(arr[:, :, :3])
    tira_rgb = np.concatenate(tira_filas, axis=0)
    tira_img = Image.fromarray(tira_rgb.astype(np.uint8), mode="RGB")
    paleta_ref = tira_img.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.NONE)
    colores_paleta = np.array(paleta_ref.getpalette()[:255 * 3]).reshape(-1, 3).astype(np.int32)

    frames_p = []
    for f, opaco in zip(frames_rgba, opacos_por_frame):
        pixeles = np.asarray(f, dtype=np.int32)[:, :, :3]  # (SALIDA_ALTO, SALIDA_ANCHO, 3)
        # Distancia al cuadrado de cada pixel a cada color de la paleta;
        # se procesa por filas para no disparar el uso de memoria.
        indices = np.empty((SALIDA_ALTO, SALIDA_ANCHO), dtype=np.uint8)
        for y in range(SALIDA_ALTO):
            fila = pixeles[y]  # (SALIDA_ANCHO, 3)
            dist = ((fila[:, None, :] - colores_paleta[None, :, :]) ** 2).sum(axis=-1)
            indices[y] = dist.argmin(axis=-1)
        indices[~opaco] = INDICE_TRANSPARENTE

        frame_p = Image.fromarray(indices, mode="P")
        paleta_final = paleta_ref.getpalette()[:255 * 3] + [0, 0, 0]
        frame_p.putpalette(paleta_final)
        frame_p.info["transparency"] = INDICE_TRANSPARENTE
        frames_p.append(frame_p)
    indice_transparente = INDICE_TRANSPARENTE

    salida = Path(__file__).resolve().parent.parent / "stockhogar" / "static" / "icons" / "mantenimiento.gif"
    frames_p[0].save(
        salida, save_all=True, append_images=frames_p[1:], duration=DURACION_MS,
        loop=0, disposal=2, transparency=indice_transparente,
    )
    print(f"Generado: {salida} (indice transparente={indice_transparente}, frames={FRAMES})")


if __name__ == "__main__":
    genera()
