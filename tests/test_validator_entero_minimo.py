"""Test de regresion: Validator.entero_minimo() sin tope superior.

Antes, un cliente podia mandar una cantidad absurdamente grande (p.ej.
999999999999) sin ningun limite. Ahora se acota tambien por arriba.
"""
import unittest

from stockhogar.utils import Validator
from stockhogar.utils.validation import ValidationError


class EnteroMinimoTests(unittest.TestCase):
    def test_valor_normal_se_conserva(self):
        self.assertEqual(Validator.entero_minimo(5, "cantidad"), 5)

    def test_valor_por_debajo_del_minimo_se_sube_al_minimo(self):
        self.assertEqual(Validator.entero_minimo(-3, "cantidad", minimo=1), 1)

    def test_valor_absurdamente_grande_se_acota_al_maximo(self):
        self.assertEqual(Validator.entero_minimo(999999999999, "cantidad"), 100_000)

    def test_valor_justo_en_el_maximo_se_conserva(self):
        self.assertEqual(Validator.entero_minimo(100_000, "cantidad"), 100_000)

    def test_maximo_personalizado_se_respeta(self):
        self.assertEqual(Validator.entero_minimo(500, "cantidad", maximo=100), 100)

    def test_no_numerico_sigue_lanzando_error(self):
        with self.assertRaises(ValidationError):
            Validator.entero_minimo("no-es-un-numero", "cantidad")


if __name__ == "__main__":
    unittest.main()
