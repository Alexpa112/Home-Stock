"""Mock de pytesseract para testing sin Tesseract instalado."""

class TesseractNotFoundError(Exception):
    """Simulación de error de Tesseract."""
    pass


def get_tesseract_version():
    """Retorna versión simulada."""
    return "Mock Tesseract 5.0.0"


def image_to_string(image, config=""):
    """Simula extracción de texto.

    Para testing: retorna texto simulado de un ticket.
    """
    return """
    Leche entera 1L .................................... 2,50€
    Pan integral 500g .................................. 1,80€
    Manzanas Fuji 2kg @ 1,20€/kg ....................... 2,40€
    Tomates pera 6 ud .................................. 3,20€
    Queso manchego 250g ................................. 5,90€
    TOTAL ................................................ 15,80€
    """


def image_to_data(image, config="", output_type=None):
    """Simula datos de confianza."""
    return {
        "conf": [85] * 20,  # Confianza simulada
        "text": ["Leche", "entera", "1L", "2,50€"],
    }
