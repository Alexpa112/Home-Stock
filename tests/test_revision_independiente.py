"""Regresiones halladas en la revision independiente del escaner de tickets."""
import unittest

from stockhogar.integraciones import ocr_rapid
from stockhogar.servicios.ocr.cuadre_ticket import extraer_total_impreso
from stockhogar.servicios.ocr.diccionario import identificar_articulo
from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado

CAB = "MERCADONA S.A.\nC/ MAYOR 5\nCIF A46103834\n01/02/2024 12:30\n"
PIE = "\nTOTAL 20,00\nTARJETA 20,00"


def _parsear(cuerpo):
    return [(x.nombre, x.cantidad, x.precio_total) for x in ParserMejorado().parsear(CAB + cuerpo + PIE)]


class DiccionarioTests(unittest.TestCase):
    def test_leche_no_es_de_formula(self):
        self.assertNotEqual(identificar_articulo("LECHE").categoria, "Bebé")
        self.assertNotEqual(identificar_articulo("LECHE PASCUAL").categoria, "Bebé")
        self.assertEqual(identificar_articulo("LECHE FORMULA").categoria, "Bebé")

    def test_no_inventa_palabras(self):
        self.assertEqual(identificar_articulo("TURRON ALICANTE").nombre_limpio, "Turrón Alicante")
        self.assertEqual(identificar_articulo("ENSALADILLA MARINERA").nombre_limpio, "Ensaladilla Marinera")


class ParserTests(unittest.TestCase):
    def test_marca_de_iva_tras_el_precio(self):
        self.assertEqual([n.strip(" *") for n, *_ in _parsear("PAN 1,85 *\nLECHE 0,89\nAGUA 0,50")], ["Pan", "Leche", "Agua"])
        self.assertEqual(len(_parsear("PAN 1,85 10%\nLECHE 0,89 10%\nAGUA 0,50")), 3)

    def test_descuento_en_la_misma_linea(self):
        n, c, pt = _parsear("LECHE 0,89 Desc. -0,10\nPAN 1,00\nAGUA 0,50")[0]
        self.assertAlmostEqual(pt, 0.79)

    def test_primer_articulo_a_peso(self):
        self.assertEqual(_parsear("MANZANA\n1,088 kg x 14,50/kg\n15,78\nPAN 1,00\nAGUA 0,50")[0][:2], ("Manzana", 1.088))

    def test_cantidad_con_u(self):
        self.assertEqual(_parsear("PIMIENTOS 3 U 1,20\nPAN 1,00\nAGUA 2,00")[0][1], 3.0)

    def test_importes_enormes_no_rompen(self):
        self.assertIsInstance(_parsear("2 PAN " + "9" * 400 + ",99 " + "9" * 400 + ",99\nLECHE 1,00"), list)

    def test_linea_larga_de_digitos_es_rapida(self):
        import time
        t = time.time()
        _parsear("PAN " + "1" * 3000 + " 1,00\nLECHE 1,00")
        self.assertLess(time.time() - t, 5)


class TotalTests(unittest.TestCase):
    def test_miles_y_total_efectivo(self):
        self.assertEqual(extraer_total_impreso("TOTAL 1.234,56"), 1234.56)
        self.assertEqual(extraer_total_impreso("TOTAL 12,50\nTOTAL EFECTIVO 20,00"), 12.5)
        self.assertEqual(extraer_total_impreso("TOTAL A PAGAR 12,50"), 12.5)


class OcrRapidTests(unittest.TestCase):
    def test_multipack_no_se_toca(self):
        self.assertEqual(ocr_rapid._arreglar_confusiones("AGUA 6X1L"), "AGUA 6X1L")
        self.assertEqual(ocr_rapid._arreglar_confusiones("BR0C0LI"), "BROCOLI")

    def test_entorno_mal_escrito(self):
        import os
        os.environ["_T_OCR"] = "dos"
        try:
            self.assertEqual(ocr_rapid._entero_de_entorno("_T_OCR", 2), 2)
        finally:
            del os.environ["_T_OCR"]


if __name__ == "__main__":
    unittest.main()


class PendientesTests(unittest.TestCase):
    def test_pesadas_repetidas_se_suman(self):
        r = _parsear("PLATANO 0,850 kg 1,89 EUR/kg 1,61\nPLATANO 0,500 kg 1,89 EUR/kg 0,95\nPAN 1,00")
        platano = [x for x in r if x[0].lower().startswith("platano")][0]
        self.assertAlmostEqual(platano[1], 1.35)
        self.assertAlmostEqual(platano[2], 2.56)

    def test_peso_cero_es_una_unidad(self):
        self.assertEqual(_parsear("PAN 0,000 kg 1,50\nLECHE 1,00")[0][1], 1.0)

    def test_cuadre_no_borra_un_articulo_normal(self):
        from stockhogar.servicios.ocr.cuadre_ticket import cuadrar_con_total

        def it(n, t):
            return {"nombre": n, "cantidad": 1, "precio_total": t, "origen_nombre": "ticket"}
        items = [it("Cola", 8.5), it("Xyz Queso", 5.0), it("Pan", 2.0)]
        out, _ = cuadrar_con_total(items, "TOTAL 10,50")
        self.assertEqual(len(out), 3)

    def test_ticket_gigante_se_acota(self):
        import time
        t = time.time()
        _parsear("\n".join("ARTICULO%d 1,00" % i for i in range(3000)))
        self.assertLess(time.time() - t, 20)
