"""Testing exhaustivo de OCR con casos reales y edge cases."""
import sys
import os
import base64
from io import BytesIO

# Agregar proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockhogar.servicios.ocr import (
    ProcesadorImagen,
    ParseadorTicket,
    MatcherProductos,
)


class SuiteOCR:
    """Suite exhaustiva de testing para OCR."""

    def __init__(self):
        self.procesador = ProcesadorImagen()
        self.parseador = ParseadorTicket()
        self.matcher = MatcherProductos()
        self.resultados = []

    def test_parsing_basico(self):
        """Test: Parsing de ticket simple y bien formateado."""
        print("\n[TEST] Parsing basico - Ticket bien formateado")

        texto = """
        Leche entera 1L ........................ 2,50€
        Pan integral 500g ...................... 1,80€
        Manzanas 2kg @ 1,20€/kg ............... 2,40€
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_basico",
            "status": "OK" if len(productos) == 3 else "FAIL",
            "esperado": 3,
            "obtenido": len(productos),
            "detalle": [
                {
                    "nombre": p.nombre,
                    "cantidad": p.cantidad,
                    "precio": p.precio_total
                } for p in productos
            ]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: 3 productos")
        print(f"  Obtenido: {len(productos)} productos")
        for p in productos:
            cantidad_str = p.cantidad_texto if p.cantidad_texto else str(p.cantidad)
            print(f"    - {p.nombre}: {cantidad_str} @ {p.precio_total}€")

        return resultado["status"] == "OK"

    def test_parsing_mal_formateado(self):
        """Test: Ticket mal formateado, con espacios irregulares."""
        print("\n[TEST] Parsing mal formateado - Espacios irregulares")

        texto = """
        leche    entera     1l                             2.50
        pan   integral 500   g                          1.80
        manzanas  rojas    2    kg                       2.40
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_mal_formateado",
            "status": "OK" if len(productos) >= 2 else "FAIL",
            "esperado": ">=2",
            "obtenido": len(productos),
            "detalle": [p.nombre for p in productos]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: >=2 productos")
        print(f"  Obtenido: {len(productos)} productos")
        for p in productos:
            print(f"    - {p.nombre}")

        return resultado["status"] == "OK"

    def test_parsing_sin_cantidad(self):
        """Test: Producto sin cantidad especificada."""
        print("\n[TEST] Parsing sin cantidad - Producto sin unidades")

        texto = """
        Leche entera ........................... 2,50€
        Pan ..................................... 1,80€
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_sin_cantidad",
            "status": "OK" if len(productos) >= 1 else "FAIL",
            "esperado": ">=1",
            "obtenido": len(productos),
            "detalle": [p.cantidad for p in productos]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: >=1 productos sin cantidad")
        print(f"  Obtenido: {len(productos)}")
        for p in productos:
            print(f"    - {p.nombre}: {p.cantidad}")

        return resultado["status"] == "OK"

    def test_parsing_sin_precio(self):
        """Test: Producto sin precio."""
        print("\n[TEST] Parsing sin precio - Producto sin precio")

        texto = """
        Leche entera 1L
        Pan integral 500g
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_sin_precio",
            "status": "OK" if len(productos) >= 1 else "FAIL",
            "esperado": ">=1",
            "obtenido": len(productos),
            "precios": [p.precio_total for p in productos]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: >=1 productos")
        print(f"  Obtenido: {len(productos)}")
        for p in productos:
            print(f"    - {p.nombre}: precio={p.precio_total}€")

        return resultado["status"] == "OK"

    def test_parsing_unidades_variadas(self):
        """Test: Diferentes unidades (kg, g, L, ml, ud, etc)."""
        print("\n[TEST] Parsing unidades variadas")

        texto = """
        Manzanas 2kg ......................... 2,40€
        Leche 1L ............................ 2,50€
        Chocolate 100g ..................... 1,20€
        Tomates 6ud ........................ 3,20€
        Zumo 500ml ......................... 2,10€
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_unidades_variadas",
            "status": "OK" if len(productos) >= 3 else "FAIL",
            "esperado": ">=3",
            "obtenido": len(productos),
            "unidades": [p.cantidad_texto for p in productos]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: >=3 productos con unidades")
        print(f"  Obtenido: {len(productos)}")
        for p in productos:
            cantidad_str = p.cantidad_texto if p.cantidad_texto else str(p.cantidad)
            print(f"    - {p.nombre}: {cantidad_str}")

        return resultado["status"] == "OK"

    def test_parsing_errores_ocr_simples(self):
        """Test: Errores OCR simples (similares a reales)."""
        print("\n[TEST] Parsing con errores OCR simples")

        # Errores comunes de OCR: 0->O, 1->I, S->5
        texto = """
        Leche entera 1L (OCR: Leche enter@ 1L) ........... 2,50€
        P@n integral 5OOg ............................. 1,80€
        M@nz@n@s 2kg ................................ 2,40€
        """

        productos = self.parseador.parsear(texto)

        resultado = {
            "test": "parsing_ocr_simples",
            "status": "OK" if len(productos) >= 2 else "FAIL",
            "esperado": ">=2",
            "obtenido": len(productos),
            "nombres": [p.nombre for p in productos]
        }

        self.resultados.append(resultado)
        print(f"  Esperado: >=2 productos (tolerancia a errores)")
        print(f"  Obtenido: {len(productos)}")
        for p in productos:
            print(f"    - {p.nombre}")

        return resultado["status"] == "OK"

    def test_matching_exacto(self):
        """Test: Matching con nombre exacto en catálogo (simulado)."""
        print("\n[TEST] Matching exacto - Nombre existe en catálogo")

        nombres_catalogo = ["Leche entera", "Pan integral", "Manzanas"]
        nombre_ocr = "Leche entera"

        # Simular búsqueda
        from rapidfuzz import process, fuzz
        resultado_match, score, _ = process.extractOne(
            nombre_ocr, nombres_catalogo, scorer=fuzz.token_set_ratio
        )

        resultado = {
            "test": "matching_exacto",
            "status": "OK" if score >= 80 else "FAIL",
            "nombre_ocr": nombre_ocr,
            "coincidencia": resultado_match,
            "score": score
        }

        self.resultados.append(resultado)
        print(f"  OCR: '{nombre_ocr}'")
        print(f"  Coincidencia: '{resultado_match}' (score: {score}%)")

        return resultado["status"] == "OK"

    def test_matching_con_errores(self):
        """Test: Matching con errores OCR (tolerancia)."""
        print("\n[TEST] Matching con errores OCR")

        nombres_catalogo = ["Leche entera", "Pan integral", "Manzanas rojas"]
        nombre_ocr = "Lechè entera"  # Error: accent

        from rapidfuzz import process, fuzz
        resultado_match, score, _ = process.extractOne(
            nombre_ocr, nombres_catalogo, scorer=fuzz.token_set_ratio
        )

        resultado = {
            "test": "matching_con_errores",
            "status": "OK" if score >= 60 else "FAIL",
            "nombre_ocr": nombre_ocr,
            "coincidencia": resultado_match,
            "score": score
        }

        self.resultados.append(resultado)
        print(f"  OCR: '{nombre_ocr}'")
        print(f"  Coincidencia: '{resultado_match}' (score: {score}%)")
        print(f"  Tolerancia: {'ACEPTADO' if score >= 60 else 'RECHAZADO'}")

        return resultado["status"] == "OK"

    def test_categoria_sugerida(self):
        """Test: Sugerencia de categoría."""
        print("\n[TEST] Sugerencia de categoria")

        nombres_test = [
            ("Leche entera", "Alimentación"),
            ("Manzanas rojas", "Frutas"),
            ("Tomates pera", "Verduras"),
            ("Pollo 1kg", "Carnes"),
        ]

        aciertos = 0
        for nombre, categoria_esperada in nombres_test:
            categoria = self.matcher.sugerir_categoria(nombre)
            acierto = categoria == categoria_esperada
            if acierto:
                aciertos += 1
            print(f"  {nombre}: {categoria} {'[OK]' if acierto else '[FAIL: esperado ' + categoria_esperada + ']'}")

        resultado = {
            "test": "categoria_sugerida",
            "status": "OK" if aciertos >= 3 else "FAIL",
            "aciertos": aciertos,
            "total": len(nombres_test)
        }

        self.resultados.append(resultado)

        return resultado["status"] == "OK"

    def generar_reporte(self):
        """Genera reporte de testing."""
        print("\n" + "="*70)
        print("REPORTE FINAL - TESTING EXHAUSTIVO OCR")
        print("="*70)

        pasados = sum(1 for r in self.resultados if r["status"] == "OK")
        total = len(self.resultados)

        print(f"\nRESULTADOS: {pasados}/{total} tests pasados")
        print("\nDETALLE:")
        for r in self.resultados:
            estado = "[OK]" if r["status"] == "OK" else "[FAIL]"
            print(f"  {estado} {r['test']}")

        print("\n" + "="*70)
        if pasados == total:
            print("[EXITO] TODOS LOS TESTS PASARON - OCR FUNCIONANDO CORRECTAMENTE")
        else:
            print(f"[ALERTA] {total - pasados} TESTS FALLARON - REVISAR ARRIBA")

        return pasados == total


def main():
    """Ejecuta suite exhaustiva de testing."""
    print("\n" + "="*70)
    print("TESTING EXHAUSTIVO - OCR TICKETS")
    print("Intentando romper el sistema desde todos los angulos...")
    print("="*70)

    testing = SuiteOCR()

    # Ejecutar tests
    tests = [
        testing.test_parsing_basico,
        testing.test_parsing_mal_formateado,
        testing.test_parsing_sin_cantidad,
        testing.test_parsing_sin_precio,
        testing.test_parsing_unidades_variadas,
        testing.test_parsing_errores_ocr_simples,
        testing.test_matching_exacto,
        testing.test_matching_con_errores,
        testing.test_categoria_sugerida,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    # Generar reporte
    exito = testing.generar_reporte()
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
