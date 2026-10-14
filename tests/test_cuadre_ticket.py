"""Cuadre de un ticket leido con OCR local contra el TOTAL impreso."""
import unittest

from stockhogar.servicios.ocr.cuadre_ticket import cuadrar_con_total, extraer_total_impreso


def _item(nombre, cantidad, unitario, total, unidad="ud"):
    return {"nombre": nombre, "cantidad": cantidad, "unidad": unidad, "precio_unitario": unitario,
            "precio_total": total, "cantidad_texto": f"{cantidad:g} {unidad}"}


class TotalImpresoTests(unittest.TestCase):
    def test_lee_el_total(self):
        self.assertEqual(extraer_total_impreso("PAN 1,00\nTOTAL 34,56\nTARJETA"), 34.56)
        self.assertEqual(extraer_total_impreso("TOTAL A PAGAR  1.234,50 EUR".replace("1.234,50", "234,50")), 234.5)

    def test_no_confunde_subtotal_ni_ahorro(self):
        self.assertEqual(extraer_total_impreso("SUBTOTAL 40,00\nAHORRO TOTAL 3,00\nTOTAL 37,00"), 37.0)

    def test_sin_total_es_none(self):
        self.assertIsNone(extraer_total_impreso("PAN 1,00\nLECHE 1,20"))

    def test_se_queda_con_el_mayor_si_hay_varios(self):
        self.assertEqual(extraer_total_impreso("TOTAL 5,00\nTOTAL (EUR) 12,30"), 12.3)


class CuadreTests(unittest.TestCase):
    def test_cuadra_sin_tocar_nada(self):
        items = [_item("Pan", 2, 1.85, 3.70), _item("Leche", 1, 1.20, 1.20)]
        out, cuadre = cuadrar_con_total(items, "TOTAL 4,90")
        self.assertTrue(cuadre["cuadra"])
        self.assertNotIn("corregido_por_total", out[0])

    def test_sin_total_no_hay_cuadre(self):
        self.assertEqual(cuadrar_con_total([_item("Pan", 1, 1.0, 1.0)], "PAN 1,00")[1], None)

    def test_corrige_la_cantidad_si_solo_una_cuadra(self):
        # El OCR leyo "1" donde decia "4": 4 x 4,44 = 17,76 y el total lo confirma.
        items = [_item("Cepillo", 1, 4.44, 4.44), _item("Leche", 1, 1.20, 1.20), _item("Pan", 2, 0.85, 1.70)]
        out, cuadre = cuadrar_con_total(items, "TOTAL 20,66")
        self.assertEqual(out[0]["cantidad"], 4.0)
        self.assertEqual(out[0]["precio_total"], 17.76)
        self.assertEqual(out[0]["corregido_por_total"], "cantidad")
        self.assertTrue(cuadre["cuadra"])

    def test_no_adivina_si_hay_mas_de_una_solucion(self):
        items = [_item("A", 1, 2.00, 2.00), _item("B", 1, 2.00, 2.00)]
        out, cuadre = cuadrar_con_total(items, "TOTAL 6,00")
        self.assertEqual([i["cantidad"] for i in out], [1, 1])
        self.assertFalse(cuadre["cuadra"])

    def test_rellena_la_unica_linea_sin_importe(self):
        items = [_item("Pan", 1, 0, 1.00), _item("Fruta", 1, 0, None)]
        out, cuadre = cuadrar_con_total(items, "TOTAL 3,50")
        self.assertEqual(out[1]["precio_total"], 2.5)
        self.assertEqual(out[1]["corregido_por_total"], "importe")
        self.assertTrue(cuadre["cuadra"])

    def test_descuadre_que_no_se_puede_corregir_se_avisa(self):
        items = [_item("Pan", 1, 1.0, 1.0)]
        _, cuadre = cuadrar_con_total(items, "TOTAL 9,00")
        self.assertTrue(cuadre["comprobado"])
        self.assertFalse(cuadre["cuadra"])
        self.assertEqual(items[0]["cantidad"], 1)  # con un solo articulo no se adivina nada

    def test_un_peso_no_se_corrige_como_unidades(self):
        items = [_item("Tomate", 0.85, 1.89, 1.61, unidad="kg"), _item("Pan", 1, 1.0, 1.0)]
        out, _ = cuadrar_con_total(items, "TOTAL 9,00")
        self.assertEqual(out[0]["cantidad"], 0.85)


if __name__ == "__main__":
    unittest.main()
