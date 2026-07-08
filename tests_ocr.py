"""Tests exhaustivos para sistema OCR."""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr import (
    ProcesadorImagen,
    ExtractorTexto,
    ParseadorTicket,
    MatcherProductos,
    GestorOCR,
)
from stockhogar.servicios.ocr.parseador_ticket import LineaTicket


class ColoresTerminal:
    """Colores para output en terminal."""
    OK = '\033[92m'
    ERROR = '\033[91m'
    INFO = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CHECK = '[OK]'
    CROSS = '[XX]'


def test_importes_dependencias():
    """Test 1: Validar que todas las dependencias se pueden importar."""
    print(f"\n{ColoresTerminal.BOLD}TEST 1: Importes de dependencias{ColoresTerminal.RESET}")

    deps = {
        "cv2": "opencv-python",
        "pytesseract": "pytesseract",
        "PIL": "Pillow",
        "fuzzywuzzy": "fuzzywuzzy",
        "numpy": "numpy",
    }

    todos_ok = True
    for modulo, nombre_pip in deps.items():
        try:
            __import__(modulo)
            print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} {nombre_pip}")
        except ImportError:
            print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} {nombre_pip} (FALTA INSTALAR)")
            todos_ok = False

    return todos_ok


def test_tesseract():
    """Test 2: Validar que Tesseract está instalado y funciona."""
    print(f"\n{ColoresTerminal.BOLD}TEST 2: Tesseract OCR{ColoresTerminal.RESET}")

    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Tesseract encontrado: {version}")
        return True
    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        print(f"    Instala: sudo apt-get install tesseract-ocr")
        return False


def test_procesador_imagen():
    """Test 3: Validar ProcesadorImagen."""
    print(f"\n{ColoresTerminal.BOLD}TEST 3: ProcesadorImagen{ColoresTerminal.RESET}")

    try:
        procesador = ProcesadorImagen()
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Instancia creada correctamente")

        # Validar propiedades
        assert hasattr(procesador, 'procesar'), "Falta método procesar"
        assert hasattr(procesador, 'width_optimo'), "Falta propiedad width_optimo"
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Métodos disponibles")

        return True
    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def test_extractor_texto():
    """Test 4: Validar ExtractorTexto."""
    print(f"\n{ColoresTerminal.BOLD}TEST 4: ExtractorTexto{ColoresTerminal.RESET}")

    try:
        extractor = ExtractorTexto(idioma="spa")
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Instancia creada correctamente")

        assert hasattr(extractor, 'extraer'), "Falta método extraer"
        assert hasattr(extractor, 'idioma'), "Falta propiedad idioma"
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Métodos disponibles")

        return True
    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def test_parseador_ticket():
    """Test 5: Validar ParseadorTicket con datos simulados."""
    print(f"\n{ColoresTerminal.BOLD}TEST 5: ParseadorTicket{ColoresTerminal.RESET}")

    try:
        parseador = ParseadorTicket()
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Instancia creada")

        # Test con texto simulado
        texto_simulado = """
        Leche entera 1 L ........................ 2,50€
        Pan integral 500g ...................... 1,80€
        Manzanas 2 kg @ 1,20€/kg .............. 2,40€
        Tomates pera 6 ud ...................... 3,20€
        """

        productos = parseador.parsear(texto_simulado)
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Parsing completado: {len(productos)} productos detectados")

        # Validar estructura
        if productos:
            p = productos[0]
            assert hasattr(p, 'nombre'), "Falta nombre"
            assert hasattr(p, 'cantidad'), "Falta cantidad"
            assert hasattr(p, 'precio_total'), "Falta precio"
            print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Estructura de LineaTicket correcta")

        return len(productos) > 0

    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def test_matcher_productos():
    """Test 6: Validar MatcherProductos con DB simulada."""
    print(f"\n{ColoresTerminal.BOLD}TEST 6: MatcherProductos{ColoresTerminal.RESET}")

    try:
        matcher = MatcherProductos()
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Instancia creada")

        # Test de sugerencias sin DB
        categoria = matcher.sugerir_categoria("Leche entera 1L")
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Categoría sugerida: {categoria}")

        icono = matcher.sugerir_icono("Manzanas rojas")
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Icono sugerido: {icono}")

        return True

    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def test_gestor_ocr():
    """Test 7: Validar GestorOCR estructura."""
    print(f"\n{ColoresTerminal.BOLD}TEST 7: GestorOCR{ColoresTerminal.RESET}")

    try:
        gestor = GestorOCR()
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Instancia creada")

        # Validar componentes
        assert hasattr(gestor, 'procesador'), "Falta procesador"
        assert hasattr(gestor, 'extractor'), "Falta extractor"
        assert hasattr(gestor, 'parseador'), "Falta parseador"
        assert hasattr(gestor, 'matcher'), "Falta matcher"
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Todos los componentes presentes")

        assert hasattr(gestor, 'procesar_ticket'), "Falta método procesar_ticket"
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Métodos principales presentes")

        return True

    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def test_endpoints_api():
    """Test 8: Validar que endpoint está registrado."""
    print(f"\n{ColoresTerminal.BOLD}TEST 8: Endpoints API{ColoresTerminal.RESET}")

    try:
        from stockhogar.rutas import ocr_tickets
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Módulo ocr_tickets importado")

        assert hasattr(ocr_tickets, 'bp'), "Falta blueprint"
        print(f"  {ColoresTerminal.OK}{ColoresTerminal.CHECK}{ColoresTerminal.RESET} Blueprint registrado")

        return True

    except Exception as e:
        print(f"  {ColoresTerminal.ERROR}{ColoresTerminal.CROSS}{ColoresTerminal.RESET} Error: {e}")
        return False


