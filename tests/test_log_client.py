"""Test (S-14): /api/log/client debe truncar mensaje/contexto y sanear saltos
de linea (para no permitir fabricar entradas de log falsas), y limitar la
tasa de peticiones por IP.
"""
import logging
import unittest

from stockhogar import create_app, red


class LogClientTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        red._contadores.clear()

    def test_saltos_de_linea_saneados_y_mensaje_truncado(self):
        mensaje_malicioso = "hola\n2026-01-01 ERROR [otro] entrada falsa" + ("x" * 600)
        with self.assertLogs("stockhogar.rutas.paginas", level="INFO") as logs:
            resp = self.client.post(
                "/api/log/client",
                json={"nivel": "info", "mensaje": mensaje_malicioso, "contexto": {}},
            )
        self.assertEqual(resp.status_code, 200)
        linea = logs.output[0]
        self.assertNotIn("\n", linea.split("[CLIENT]", 1)[1])
        # 500 caracteres de mensaje + prefijo "[CLIENT] " -> la linea logueada
        # no debe contener el texto completo de 600+ caracteres.
        self.assertLess(len(linea), len(mensaje_malicioso))

    def test_rate_limit_devuelve_429(self):
        for _ in range(30):
            resp = self.client.post("/api/log/client", json={"mensaje": "ok"})
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post("/api/log/client", json={"mensaje": "de mas"})
        self.assertEqual(resp.status_code, 429, resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
