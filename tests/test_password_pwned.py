"""Tests de la comprobacion de contraseñas filtradas contra HIBP (S-20)."""
import unittest
from unittest.mock import MagicMock, patch

import requests

from stockhogar.servicios.password_pwned import es_password_filtrada


class PasswordPwnedTests(unittest.TestCase):
    @patch("stockhogar.servicios.password_pwned.requests.get")
    def test_password_filtrada_detecta_sufijo_presente(self, mock_get):
        # sha1("password123456") -> comprobamos el sufijo real de ese hash.
        import hashlib
        hash_completo = hashlib.sha1(b"password123456").hexdigest().upper()
        sufijo = hash_completo[5:]

        respuesta = MagicMock()
        respuesta.text = f"{sufijo}:12345\nOTROSUFIJOQUENOCOINCIDE:1"
        respuesta.raise_for_status = MagicMock()
        mock_get.return_value = respuesta

        self.assertTrue(es_password_filtrada("password123456"))

    @patch("stockhogar.servicios.password_pwned.requests.get")
    def test_password_no_filtrada_cuando_sufijo_no_aparece(self, mock_get):
        respuesta = MagicMock()
        respuesta.text = "SUFIJOQUENOCOINCIDE:1"
        respuesta.raise_for_status = MagicMock()
        mock_get.return_value = respuesta

        self.assertFalse(es_password_filtrada("unaContraseñaMuySegura987"))

    @patch("stockhogar.servicios.password_pwned.requests.get", side_effect=requests.ConnectionError)
    def test_fallo_de_red_no_bloquea(self, _mock_get):
        self.assertFalse(es_password_filtrada("cualquierPassword123"))

    @patch("stockhogar.servicios.password_pwned.requests.get", side_effect=requests.Timeout)
    def test_timeout_no_bloquea(self, _mock_get):
        self.assertFalse(es_password_filtrada("cualquierPassword123"))


if __name__ == "__main__":
    unittest.main()
