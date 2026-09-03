"""Ataduras entre ficheros de herramientas que ya se han desincronizado antes.

Dos acoplamientos reales, cada uno con su modo de fallo:

  1. El CMD de los Dockerfile usa `--no-control-socket`, un flag que gunicorn
     no reconoce antes de la 26.0.0. Si alguien relajara el minimo de
     requirements.txt por debajo de 26, el contenedor no arrancaria: gunicorn
     sale con "unrecognized arguments" antes de servir nada, y eso no lo ve
     ningun test de la app.

  2. Los scripts de npm apuntaban a jest.config.js, config muerta que apuntaba
     a su vez a stockhogar/static (borrado en la migracion a Next). `npm run
     test:watch` y `npm run test:coverage` estaban rotos sin que nadie se
     enterara, porque CI solo ejecuta `npx jest -c jest.config.lib.js`.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class GunicornYDockerfileTests(unittest.TestCase):
    DOCKERFILES = ("Dockerfile", "Dockerfile.raspbian")

    @classmethod
    def setUpClass(cls):
        cls.requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")

    def _minimo_de_gunicorn(self):
        for linea in self.requisitos.splitlines():
            limpia = linea.strip()
            if limpia.startswith("gunicorn"):
                encontrado = re.search(r">=\s*(\d+)", limpia)
                self.assertIsNotNone(encontrado, f"no se pudo leer el minimo en: {limpia}")
                return int(encontrado.group(1)), limpia
        self.fail("gunicorn no esta declarado en requirements.txt")

    def test_el_minimo_de_gunicorn_soporta_los_flags_del_cmd(self):
        minimo, linea = self._minimo_de_gunicorn()
        for fichero in self.DOCKERFILES:
            texto = (RAIZ / fichero).read_text(encoding="utf-8")
            if "--no-control-socket" not in texto:
                continue
            with self.subTest(fichero=fichero):
                self.assertGreaterEqual(
                    minimo, 26,
                    f"{fichero} usa --no-control-socket, que gunicorn no reconoce "
                    f"antes de la 26.0.0, pero requirements.txt permite instalar "
                    f"una anterior ({linea}): el contenedor no arrancaria",
                )

    def test_los_dos_dockerfile_arrancan_gunicorn_igual(self):
        """La imagen normal y la de la Raspberry deben compartir flags: si una
        se queda atras, el fallo solo aparece en uno de los dos despliegues."""
        comandos = {}
        for fichero in self.DOCKERFILES:
            texto = (RAIZ / fichero).read_text(encoding="utf-8")
            encontrado = re.search(r"^CMD \[.*gunicorn (.+?) --bind", texto, re.M)
            self.assertIsNotNone(encontrado, f"{fichero} no tiene un CMD de gunicorn reconocible")
            comandos[fichero] = sorted(encontrado.group(1).split())
        self.assertEqual(
            comandos["Dockerfile"], comandos["Dockerfile.raspbian"],
            "los flags de gunicorn difieren entre los dos Dockerfile",
        )


class ScriptsDeJestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paquete = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))

    def test_los_scripts_de_test_apuntan_a_una_config_que_existe(self):
        scripts = self.paquete["scripts"]
        de_test = {k: v for k, v in scripts.items() if v.split()[0] == "jest"}
        self.assertTrue(de_test, "ningun script de npm ejecuta jest")
        for nombre, comando in de_test.items():
            with self.subTest(script=nombre):
                encontrado = re.search(r"-c\s+(\S+)", comando)
                self.assertIsNotNone(
                    encontrado,
                    f"`npm run {nombre}` ejecuta jest sin -c, asi que buscaria "
                    f"jest.config.js, que ya no existe",
                )
                config = RAIZ / encontrado.group(1)
                self.assertTrue(config.exists(), f"{config.name} no existe")

    def test_no_vuelve_la_config_muerta(self):
        for muerto in ("jest.config.js", "jest.setup.js"):
            with self.subTest(fichero=muerto):
                self.assertFalse(
                    (RAIZ / muerto).exists(),
                    f"{muerto} apuntaba a stockhogar/static, que no existe desde "
                    f"la migracion a Next",
                )

    def test_no_se_declara_jsdom_si_nadie_lo_usa(self):
        """jest-environment-jsdom solo lo pedia la config borrada; el entorno
        de jest.config.lib.js es 'node'."""
        dev = self.paquete.get("devDependencies", {})
        config = (RAIZ / "jest.config.lib.js").read_text(encoding="utf-8")
        # Se busca el ajuste, no la palabra: el comentario de cabecera de esa
        # config explica precisamente por que YA NO se usa jsdom, y buscar el
        # substring hacia que este test se saltara solo.
        if re.search(r"testEnvironment:\s*['\"]jsdom['\"]", config):
            self.skipTest("la config volvio a usar jsdom, la dependencia hace falta")
        self.assertNotIn(
            "jest-environment-jsdom", dev,
            "ninguna config de jest usa jsdom, asi que la dependencia sobra",
        )

    def test_jest_y_sus_tipos_van_en_la_misma_major(self):
        dev = self.paquete["devDependencies"]
        major = lambda spec: re.search(r"(\d+)", spec).group(1)  # noqa: E731
        self.assertEqual(
            major(dev["jest"]), major(dev["@types/jest"]),
            "jest y @types/jest en majors distintas: los tipos dejan de "
            "corresponderse con la API real",
        )


if __name__ == "__main__":
    unittest.main()
