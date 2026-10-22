"""Escalera de timeouts del escaneo de tickets (API < gunicorn < proxy de Next < abort del cliente).

Regresion: el proxy de rewrites de Next corta a los 30 s por defecto, y subir
una foto grande (3,4 MB, ~33 s) devolvia un 500 "Internal Server Error" en
texto plano aunque el backend siguiera trabajando (reproducido en el servidor
real el 2026-10-22). Cada escalon debe dejar margen sobre el de dentro.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent


def _numero(patron, texto):
    m = re.search(patron, texto)
    assert m, patron
    return int(m.group(1).replace("_", ""))


class EscaleraDeTimeoutsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _numero(r"_TIMEOUT_SEGUNDOS = (\d+)", (RAIZ / "stockhogar/servicios/ocr/claude_ocr.py").read_text(encoding="utf-8"))
        cls.proxy = _numero(r"proxyTimeout:\s*([\d_]+)", (RAIZ / "next.config.mjs").read_text(encoding="utf-8")) / 1000
        api_ts = (RAIZ / "lib" / "api.ts").read_text(encoding="utf-8")
        cls.abort = _numero(r"apiUpload\('/api/tickets/analizar', formData, ([\d_]+)\)", api_ts) / 1000
        cls.gunicorn = {
            f: _numero(r"--timeout (\d+)", (RAIZ / f).read_text(encoding="utf-8"))
            for f in ("Dockerfile", "Dockerfile.raspbian")
        }

    def test_el_proxy_de_next_no_corta_antes_que_gunicorn(self):
        for fichero, g in self.gunicorn.items():
            self.assertGreater(self.proxy, g, f"proxyTimeout debe superar el --timeout de {fichero}")

    def test_el_proxy_no_supera_el_abort_del_cliente(self):
        self.assertLess(self.proxy, self.abort)

    def test_gunicorn_deja_margen_sobre_la_llamada_a_la_api(self):
        for fichero, g in self.gunicorn.items():
            self.assertGreater(g, self.api + 30, fichero)

    def test_el_proxy_supera_con_holgura_el_valor_por_defecto_de_30s(self):
        self.assertGreaterEqual(self.proxy, 120)


if __name__ == "__main__":
    unittest.main()
