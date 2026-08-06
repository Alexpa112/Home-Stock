"""Test de regresion: Validator.con_defecto().

Antes, varias rutas leian los campos opcionales con datos.get(clave, defecto),
que solo aplica el defecto si la clave esta AUSENTE del JSON. Si el input se
dejaba en blanco en el frontend y este mandaba la clave con valor null (o
''), el defecto no se aplicaba y la peticion fallaba (int(None) sin capturar)
en vez de grabar el valor por defecto esperado.
"""
import unittest

from stockhogar.utils import Validator


class ConDefectoTests(unittest.TestCase):
    def test_clave_ausente_usa_defecto(self):
        self.assertEqual(Validator.con_defecto({}, "dias_aviso", 30), 30)

    def test_clave_presente_con_none_usa_defecto(self):
        self.assertEqual(Validator.con_defecto({"dias_aviso": None}, "dias_aviso", 30), 30)

    def test_clave_presente_con_string_vacio_usa_defecto(self):
        self.assertEqual(Validator.con_defecto({"cantidad": ""}, "cantidad", 1), 1)

    def test_valor_cero_valido_no_se_pisa(self):
        """0 es un valor legitimo (p.ej. cantidad en stock agotado) y no debe
        confundirse con 'campo vacio'."""
        self.assertEqual(Validator.con_defecto({"cantidad": 0}, "cantidad", 5), 0)

    def test_valor_informado_se_conserva(self):
        self.assertEqual(Validator.con_defecto({"dias_aviso": 15}, "dias_aviso", 30), 15)


if __name__ == "__main__":
    unittest.main()
