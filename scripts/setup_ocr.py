"""Setup asistido para OCR - detección e instalación automática de
Tesseract, Poppler (pdftoppm) y libheif (heif-convert), las tres
dependencias de sistema que usa el escaneo de tickets."""
import subprocess
import sys
import platform
import shutil


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

SI_WINDOWS = platform.system() == "Windows"
SI_MAC = platform.system() == "Darwin"


def ejecutar_comando(cmd, timeout=600):
    """Ejecuta comando (lista de argv, sin shell) y devuelve (exitoso, output)."""
    try:
        resultado = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return resultado.returncode == 0, resultado.stdout + resultado.stderr
    except Exception as e:
        return False, str(e)


def verificar_binario(nombre_binario, etiqueta):
    """Comprueba si un binario de sistema está en el PATH."""
    print(f"\n{BOLD}Verificando {etiqueta}...{RESET}")
    ruta = shutil.which(nombre_binario)
    if ruta:
        print(f"{OK}{CHECK} {etiqueta} encontrado:{RESET} {ruta}")
        return True
    print(f"{ERROR}{CROSS} {etiqueta} NO encontrado{RESET}")
    return False


def verificar_python_deps():
    """Verifica dependencias Python."""
    print(f"\n{BOLD}Verificando dependencias Python...{RESET}")

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


def instalar_tesseract():
    """Instala Tesseract automáticamente según el SO."""
    print(f"\n{INFO}Instalando Tesseract OCR...{RESET}")
    if SI_WINDOWS:
        exitoso, output = ejecutar_comando(
            ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "-e", "--silent"]
        )
    elif SI_MAC:
        exitoso, output = ejecutar_comando(["brew", "install", "tesseract", "tesseract-lang"])
    else:
        ejecutar_comando(["sudo", "apt-get", "update", "-qq"])
        exitoso, output = ejecutar_comando(
            ["sudo", "apt-get", "install", "-y", "tesseract-ocr", "tesseract-ocr-spa"]
        )

    if exitoso:
        print(f"{OK}{CHECK} Tesseract instalado{RESET}")
    else:
        print(f"{ERROR}{CROSS} No se pudo instalar Tesseract automáticamente:{RESET}\n{output}")
        mostrar_instrucciones_manuales(
            "Tesseract",
            windows="https://github.com/UB-Mannheim/tesseract/wiki (tesseract-ocr-w64-setup, marca el idioma Spanish)",
            mac="brew install tesseract tesseract-lang",
            linux="sudo apt-get install tesseract-ocr tesseract-ocr-spa",
        )
    return exitoso


def instalar_poppler():
    """Instala Poppler (pdftoppm), necesario para escanear tickets en PDF."""
    print(f"\n{INFO}Instalando Poppler (pdftoppm)...{RESET}")
    if SI_WINDOWS:
        exitoso, output = ejecutar_comando(
            ["winget", "install", "--id", "oschwartz10612.Poppler", "-e", "--silent"]
        )
    elif SI_MAC:
        exitoso, output = ejecutar_comando(["brew", "install", "poppler"])
    else:
        ejecutar_comando(["sudo", "apt-get", "update", "-qq"])
        exitoso, output = ejecutar_comando(["sudo", "apt-get", "install", "-y", "poppler-utils"])

    if exitoso:
        print(f"{OK}{CHECK} Poppler instalado{RESET}")
    else:
        print(f"{ERROR}{CROSS} No se pudo instalar Poppler automáticamente:{RESET}\n{output}")
        mostrar_instrucciones_manuales(
            "Poppler",
            windows="winget install --id oschwartz10612.Poppler -e",
            mac="brew install poppler",
            linux="sudo apt-get install poppler-utils",
        )
    return exitoso


