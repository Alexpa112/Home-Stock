"""Tests del diagnostico de arranque del escaner de tickets.

Una instalacion sin el paquete `anthropic` o sin ANTHROPIC_API_KEY se comporta
como si funcionase: el escaner cae a Tesseract en silencio y reconoce mucho
peor. Antes eso solo se sabia escaneando un ticket, y el aviso se perdia entre
el resto del log. Estos tests fijan que el estado del motor quede registrado al
arrancar, con el nivel correcto, para poder comprobarlo de un vistazo despues de
reinstalar.

Tambien se comprueba que el paquete este declarado en requirements.txt y que los
dos Dockerfile rompan el build si falta: es la red que evita volver a publicar
una imagen donde el escaner esta degradado sin que nadie se entere.
"""
import logging
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from stockhogar import _registrar_estado_escaner

RAIZ = Path(__file__).resolve().parent.parent


class DiagnosticoArranqueTests(unittest.TestCase):
    def _capturar(self, con_paquete=True, con_clave=True):
        entorno = dict(os.environ)
        entorno.pop("ANTHROPIC_API_KEY", None)
        if con_clave:
            entorno["ANTHROPIC_API_KEY"] = "clave_falsa"

        modulos = {} if con_paquete else {"anthropic": None}
        with patch.dict(os.environ, entorno, clear=True):
            with patch.dict(sys.modules, modulos):
                with self.assertLogs("stockhogar", level="INFO") as capturado:
                    _registrar_estado_escaner()
        return capturado.records

    def test_con_paquete_y_clave_informa_de_que_el_motor_esta_listo(self):
        registros = self._capturar(con_paquete=True, con_clave=True)
        propios = [r for r in registros if r.name == "stockhogar"]
        self.assertEqual(len(propios), 1)
        self.assertEqual(propios[0].levelno, logging.INFO)
        self.assertIn("Claude Vision", propios[0].getMessage())

    def test_sin_clave_avisa_y_nombra_el_fichero_donde_ponerla(self):
        registros = self._capturar(con_paquete=True, con_clave=False)
        propios = [r for r in registros if r.name == "stockhogar"]
        self.assertEqual(propios[0].levelno, logging.WARNING)
        mensaje = propios[0].getMessage()
        self.assertIn("ANTHROPIC_API_KEY", mensaje)
        self.assertIn(".env", mensaje)

    def test_sin_paquete_avisa_y_da_el_comando_para_instalarlo(self):
        registros = self._capturar(con_paquete=False, con_clave=True)
        propios = [r for r in registros if r.name == "stockhogar"]
        self.assertEqual(propios[0].levelno, logging.WARNING)
        mensaje = propios[0].getMessage()
        self.assertIn("anthropic", mensaje)
        self.assertIn("pip install", mensaje)


class DependenciaDeclaradaTests(unittest.TestCase):
    def test_anthropic_esta_en_requirements(self):
        requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        lineas = [
            l.strip() for l in requisitos.splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        self.assertTrue(
            any(l.split("=")[0].split(">")[0].split("<")[0].strip() == "anthropic" for l in lineas),
            "sin esta linea la imagen se construye sin el motor principal del escaner",
        )

    def test_los_dockerfile_rompen_el_build_si_falta_anthropic(self):
        for nombre in ("Dockerfile", "Dockerfile.raspbian"):
            contenido = (RAIZ / nombre).read_text(encoding="utf-8")
            self.assertIn(
                "import anthropic", contenido,
                f"{nombre} debe verificar el paquete en build-time: si falta, el "
                "escaner cae a Tesseract en silencio en vez de fallar",
            )


if __name__ == "__main__":
    unittest.main()
