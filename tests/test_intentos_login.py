"""Test de regresion (S-01): el bloqueo de login debe distinguir cubo por IP
y cubo por IP+cuenta, persistido en SQLite (no en memoria del proceso).

5 fallos desde una IP contra la cuenta "x" deben bloquear "x" pero no "y"
tras limpiar_exito; 5 fallos desde una IP contra 5 cuentas distintas deben
bloquear esa IP entera (protege contra fuerza bruta de credential stuffing).
"""
import unittest

from stockhogar import create_app
from stockhogar.db import get_db
from stockhogar.servicios import intentos_login


class IntentosLoginTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.ctx = self.app.app_context()
        self.ctx.push()
        get_db().execute("DELETE FROM intentos_login")
        get_db().commit()

    def tearDown(self):
        get_db().execute("DELETE FROM intentos_login")
        get_db().commit()
        self.ctx.pop()

    def test_bloqueo_por_cuenta_no_afecta_a_otra_cuenta_misma_ip(self):
        ip = "1.2.3.4"
        for _ in range(5):
            intentos_login.registrar_fallo(ip, "x")

        self.assertTrue(intentos_login.bloqueada(ip, "x"))

        intentos_login.limpiar_exito(ip, "x")
        self.assertFalse(intentos_login.bloqueada(ip, "x"))
        # "y" nunca tuvo fallos propios, pero comparte IP: si la IP no llego
        # a su propio umbral (5 fallos totales, todos sobre "x", ya
        # limpiados), "y" no deberia estar bloqueada.
        self.assertFalse(intentos_login.bloqueada(ip, "y"))

    def test_bloqueo_por_ip_con_varias_cuentas_distintas(self):
        ip = "9.9.9.9"
        for i in range(5):
            intentos_login.registrar_fallo(ip, f"cuenta_{i}")

        # La IP acumulo 5 fallos (uno por cuenta distinta): debe bloquearse
        # entera, incluso para una cuenta nueva que no ha fallado nunca.
        self.assertTrue(intentos_login.bloqueada(ip, "cuenta_nunca_probada"))


if __name__ == "__main__":
    unittest.main()
