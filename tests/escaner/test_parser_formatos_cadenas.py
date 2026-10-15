"""Formatos de ticket de varias cadenas, como los entrega el OCR (texto plano).

Cada caso fija un formato real que antes se leia mal: la cantidad marcada con
UN/UD (Alcampo, Eroski), el peso en su propio renglon con precio por kilo (Aldi),
el importe en el renglon siguiente, la columna de peso sin unidad (Consum), el
codigo de articulo delante del nombre y "2x1,50" sin espacios.
"""
import unittest

from stockhogar.servicios.ocr.parser import ParserMejorado, TipoUnidad


def _items(texto):
    return {l.nombre: l for l in ParserMejorado().parsear(texto)}


class FormatosDeCadenasTests(unittest.TestCase):
    def test_cantidad_marcada_con_un(self):
        it = _items("ALCAMPO S.A.\nFECHA: 12/10/2026 HORA: 12:40\nDETERGENTE LIQ 2 UN 11,98\nPALMERITAS 3 UDS 3,60\nTOTAL 15,58")
        self.assertEqual(it["Detergente Liq"].cantidad, 2)
        self.assertEqual(it["Palmeritas"].cantidad, 3)
        self.assertEqual(it["Detergente Liq"].precio_total, 11.98)

    def test_peso_en_renglon_aparte_con_precio_por_kilo(self):
        it = _items("ALDI SUPERMERCADOS S.L.\n12.10.2026 09:58\nFILETE PESCADILLA 15,78 B\n1,088 kg x 14,50/kg\nTOTAL 15,78")
        pesc = it["Filete Pescadilla"]
        self.assertAlmostEqual(pesc.cantidad, 1.088)
        self.assertEqual(pesc.unidad, TipoUnidad.KILOGRAMO)
        self.assertEqual(pesc.precio_unitario, 14.5)

    def test_importe_en_el_renglon_siguiente(self):
        it = _items("ALCAMPO S.A.\nFECHA: 12/10/2026 HORA: 12:40\nFILETE PESCADILLA 1,088 KG\n15,78\nTOTAL 15,78")
        self.assertEqual(it["Filete Pescadilla"].precio_total, 15.78)
        self.assertAlmostEqual(it["Filete Pescadilla"].cantidad, 1.088)

    def test_columna_de_peso_sin_unidad_son_kilos(self):
        it = _items("CONSUM S. COOP. V.\n12-10-2026 10:12\nCANT DESCRIPCION IMPORTE\n1,577 MORTADELA ACEITUNAS 8,20\n    2 YOGUR GRIEGO 1,80\nTOTAL A PAGAR 10,00")
        self.assertAlmostEqual(it["Mortadela Aceitunas"].cantidad, 1.577)
        self.assertEqual(it["Mortadela Aceitunas"].unidad, TipoUnidad.KILOGRAMO)
        self.assertEqual(it["Yogur Griego"].cantidad, 2)
        self.assertEqual(it["Yogur Griego"].unidad, TipoUnidad.UNIDAD)

    def test_codigo_de_articulo_no_es_parte_del_nombre(self):
        it = _items("EROSKI\n12/10/26 20:15\n400137 MEJILLON ESCABECHE 2x1,50 3,00\n400274 YOGUR GRIEGO 1,20\nTOTAL 4,20")
        self.assertIn("Mejillon Escabeche", it)
        self.assertEqual(it["Mejillon Escabeche"].cantidad, 2)
        self.assertEqual(it["Mejillon Escabeche"].precio_unitario, 1.5)
        self.assertIn("Yogur Griego", it)

    def test_un_numero_de_tres_decimales_seguido_de_precio_no_cambia_las_unidades(self):
        # Una cantidad "2 UN" y un tamano "1L" conviven: manda la cantidad.
        it = _items("ALCAMPO S.A.\nFECHA: 12/10/2026 HORA: 12:40\nLECHE ENTERA 1L 6 UN 5,40\nTOTAL 5,40")
        self.assertEqual(next(iter(it.values())).cantidad, 6)

    def test_suma_cierra_la_lista_de_articulos(self):
        it = _items("ALDI SUPERMERCADOS S.L.\n12.10.2026 09:58\nPALMERITAS 2,40 B\n2 x 1,20\nSUMA 2,40\nTARJETA")
        self.assertNotIn("Suma", it)
        self.assertEqual(it["Palmeritas"].cantidad, 2)