def main():
    """Ejecuta todos los tests."""
    print(f"\n{ColoresTerminal.BOLD}{'='*60}")
    print(f"TESTING EXHAUSTIVO - SISTEMA OCR TICKETS")
    print(f"{'='*60}{ColoresTerminal.RESET}")

    tests = [
        test_importes_dependencias,
        test_tesseract,
        test_procesador_imagen,
        test_extractor_texto,
        test_parseador_ticket,
        test_matcher_productos,
        test_gestor_ocr,
        test_endpoints_api,
    ]

    resultados = []
    for test in tests:
        try:
            resultado = test()
            resultados.append((test.__name__, resultado))
        except Exception as e:
            print(f"\n{ColoresTerminal.ERROR}{ColoresTerminal.CROSS} EXCEPCION NO MANEJADA en {test.__name__}: {e}{ColoresTerminal.RESET}")
            resultados.append((test.__name__, False))

    # Resumen
    print(f"\n{ColoresTerminal.BOLD}{'='*60}")
    print(f"RESUMEN{ColoresTerminal.RESET}")
    print(f"{'='*60}")

    pasados = sum(1 for _, r in resultados if r)
    totales = len(resultados)

    for nombre, resultado in resultados:
        estado = f"{ColoresTerminal.OK}{ColoresTerminal.CHECK} PASADO{ColoresTerminal.RESET}" if resultado else f"{ColoresTerminal.ERROR}{ColoresTerminal.CROSS} FALLIDO{ColoresTerminal.RESET}"
        print(f"  {nombre}: {estado}")

    print(f"\n{ColoresTerminal.BOLD}Total: {pasados}/{totales} tests pasados{ColoresTerminal.RESET}")

    if pasados == totales:
        print(f"{ColoresTerminal.OK}\n[EXITO] TODOS LOS TESTS PASARON - SISTEMA LISTO{ColoresTerminal.RESET}")
        return 0
    else:
        print(f"{ColoresTerminal.ERROR}\n[ALERTA] ALGUNOS TESTS FALLARON - REVISA ARRIBA{ColoresTerminal.RESET}")
        return 1


if __name__ == "__main__":
    exit(main())
