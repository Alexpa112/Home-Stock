"""Formatos de ticket de varias estructuras e idiomas (vistos en recibos reales).

Cubre: nombre en una linea y la fila numerica en otra (con o sin codigo), fila
numerica ANTES del nombre, descuentos que se restan del articulo anterior,
cabeceras y palabras de cierre de otros idiomas, importes pegados a la moneda
("RM1.25"), lineas repetidas que se funden y cabecera de columnas con "total".
"""
import unittest

from stockhogar.servicios.ocr.parser_mejorado import ParserMejorado, TipoUnidad


def _items(texto):
    return ParserMejorado().parsear(texto)


class NombreYFilaNumericaTests(unittest.TestCase):
    def test_nombre_codigo_y_fila_numerica(self):
        it = _items("MR D.I.Y. SDN BHD\n(CO.REG :933109-X)\n-INVOICE-\nCHOPPING BOARD 35.5x25.5CM\nEZ10HD05 - 24\n"
                    "8970669 1 X 19.00 19.00\nAIR PRESSURE SPRAYER 1.5L\nHC03-7 - 15\n9066468 1 X 8.02 8.02\n"
                    "Item(s) : 2 Qty(s) : 2\nTOTAL RM 27.02\n")
        self.assertEqual([(i.nombre.split()[0], i.precio_total) for i in it], [("Chopping", 19.0), ("Air", 8.02)])

    def test_la_fila_numerica_antes_del_nombre(self):
        it = _items("TIENDA\nItem Qty S/Price Amount Tax\n1072 1 80.00 80.00\nREPAIR ENGINE\n"
                    "70561 2 18.00 36.00\nSTARTER HANDLE\nTotal Sales : 116.00\n")
        self.assertEqual([(i.cantidad, i.precio_total) for i in it], [(1, 80.0), (2, 36.0)])

    def test_cantidad_con_x_pegada_al_precio_y_letra_de_impuesto(self):
        it = _items("BAR\nDescription Qty U.price Total TAX\nHEINEKEN (5 BTL)\n2x 95.00 190.00 SR\nTotal: 190.00\n")
        self.assertEqual((it[0].cantidad, it[0].precio_total), (2, 190.0))

    def test_moneda_pegada_al_importe(self):
        it = _items("99 SPEED MART\nINVOICE NO : 18287\n1973 GARBAGE BAG (BLUE) RM1.25 s\n1974 GARBAGE BAG (GREEN) RM1.50 s\nTotal Sales RM 2.75\n")
        self.assertEqual(sorted(i.precio_total for i in it), [1.25, 1.5])
        self.assertTrue(all(i.nombre.startswith("Garbage") for i in it))

    def test_cabecera_de_columnas_con_total_no_cierra_la_lista(self):
        it = _items("MCDONALDS\nTAX INVOICE\nQTY ITEM TOTAL\n2 ChicMcMuffin 11.00\n1 M Porridge 5.60\nTotal (incl GST) 16.60\n")
        self.assertEqual([i.precio_total for i in it], [11.0, 5.6])
        self.assertEqual(it[0].cantidad, 2)


class DescuentosTests(unittest.TestCase):
    TICKET = ("Lidl Supermercados S.A.U.\nCIF A-60195278\n12.10.2026 19:10\nLeche entera 1L 0,89 A\n"
              "Tomate pera 1,61 A\n0,850 kg x 1,89 EUR/kg\nDesc. -0,30\nYogur natural 2,20 A\n4 x 0,55\n"
              "PROMO LIDL PLUS -0,50\nAgua mineral 1,5L 2,52 A\n6 x 0,42\nTotal 6,42\n")

    def test_el_descuento_no_es_un_articulo_y_se_resta_del_anterior(self):
        it = {i.nombre: i for i in _items(self.TICKET)}
        self.assertEqual(sorted(it), ["Agua Mineral", "Leche Entera", "Tomate Pera", "Yogur Natural"])
        self.assertEqual(it["Tomate Pera"].precio_total, 1.31)
        self.assertEqual(it["Yogur Natural"].precio_total, 1.7)
        self.assertEqual(it["Yogur Natural"].descuento, 0.5)

    def test_la_cantidad_no_cambia_por_el_descuento(self):
        it = {i.nombre: i for i in _items(self.TICKET)}
        self.assertEqual((it["Yogur Natural"].cantidad, it["Tomate Pera"].cantidad), (4, 0.85))
        self.assertEqual(it["Tomate Pera"].unidad, TipoUnidad.KILOGRAMO)

    def test_la_suma_de_los_articulos_da_el_total(self):
        self.assertAlmostEqual(sum(i.precio_total for i in _items(self.TICKET)), 6.42, places=2)


class LineasDeCierreEnOtrosIdiomasTests(unittest.TestCase):
    def test_palabras_de_cierre_mal_leidas(self):
        it = _items("TIENDA\nCOLA 1,50\nPAN 0,90\nLECHE 1,10\nTotai 3,50\nSub Tal 3,50\nDiscount 0,00\nTOTQTY 3\n")
        self.assertEqual([i.nombre for i in it], ["Cola", "Pan", "Leche"])

    def test_arroz_redondo_no_es_redondeo(self):
        it = _items("TIENDA X\n12/10/2026\nARROZ REDONDO 1KG 1,35\nPAN 0,90\nLECHE 1,10\nTOTAL 3,35\n")
        self.assertIn("Arroz Redondo", [i.nombre for i in it])

    def test_palabras_de_cierre_en_otros_idiomas(self):
        for cierre in ("Cash 20.00", "Change 5.00", "Especes 20,00", "Troco 5,00", "Contanti 20,00", "Rueckgeld 5,00"):
            with self.subTest(cierre=cierre):
                it = _items(f"TIENDA\nCOLA 1,50\nPAN 0,90\nLECHE 1,10\n{cierre}\n")
                self.assertEqual(len(it), 3, [i.nombre for i in it])