def instalar_libheif():
    """Instala libheif (heif-convert), necesario para escanear tickets HEIC/HEIF (fotos iOS)."""
    print(f"\n{INFO}Instalando libheif (heif-convert)...{RESET}")
    if SI_WINDOWS:
        # No hay paquete winget fiable de heif-convert para Windows; se deja manual.
        exitoso, output = False, "sin paquete winget disponible"
    elif SI_MAC:
        exitoso, output = ejecutar_comando(["brew", "install", "libheif"])
    else:
        ejecutar_comando(["sudo", "apt-get", "update", "-qq"])
        exitoso, output = ejecutar_comando(["sudo", "apt-get", "install", "-y", "libheif-examples"])

    if exitoso:
        print(f"{OK}{CHECK} libheif instalado{RESET}")
    else:
        print(f"{WARNING}[!!] No se pudo instalar libheif automáticamente:{RESET}\n{output}")
        mostrar_instrucciones_manuales(
            "libheif",
            windows="No hay instalador automático en Windows. Sin esto, los tickets en formato HEIC/HEIF (fotos de iPhone) no se pueden escanear; PNG/JPG sí funcionan igualmente.",
            mac="brew install libheif",
            linux="sudo apt-get install libheif-examples",
        )
    return exitoso


def mostrar_instrucciones_manuales(nombre, windows, mac, linux):
    print(f"\n{WARNING}Instalación manual de {nombre}:{RESET}")
    if SI_WINDOWS:
        print(f"  Windows: {windows}")
    elif SI_MAC:
        print(f"  macOS: {mac}")
    else:
        print(f"  Linux: {linux}")


def main():
    """Ejecuta setup completo: detecta y, si falta, instala."""
    print(f"\n{BOLD}{'='*60}")
    print(f"OCR SETUP - Tesseract + Poppler + libheif")
    print(f"{'='*60}{RESET}")

    tesseract_ok = verificar_binario("tesseract", "Tesseract OCR")
    if not tesseract_ok:
        tesseract_ok = instalar_tesseract()

    poppler_ok = verificar_binario("pdftoppm", "Poppler (lectura de tickets en PDF)")
    if not poppler_ok:
        poppler_ok = instalar_poppler()

    heif_ok = verificar_binario("heif-convert", "libheif (lectura de tickets HEIC/HEIF)")
    if not heif_ok:
        heif_ok = instalar_libheif()

    deps_ok = verificar_python_deps()
    todos_deps_ok = all(deps_ok.values())

    print(f"\n{BOLD}{'='*60}")
    print(f"RESUMEN{RESET}")
    print(f"{'='*60}")
    print(f"Tesseract OCR (PNG/JPG):        {f'{OK}{CHECK}{RESET}' if tesseract_ok else f'{ERROR}{CROSS} FALTA{RESET}'}")
    print(f"Poppler (PDF):                  {f'{OK}{CHECK}{RESET}' if poppler_ok else f'{WARNING}[!!] FALTA (sin esto, PDF no funciona){RESET}'}")
    print(f"libheif (HEIC/HEIF, fotos iOS): {f'{OK}{CHECK}{RESET}' if heif_ok else f'{WARNING}[!!] FALTA (sin esto, HEIC no funciona){RESET}'}")
    print(f"Dependencias Python:            {f'{OK}{CHECK} Todas OK{RESET}' if todos_deps_ok else f'{ERROR}{CROSS} Faltan algunas{RESET}'}")

    if not todos_deps_ok:
        print(f"\n{ERROR}Falta instalar (pip):{RESET}")
        for nombre, ok in deps_ok.items():
            if not ok:
                print(f"  - pip install {nombre}")

    if SI_WINDOWS and (tesseract_ok or poppler_ok):
        print(f"\n{WARNING}Si acabas de instalar algo nuevo, reinicia la terminal "
              f"(y el servidor Flask) para que recoja el PATH actualizado.{RESET}")

    print(f"\n{BOLD}{'='*60}")
    if tesseract_ok and todos_deps_ok:
        print(f"{OK}{CHECK} SISTEMA LISTO PARA OCR{RESET}")
        if not poppler_ok or not heif_ok:
            print(f"{WARNING}(PDF/HEIC parcialmente disponibles, ver arriba){RESET}")
        return 0
    else:
        print(f"{ERROR}{CROSS} FALTAN DEPENDENCIAS CRÍTICAS{RESET}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
