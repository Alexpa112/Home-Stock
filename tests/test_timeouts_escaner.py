"""Test de regresion: la cadena de timeouts del escaneo de tickets tiene que
estar ordenada de dentro afuera.

    llamada a la API  <  worker de gunicorn  <  abort del frontend

Si el worker se queda por debajo de la llamada a la API, gunicorn mata el
proceso a mitad del analisis y el usuario recibe un error generico en vez del
resultado. Si el abort del navegador se queda por debajo del worker, el usuario
ve "ha tardado demasiado" aunque el servidor fuera a responder correctamente.

Los tres valores viven en ficheros distintos (Python, Dockerfile y TypeScript),
asi que es facil tocar uno y olvidar los otros dos: este test lo impide.
"""
import re
import unittest
from pathlib import Path

from stockhogar.servicios.ocr import claude_ocr

RAIZ = Path(__file__).resolve().parent.parent

# Margen minimo entre escalones, para que quepan la subida de la foto, el
# troceado de la imagen y el emparejado contra el catalogo.
MARGEN_MINIMO_SEGUNDOS = 20


def _timeout_gunicorn(nombre_dockerfile):
    contenido = (RAIZ / nombre_dockerfile).read_text(encoding="utf-8")
    cmd = [l for l in contenido.splitlines() if "gunicorn" in l and l.lstrip().startswith("CMD")]
    assert len(cmd) == 1, f"{nombre_dockerfile}: se esperaba un unico CMD con gunicorn"
    encontrado = re.search(r"--timeout\s+(\d+)", cmd[0])
    assert encontrado, f"{nombre_dockerfile}: el CMD de gunicorn no fija --timeout"
    return int(encontrado.group(1))


def _timeout_frontend_escaner():
    contenido = (RAIZ / "lib" / "api.ts").read_text(encoding="utf-8")
    encontrado = re.search(
        r"apiUpload\(\s*'/api/tickets/analizar'\s*,\s*formData\s*,\s*([\d_]+)\s*\)",
        contenido,
    )
    assert encontrado, "lib/api.ts: la llamada del escaner no fija un timeout explicito"
    return int(encontrado.group(1).replace("_", "")) / 1000


class TimeoutsEscanerTests(unittest.TestCase):
    def test_los_dos_dockerfiles_usan_el_mismo_timeout(self):
        self.assertEqual(
            _timeout_gunicorn("Dockerfile"),
            _timeout_gunicorn("Dockerfile.raspbian"),
            "Los despliegues normal y de Raspberry Pi deben coincidir",
        )

    def test_el_worker_aguanta_mas_que_la_llamada_a_la_api(self):
        api = claude_ocr._TIMEOUT_SEGUNDOS
        worker = _timeout_gunicorn("Dockerfile")
        self.assertGreaterEqual(
            worker, api + MARGEN_MINIMO_SEGUNDOS,
            f"gunicorn ({worker}s) debe superar a la llamada a la API ({api}s) "
            f"con al menos {MARGEN_MINIMO_SEGUNDOS}s de margen",
        )

    def test_el_navegador_espera_mas_que_el_worker(self):
        worker = _timeout_gunicorn("Dockerfile")
        frontend = _timeout_frontend_escaner()
        self.assertGreater(
            frontend, worker,
            f"El abort del frontend ({frontend}s) debe superar al worker ({worker}s) "
            "para que el usuario reciba el error real del servidor",
        )

    def test_el_esfuerzo_del_modelo_es_uno_de_los_admitidos(self):
        self.assertIn(claude_ocr._ESFUERZO, ("low", "medium", "high", "xhigh", "max"))


if __name__ == "__main__":
    unittest.main()
