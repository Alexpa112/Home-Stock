"""Procesamiento y preprocesamiento de imágenes de tickets."""
import cv2
import numpy as np
from PIL import Image
import io


class ProcesadorImagen:
    """Preprocesa imágenes para mejorar OCR.

    - Ajusta orientación
    - Mejora contraste y brillo
    - Redimensiona para OCR óptimo
    - Elimina ruido
    """

    def __init__(self):
        self.width_optimo = 2000  # Ancho óptimo para OCR

    def procesar(self, imagen_bytes):
        """Procesa imagen bytes y devuelve imagen mejorada.

        Args:
            imagen_bytes: Bytes de la imagen (PNG, JPG)

        Returns:
            np.ndarray: Imagen procesada en escala de grises
        """
        # Cargar imagen
        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("No se pudo decodificar la imagen")

        # Detectar y corregir orientación
        img = self._corregir_orientacion(img)

        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Redimensionar para OCR óptimo
        gray = self._redimensionar_optimo(gray)

        # Mejorar contraste (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Reducir ruido
        gray = cv2.bilateralFilter(gray, 9, 75, 75)

        # Binarización adaptativa
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return gray

    def _corregir_orientacion(self, img):
        """Detecta y corrige la orientación de la imagen."""
        angulo = self._detectar_angulo_rotacion(img)
        if angulo != 0:
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angulo, 1.0)
            img = cv2.warpAffine(
                img, M, (w, h), borderMode=cv2.BORDER_REPLICATE
            )
        return img

    def _detectar_angulo_rotacion(self, img):
        """Detecta si la imagen está rotada y devuelve el ángulo de corrección.

        Canny+HoughLines se ejecutan sobre una copia reducida (máx. 800px de
        ancho) en vez de la foto original: en fotos de móvil de varios
        megapíxeles esto era el cuello de botella de rendimiento en hardware
        limitado (Raspberry Pi), sin aportar precisión extra a la detección
        de ángulo.
        """
        h, w = img.shape[:2]
        if w > 800:
            escala = 800 / w
            muestra = cv2.resize(img, (800, int(h * escala)))
        else:
            muestra = img

        gray = cv2.cvtColor(muestra, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Detectar líneas (tickets suelen tener líneas de texto horizontales)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)

        if lines is None:
            return 0

        angulos = []
        for line in lines:
            rho, theta = line[0]
            # theta es el ángulo de la NORMAL a la línea: para una línea ya
            # horizontal theta ≈ 90°, así que hay que restar 90 para obtener
            # el ángulo de desviación real (0 = ya recta). Sin esta resta,
            # un ticket bien orientado se detectaba como rotado ~90° y se
            # giraba de lado, dejando el texto en vertical e inutilizable
            # para Tesseract.
            angulo = np.degrees(theta) - 90
            # Normalizar a (-45, 45]
            if angulo > 45:
                angulo -= 90
            elif angulo < -45:
                angulo += 90
            angulos.append(angulo)

        angulo_promedio = np.median(angulos)
        # Si está rotado más de 5 grados, corregir
        if abs(angulo_promedio) > 5:
            return float(angulo_promedio)

        return 0

    def _redimensionar_optimo(self, img):
        """Redimensiona imagen para OCR óptimo (ancho ~2000px)."""
        h, w = img.shape[:2]
        escala = self.width_optimo / w
        nuevo_ancho = self.width_optimo
        nuevo_alto = int(h * escala)

        # Asegurar que no sea muy pequeño
        if nuevo_alto < 200:
            return img

        return cv2.resize(img, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_CUBIC)