class CuadreAritmeticoDeLineaTests(unittest.TestCase):
    """cantidad x unitario = total: si el OCR leyo mal un digito, el cociente lo delata."""

    CAB = "TIENDA X\n12/10/2026 10:00\n"

    def test_cantidad_mal_leida_se_corrige_con_el_cociente(self):
        it = _items(self.CAB + "CEPILLO DIENTES 1 4,44 17,76\nTOTAL 17,76")
        self.assertEqual(it["Cepillo Dientes"].cantidad, 4)
        self.assertEqual(it["Cepillo Dientes"].precio_unitario, 4.44)

    def test_cantidad_pegada_a_basura_se_deduce_del_importe(self):
        it = _items(self.CAB + "MANTEQUILLA CON SAL 25064 x 3,15 12,60\nTOTAL 12,60")
        self.assertEqual(it["Mantequilla Con Sal"].cantidad, 4)

    def test_sin_cantidad_impresa_pero_con_unitario_y_total(self):
        it = _items(self.CAB + "PIENSO GATOS ESTERIL a 3,47 13,88\nTOTAL 13,88")
        self.assertEqual(it["Pienso Gatos Esteril"].cantidad, 4)

    def test_si_cuadra_no_se_toca(self):
        it = _items(self.CAB + "PAN 2 1,85 3,70\nLECHE 1 1,20 1,20\nTOTAL 4,90")
        self.assertEqual((it["Pan"].cantidad, it["Leche"].cantidad), (2, 1))

    def test_un_peso_no_se_cuadra_como_unidades(self):
        it = _items(self.CAB + "TOMATE 0,850 kg 1,89 1,61\nTOTAL 1,61")
        self.assertAlmostEqual(it["Tomate"].cantidad, 0.85)
        self.assertEqual(it["Tomate"].unidad, TipoUnidad.KILOGRAMO)

    def test_peso_con_la_coma_separada(self):
        it = _items(self.CAB + "CALABAZA TROZO 0, 885kg 4,31\nTOTAL 4,31")
        self.assertAlmostEqual(next(iter(it.values())).cantidad, 0.885)

    def test_peso_explicito_manda_sobre_un_3u_del_nombre(self):
        it = _items(self.CAB + "ATUN CLARO ACEITE OLIVA 3U 1,310 KG\nTOTAL 9,00")
        self.assertAlmostEqual(next(iter(it.values())).cantidad, 1.31)

    def test_multiplicador_con_el_unitario_ilegible(self):
        it = _items(self.CAB + "QUESO EDAM LONCHAS 4x 5,9% 23,76\nGEL BAÑO 4x2, 48 8,72\nTOTAL 32,48")
        self.assertEqual(it["Queso Edam Lonchas"].cantidad, 4)
        self.assertEqual(it["Gel Baño"].cantidad, 4)

    def test_la_promocion_2x1_no_es_multiplicador(self):
        it = _items(self.CAB + "PROMO GALLETAS 2x1 1,20\nTOTAL 1,20")
        self.assertEqual(next(iter(it.values())).cantidad, 1)


class ArticulosConPalabrasDeControlTests(unittest.TestCase):
    CAB = "TIENDA X\n12/10/2026 10:00\n"

    def test_caja_en_el_nombre_es_un_articulo(self):
        it = _items(self.CAB + "3 HUEVOS XL CAJA 6   6,30\nPAN 1,00\nTOTAL 7,30")
        self.assertEqual(len(it), 2)

    def test_el_puesto_de_cobro_no_es_un_articulo(self):
        it = _items(self.CAB + "CAJA 03 OP 12\nPAN 1,00\nTOTAL 1,00")
        self.assertEqual(list(it), ["Pan"])


if __name__ == "__main__":
    unittest.main()
