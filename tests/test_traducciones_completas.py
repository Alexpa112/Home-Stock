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

# Mismos prefijos mas los de permiso_*, que solo se lanzan desde el frontend
# (permisos del navegador, no del backend).
PATRON_CLAVES_FRONTEND = re.compile(
    r'["\'](err_[a-z0-9_]+|push_[a-z0-9_]+|permiso_[a-z0-9_]+)["\']'
)


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

    def test_ninguna_clave_lanzada_en_el_frontend_queda_sin_traducir(self):
        """El frontend tambien lanza claves propias (p.ej. usePushNotifications
        con `new Error('err_push_no_disponible')`) y las pinta con t(), que
        devuelve la clave si no la encuentra. Sin esta comprobacion, una clave
        que solo existe en TypeScript no la vigila nadie."""
        codigo = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for carpeta in ("lib", "app", "components", "contexts")
            for p in (RAIZ / carpeta).rglob("*.ts*")
            if "__tests__" not in str(p) and "traduccionesBase" not in str(p)
        )
        usadas = set(PATRON_CLAVES_FRONTEND.findall(codigo))
        self.assertTrue(usadas, "el patron dejo de encontrar claves: revisar la regex")
        claves_es = set(self.traducciones["es"])

        sin_traducir = sorted(k for k in usadas if k not in claves_es)
        self.assertEqual(
            sin_traducir, [],
            "estas claves se usan en el frontend pero no estan en translations.json, "
            f"asi que el usuario veria la clave en vez del mensaje: {sin_traducir}",
        )

    def test_el_fichero_es_json_valido_y_no_esta_vacio(self):
        self.assertGreater(len(self.traducciones["es"]), 100)
        self.assertIn("es", self.traducciones)

    def test_las_traducciones_base_del_frontend_estan_al_dia(self):
        """lib/traduccionesBase.ts es una copia generada del idioma por defecto.

        El frontend la usa como estado inicial para que el HTML del servidor y
        el primer pintado no salgan con las claves en crudo. Si se desincroniza
        de translations.json, vuelven a aparecer claves sin traducir en la
        primera carga. Regenerar con scripts/generar_traducciones_base.py.
        """
        generado = RAIZ / "lib" / "traduccionesBase.ts"
        self.assertTrue(generado.exists(), "falta lib/traduccionesBase.ts")

        texto = generado.read_text(encoding="utf-8")
        inicio = texto.index("{")
        fin = texto.rindex("}") + 1
        base = json.loads(texto[inicio:fin])

        self.assertEqual(
            base, self.traducciones["es"],
            "lib/traduccionesBase.ts no coincide con translations.json['es']: "
            "ejecuta `python scripts/generar_traducciones_base.py`",
        )


if __name__ == "__main__":
    unittest.main()
