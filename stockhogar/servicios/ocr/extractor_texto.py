"""Extracción de texto desde imágenes usando Tesseract OCR."""
import pytesseract
import cv2
import re
from typing import Tuple


class ExtractorTexto:
    """Extrae texto de imágenes usando Tesseract.

    - OCR local sin APIs externas
    - Limpieza y normalización de texto
    - Detección de confianza
    """

    def __init__(self, idioma="spa"):
        """
        Args:
            idioma: Código de idioma para Tesseract (spa=español)
        """
        self.idioma = idioma
        self._tesseract_disponible = None

    def _verificar_tesseract(self):
        """Verifica si Tesseract está disponible (lazy check)."""
        if self._tesseract_disponible is None:
            try:
                pytesseract.get_tesseract_version()
                self._tesseract_disponible = True
            except Exception:
                self._tesseract_disponible = False
        return self._tesseract_disponible

    def extraer(self, imagen_procesada) -> Tuple[str, float]:
        """Extrae texto y devuelve (texto, confianza).

        Args:
            imagen_procesada: Imagen en escala de grises (np.ndarray)

        Returns:
            Tuple[str, float]: (texto extraído, confianza 0-100)
        """
        if not self._verificar_tesseract():
            raise RuntimeError(
                "Tesseract no está instalado. "
                "Instala: sudo apt-get install tesseract-ocr"
            )

        try:
            # Configuración de Tesseract
            config = f"--psm 6 -l {self.idioma}"
            # PSM 6 = Asumir un bloque de texto uniforme

            # Extraer texto
            texto = pytesseract.image_to_string(imagen_procesada, config=config)

            # Obtener confianza
            datos = pytesseract.image_to_data(
                imagen_procesada, config=config, output_type=pytesseract.Output.DICT
            )
            confianza = self._calcular_confianza(datos)

            # Limpiar texto
            texto = self._limpiar_texto(texto)

            return texto, confianza

        except Exception as e:
            raise RuntimeError(f"Error en OCR: {e}") from e

    def _calcular_confianza(self, datos) -> float:
        """Calcula confianza promedio del OCR."""
        confianzas = []
        for conf in datos["conf"]:
            try:
                conf_val = int(conf)
                if conf_val > 0:  # Ignora valores inválidos
                    confianzas.append(conf_val)
            except (ValueError, TypeError):
                pass

        if confianzas:
            return sum(confianzas) / len(confianzas)
        return 0

    def _limpiar_texto(self, texto: str) -> str:
        """Limpia y normaliza el texto extraído."""
        # Normalizar espacios
        texto = re.sub(r"\s+", " ", texto)

        # Eliminar caracteres especiales problemáticos
        texto = re.sub(r"[^\w\s.,€$¢-]", "", texto)

        # Normalizar puntuación
        texto = re.sub(r"\.+", ".", texto)
        texto = re.sub(r",+", ",", texto)

        # Trim
        texto = texto.strip()

        return texto
