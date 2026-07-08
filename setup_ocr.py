"""Setup asistido para OCR - detección y instalación automática."""
import subprocess
import sys
import os
import platform


class ColoresTerminal:
    OK = '\033[92m'
    ERROR = '\033[91m'
    WARNING = '\033[93m'
    INFO = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    CHECK = '[OK]'
    CROSS = '[XX]'


OK = ColoresTerminal.OK
ERROR = ColoresTerminal.ERROR
WARNING = ColoresTerminal.WARNING
INFO = ColoresTerminal.INFO
BOLD = ColoresTerminal.BOLD
RESET = ColoresTerminal.RESET
CHECK = ColoresTerminal.CHECK
CROSS = ColoresTerminal.CROSS


def ejecutar_comando(cmd):
    """Ejecuta comando y devuelve (exitoso, output)."""
    try:
        resultado = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return resultado.returncode == 0, resultado.stdout + resultado.stderr
    except Exception as e:
        return False, str(e)


def verificar_tesseract():
    """Verifica si Tesseract está instalado."""
    print(f"\n{BOLD}[1] Verificando Tesseract...{RESET}")

    # Intenta encontrar tesseract
    si_windows = platform.system() == "Windows"
    if si_windows:
        cmd = "where tesseract"
    else:
        cmd = "which tesseract"

    exitoso, output = ejecutar_comando(cmd)

    if exitoso:
        print(f"{OK}{CHECK} Tesseract encontrado:{RESET} {output.strip()}")
        return True, output.strip()
    else:
        print(f"{ERROR}{CROSS} Tesseract NO encontrado{RESET}")
        return False, None


def verificar_python_deps():
    """Verifica dependencias Python."""
    print(f"\n{BOLD}[2] Verificando dependencias Python...{RESET}")

    deps = {
        "cv2": "opencv-python",
        "pytesseract": "pytesseract",
        "PIL": "Pillow",
        "fuzzywuzzy": "fuzzywuzzy",
        "numpy": "numpy",
    }

    resultado = {}
    for modulo, nombre in deps.items():
        try:
            __import__(modulo)
            print(f"{OK}{CHECK}{RESET} {nombre}")
            resultado[nombre] = True
        except ImportError:
            print(f"{ERROR}{CROSS}{RESET} {nombre} (FALTA)")
            resultado[nombre] = False

    return resultado


def mostrar_instrucciones_tesseract():
    """Muestra instrucciones para instalar Tesseract."""
    print(f"\n{WARNING}{BOLD}{'='*60}")
    print(f"INSTALACIÓN DE TESSERACT OCR")
    print(f"{'='*60}{RESET}")

    si_windows = platform.system() == "Windows"

    if si_windows:
        print(f"\n{INFO}Windows:{RESET}")
        print(f"""
1. Descargar instalador:
   https://github.com/UB-Mannheim/tesseract/wiki

2. Descargar: tesseract-ocr-w64-setup-v5.x.exe

3. Ejecutar el instalador

4. Elegir: Instalar en C:\\Program Files\\Tesseract-OCR

5. Cuando pregunte por idiomas, seleccionar:
   - English
   - Spanish (ESP)

6. Completar la instalación

7. Añadir al PATH (si no se hace automáticamente):
   - Panel de Control > Variables de entorno
   - Agregar: C:\\Program Files\\Tesseract-OCR
   - Reiniciar terminal

8. Verificar:
   tesseract --version
""")
    else:
        print(f"\n{INFO}Linux/Mac:{RESET}")
        print(f"""
1. Ubuntu/Debian:
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-spa

2. MacOS:
   brew install tesseract

3. Verificar:
   tesseract --version
""")


def crear_tesseract_mock():
    """Crea un módulo mock de Tesseract para testing sin instalación."""
    print(f"\n{WARNING}Creando módulo mock para testing sin Tesseract...{RESET}")

    mock_code = '''"""Mock de pytesseract para testing sin Tesseract instalado."""

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
'''

    ruta_mock = os.path.join(
        os.path.dirname(__file__),
        "stockhogar/servicios/ocr/tesseract_mock.py"
    )

    with open(ruta_mock, "w") as f:
        f.write(mock_code)

    print(f"{OK}{CHECK} Mock creado en:{RESET} {ruta_mock}")
    return ruta_mock


def main():
    """Ejecuta setup completo."""
    print(f"\n{BOLD}{'='*60}")
    print(f"OCR SETUP ASISTIDO - Verificación de dependencias")
    print(f"{'='*60}{RESET}")

    # Verificar Tesseract
    tesseract_ok, ruta_tesseract = verificar_tesseract()

    # Verificar Python deps
    deps_ok = verificar_python_deps()
    todos_deps_ok = all(deps_ok.values())

    # Resumen
    print(f"\n{BOLD}{'='*60}")
    print(f"RESUMEN{RESET}")
    print(f"{'='*60}")

    print(f"\nTesseract OCR (sistema):     {
        f'{OK}{CHECK}{RESET}' if tesseract_ok else f'{ERROR}{CROSS}{RESET} FALTA INSTALAR'
    }")
    print(f"Dependencias Python:        {
        f'{OK}{CHECK} Todas OK{RESET}' if todos_deps_ok else f'{ERROR}{CROSS} Faltan algunas{RESET}'
    }")

    if not todos_deps_ok:
        print(f"\n{ERROR}Falta instalar:{RESET}")
        for nombre, ok in deps_ok.items():
            if not ok:
                print(f"  - pip install {nombre}")

    if not tesseract_ok:
        mostrar_instrucciones_tesseract()
        crear_tesseract_mock()
        print(f"\n{WARNING}NOTA:{RESET} Se creó un mock de Tesseract para testing.")
        print(f"Para OCR real, instala Tesseract desde el enlace arriba.")

    # Status final
    print(f"\n{BOLD}{'='*60}")
    if tesseract_ok and todos_deps_ok:
        print(f"{OK}{CHECK} SISTEMA LISTO PARA OCR COMPLETO{RESET}")
        return 0
    elif todos_deps_ok:
        print(f"{WARNING}[!!] SISTEMA PARCIALMENTE LISTO (mock para testing){RESET}")
        return 1
    else:
        print(f"{ERROR}{CROSS} FALTAN DEPENDENCIAS{RESET}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
