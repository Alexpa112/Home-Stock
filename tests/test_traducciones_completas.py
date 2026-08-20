"""Regresion: toda clave de error que use el backend debe tener traduccion.

`traducir()` devuelve la propia clave cuando no la encuentra, asi que una clave
sin entrada en translations.json no rompe nada visible en los tests pero el
usuario recibe literalmente "err_email_invalido" como mensaje de error. Habia 9
claves asi (entre ellas err_email_invalido, err_demasiados_intentos_2fa y
err_usuario_no_es_miembro).

Tambien se comprueba que los 7 idiomas tengan exactamente el mismo juego de
claves: si se añade una sola en español, el resto de idiomas la mostrarian
cruda.
"""
import json
import pathlib
import re
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TRADUCCIONES = RAIZ / "stockhogar" / "translations.json"

# Prefijos de clave que el backend resuelve con traducir() al construir la
# respuesta de error (APIResponse.error / no_encontrado).
PATRON_CLAVES = re.compile(r'["\'](err_[a-z0-9_]+|push_[a-z0-9_]+|recurso_[a-z0-9_]+)["\']')


class TraduccionesCompletasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traducciones = json.loads(TRADUCCIONES.read_text(encoding="utf-8"))
        cls.idiomas = list(cls.traducciones)

    def test_todos_los_idiomas_tienen_las_mismas_claves(self):
        claves_es = set(self.traducciones["es"])
        for idioma in self.idiomas:
            with self.subTest(idioma=idioma):
                faltan = claves_es - set(self.traducciones[idioma])
                self.assertEqual(
                    faltan, set(),
                    f"{idioma} no tiene {len(faltan)} claves que si estan en es: "
                    f"se mostrarian crudas al usuario. Faltan: {sorted(faltan)[:10]}",
                )

    def test_ninguna_clave_usada_en_el_backend_queda_sin_traducir(self):
        codigo = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (RAIZ / "stockhogar").rglob("*.py")
        )
        usadas = set(PATRON_CLAVES.findall(codigo))
        claves_es = set(self.traducciones["es"])

        sin_traducir = sorted(k for k in usadas if k not in claves_es)
        self.assertEqual(
            sin_traducir, [],
            "estas claves se usan en el backend pero no estan en translations.json, "
            f"asi que el usuario veria la clave en vez del mensaje: {sin_traducir}",
        )

    def test_el_fichero_es_json_valido_y_no_esta_vacio(self):
        self.assertGreater(len(self.traducciones["es"]), 100)
        self.assertIn("es", self.traducciones)


if __name__ == "__main__":
    unittest.main()
