"""Procesamiento y preprocesamiento de imágenes de tickets."""
import cv2
import numpy as np
from PIL import Image, ImageOps
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
        # Cargar imagen respetando el tag EXIF Orientation: cv2.imdecode lo
        # ignora por completo, y las fotos de movil en vertical (el caso
        # normal al fotografiar un ticket, sobre todo en iOS) guardan el
        # pixel en horizontal con ese tag puesto. Sin esta correccion el
        # ticket llega a Tesseract tumbado de lado y no reconoce nada.
        img = self._decodificar_respetando_exif(imagen_bytes)

        if img is None:
            nparr = np.frombuffer(imagen_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("No se pudo decodificar la imagen")

        # Detectar y recortar solo la zona del ticket (elimina fondo: mesa,
        # mano, etc.) antes de seguir procesando.
        img = self._detectar_y_recortar_ticket(img)

        # Detectar y corregir orientación
        img = self._corregir_orientacion(img)

        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Redimensionar para OCR óptimo
        gray = self._redimensionar_optimo(gray)

        # Quitar ruido ISO (fotos con poca luz) ANTES del CLAHE de abajo:
        # CLAHE amplifica el contraste local, y sobre una foto ruidosa
        # amplifica igual de fuerte el grano del sensor que las letras,
        # enterrando el texto bajo "nieve" (visto con una foto real tomada
        # con poca luz: Tesseract leía basura pese a que el recorte era
        # perfecto). medianBlur(5) quita ese grano de alta frecuencia sin
        # difuminar los trazos del texto (que son más gruesos que el ruido).
        # Se probó fastNlMeansDenoising (mejor calidad) pero tarda ~15s en
        # la Pi a 2000px de ancho, muy por encima del objetivo de <20s
        # total; medianBlur da una mejora casi tan buena en <1s.
        gray = cv2.medianBlur(gray, 5)

        # Mejorar contraste (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Nota: aquí había bilateralFilter + adaptiveThreshold (binarización).
        # Con tickets reales de impresora térmica (fuente de matriz de puntos)
        # la binarización rompe los trazos en fragmentos y dispara el tiempo
        # de Tesseract de segundos a varios minutos (o lo cuelga sin
        # terminar nunca), además de degradar la precisión del texto
        # reconocido. El gris con CLAHE, sin binarizar, es lo que Tesseract
        # procesa realmente rápido y bien en este tipo de tickets.
        return gray

    @staticmethod
    def _decodificar_respetando_exif(imagen_bytes):
        """Decodifica bytes de imagen a un array BGR de OpenCV, aplicando
        antes la rotación del tag EXIF Orientation si lo hay.

        Las fotos de móvil en vertical (el caso normal al fotografiar un
        ticket) suelen guardar el píxel en horizontal con un tag EXIF que
        indica "rota 90°" para verse en vertical -asi es como la app Camara
        de iOS guarda practicamente todas las fotos en vertical, y muchos
        Android hacen lo mismo-. cv2.imdecode ignora ese tag por completo,
        asi que sin esto el ticket llegaba a Tesseract tumbado de lado.
        """
        try:
            with Image.open(io.BytesIO(imagen_bytes)) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                pil_img = pil_img.convert("RGB")
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def _detectar_y_recortar_ticket(self, img):
        """Detecta el papel del ticket en la foto y recorta/endereza esa
        zona por perspectiva, descartando el fondo (mesa, mano, teclado...).

        Se busca sobre una copia reducida (máx. 800px) por rendimiento en
        Raspberry Pi. Si no se encuentra un contorno de papel claro (ticket
        pequeño, fondo muy parecido en brillo, etc.) se devuelve la imagen
        original sin recortar para no arriesgar perder contenido real.
        """
        h, w = img.shape[:2]
        escala = 800 / w if w > 800 else 1.0
        muestra = cv2.resize(img, (int(w * escala), int(h * escala))) if escala != 1.0 else img
        area_muestra = muestra.shape[0] * muestra.shape[1]
        kernel = np.ones((25, 25), np.uint8)

        # 1er intento: aislar el papel por SATURACIÓN (HSV), no por brillo.
        # El papel del ticket es blanco/gris (saturación casi nula) sea cual
        # sea la luz; fondos con color propio -piel, madera, tela vaquera-
        # tienen saturación alta aunque su brillo (escala de grises) sea
        # parecido al del papel, y en ese caso el umbral de grises de abajo
        # no distingue papel de fondo en absoluto (contorno == casi toda la
        # foto, se recortaba fatal). Ver ticket real que fallaba: foto sobre
        # la pierna, el papel y la piel tenían brillo similar pero
        # saturación muy distinta.
        hsv = cv2.cvtColor(muestra, cv2.COLOR_BGR2HSV)
        mascara_papel = cv2.inRange(hsv, (0, 0, 120), (180, 60, 255))
        cerrado = cv2.morphologyEx(mascara_papel, cv2.MORPH_CLOSE, kernel)
        contornos, _ = cv2.findContours(cerrado, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contorno = max(contornos, key=cv2.contourArea) if contornos else None

        if contorno is None or cv2.contourArea(contorno) < 0.15 * area_muestra:
            # 2º intento (fallback): el umbral de grises de siempre. Sirve
            # para fondos oscuros/uniformes donde la saturación no separa
            # bien el papel (poca luz, fondo también gris).
            gray = cv2.cvtColor(muestra, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, umbral = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            cerrado = cv2.morphologyEx(umbral, cv2.MORPH_CLOSE, kernel)
            contornos, _ = cv2.findContours(cerrado, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contorno = max(contornos, key=cv2.contourArea) if contornos else None

        if contorno is None or cv2.contourArea(contorno) < 0.15 * area_muestra:
            # Ningún método encontró un contorno fiable: no recortamos.
            return img

        hull = cv2.convexHull(contorno)
        perimetro = cv2.arcLength(hull, True)
        cuadrilatero = None
        for factor in (0.01, 0.02, 0.03, 0.05, 0.08):
            aprox = cv2.approxPolyDP(hull, factor * perimetro, True)
            if len(aprox) == 4:
                cuadrilatero = aprox
                break

        if cuadrilatero is None:
            # Fallback: rectángulo mínimo (menos preciso con papel inclinado,
            # pero mejor que no recortar nada).
            rect = cv2.minAreaRect(contorno)
            cuadrilatero = cv2.boxPoints(rect).reshape(-1, 1, 2).astype(int)

        puntos = cuadrilatero.reshape(4, 2).astype("float32") / escala
        origen = self._ordenar_puntos(puntos)
        (sup_izq, sup_der, inf_der, inf_izq) = origen

        ancho_final = int(max(
            np.linalg.norm(inf_der - inf_izq), np.linalg.norm(sup_der - sup_izq)
        ))
        alto_final = int(max(
            np.linalg.norm(sup_der - inf_der), np.linalg.norm(sup_izq - inf_izq)
        ))
        if ancho_final < 50 or alto_final < 50:
            return img

        destino = np.array([
            [0, 0], [ancho_final - 1, 0],
            [ancho_final - 1, alto_final - 1], [0, alto_final - 1],
        ], dtype="float32")
        matriz = cv2.getPerspectiveTransform(origen, destino)
        return cv2.warpPerspective(img, matriz, (ancho_final, alto_final))

    @staticmethod
    def _ordenar_puntos(puntos):
        """Ordena 4 puntos como (superior-izq, superior-der, inferior-der,
        inferior-izq) para usarlos como origen de una transformación de
        perspectiva."""
        rect = np.zeros((4, 2), dtype="float32")
        suma = puntos.sum(axis=1)
        rect[0] = puntos[np.argmin(suma)]
        rect[2] = puntos[np.argmax(suma)]
        diferencia = np.diff(puntos, axis=1)
        rect[1] = puntos[np.argmin(diferencia)]
        rect[3] = puntos[np.argmax(diferencia)]
        return rect

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