class LineasRepetidasTests(unittest.TestCase):
    def test_la_misma_linea_dos_veces_suma_cantidades(self):
        it = _items("TIENDA X\n12/10/2026\nPAN 0,90\nLECHE 1,10\nPAN 0,90\nTOTAL 2,90\n")
        pan = next(i for i in it if i.nombre == "Pan")
        self.assertEqual((pan.cantidad, pan.precio_total), (2, 1.8))
        self.assertEqual(len(it), 2)


if __name__ == "__main__":
    unittest.main()


class FilaConDosPreciosUnitariosTests(unittest.TestCase):
    def test_precio_sin_y_con_impuesto(self):
        it = _items("FERRETERIA\nItem Qty S/Price S/Price Amount Tax\n11046 2 80.00 84.80 169.60 SR\nPASTA HALUSA\n"
                    "10012 2 3.00 3.18 6.36 SR\nBENANG NYLON\nTotal Sales 175.96\n")
        self.assertEqual([(i.cantidad, i.precio_total) for i in it], [(2, 169.6), (2, 6.36)])

    def test_cantidad_decimal_con_unidad_nos(self):
        it = _items("LIM SENG\nTAX INVOICE\nInvoice No CS24198\nBEGGUNI\n10.00 NOS X 0.70 7.0 0 SR\nSubtotal: 7.0 0\nTotal Incl.of GST 7.00")
        self.assertEqual((it[-1].cantidad, it[-1].precio_total), (10, 7.0))

    def test_estrella_como_multiplicador(self):
        it = _items("MYDIN\nRECEIPT\nPARTNER E/LOPE 4.5INX9.5IN W4292 EA .S\n3555023304662 2 * 2.60 5.20\n"
                    "PLASTIC BAG EA .S\n2300000017984 1 * 0.20 0.20\nTOTAL 5.40")
        self.assertEqual([(i.cantidad, i.precio_total) for i in it], [(2, 5.2), (1, 0.2)])


class OfertaNoEsDescuentoTests(unittest.TestCase):
    def test_un_articulo_cuyo_nombre_empieza_por_oferta_no_se_pierde(self):
        it = {i.nombre: i for i in _items("TIENDA X\n12/10/2026\nPAN 0,90\nOFERTA LECHE DESNATADA 1,20\nCOLA 1,50\nTOTAL 3,60\n")}
        self.assertIn("Oferta Leche Desnatada", it)
        self.assertEqual(it["Pan"].precio_total, 0.9)           # el "descuento" no le resto nada

    def test_dto_sin_signo_y_sin_nombre_si_es_descuento(self):
        it = _items("TIENDA X\n12/10/2026\nPAN 2,00\nDTO. 0,50\nCOLA 1,50\nTOTAL 3,00\n")
        self.assertEqual([(i.nombre, i.precio_total) for i in it], [("Pan", 1.5), ("Cola", 1.5)])


class DetalleConDosImportesTests(unittest.TestCase):
    def test_x_con_unitario_y_total_tras_el_articulo_es_su_detalle(self):
        it = _items("Lidl Supermercados S.A.U.\nCIF A-60195278\n12.10.2026 19:10\nPan de molde 3,70 A\n2 x 1,85 3,70\n"
                    "Yogur 2,20 A\n4 x 0,55 2,20\nTotal 5,90\n")
        self.assertEqual([(i.nombre, i.cantidad, i.precio_total) for i in it], [("Pan De Molde", 2, 3.7), ("Yogur", 4, 2.2)])

    def test_el_detalle_no_se_pega_al_siguiente_articulo_sin_importe(self):
        it = _items("TIENDA X\n12/10/2026\nPAN 3,70\n2 x 1,85 3,70\nBEBIDA SOJA\nCOLA 1,50\nLECHE 1,10\nTOTAL 6,30\n")
        soja = next(i for i in it if i.nombre.startswith("Bebida"))
        self.assertEqual((soja.cantidad, soja.precio_total), (1, 0))


class ArticulosDelCatalogoNoSePierdenTests(unittest.TestCase):
    """Ningun articulo real del catalogo debe confundirse con una linea de control."""

    def test_todos_los_articulos_del_catalogo_sobreviven_al_parser(self):
        from stockhogar.servicios.ocr.diccionario import obtener
        perdidos = []
        for e in obtener().entradas:
            t = f"TIENDA X\n12/10/2026\nPAN 0,90\n{e.nombre.upper()} 1,20\nCOLA 1,50\nTOTAL 3,60\n"
            nombres = [i.nombre for i in _items(t)]
            if len(nombres) != 3:
                perdidos.append((e.nombre, nombres))
        self.assertEqual(perdidos, [])

    def test_palabras_que_parecen_de_cierre(self):
        for nombre in ("TARTA DE QUESO", "ESPECIAS", "RECAMBIO FREGONA", "SALES DE BAÑO", "SANDWICH CLUB", "PINZAS DE TENDER", "TE"):
            with self.subTest(nombre=nombre):
                it = _items(f"TIENDA X\n12/10/2026\nPAN 0,90\n{nombre} 1,20\nCOLA 1,50\nTOTAL 3,60\n")
                self.assertEqual(len(it), 3, [i.nombre for i in it])
