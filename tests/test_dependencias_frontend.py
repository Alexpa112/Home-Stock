"""Test de regresion: toda dependencia npm que el codigo importa tiene que
estar declarada en package.json.

`components/dashboard/IconRenderer.tsx` importaba '@heroicons/react/24/solid' y
`components/ui/button.tsx` '@base-ui/react/button' y 'tailwind-merge' sin que
ninguno estuviese declarado. Consecuencia: `next build` fallaba con "Module not
found" y el paso que publica la imagen del frontend en GHCR llevaba semanas en
rojo en TODAS las promociones a produccion. La Pi hacia `docker compose pull`,
se traia un frontend antiguo y los cambios de lib/api.ts (entre ellos el
timeout del escaner) nunca llegaban, mientras el backend si se actualizaba.

Se comprueba aqui, en la suite de Python, porque ci.yml no ejecuta `next build`:
la rotura solo aparecia al construir la imagen, o sea al desplegar.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Modulos que resuelve el runtime o el framework, no package.json.
INTEGRADOS = {
    "react", "react-dom", "next",
    "fs", "path", "crypto", "url", "os", "http", "https",
    "stream", "buffer", "util", "events", "child_process", "zlib",
}

_IMPORT = re.compile(
    r'''from\s+['"]([^'"./][^'"]*)['"]|require\(\s*['"]([^'"./][^'"]*)['"]'''
)


def _paquete_base(especificador):
    """'@scope/pkg/sub' -> '@scope/pkg';  'pkg/sub' -> 'pkg'."""
    partes = especificador.split("/")
    if especificador.startswith("@"):
        return "/".join(partes[:2])
    return partes[0]


def _importaciones_del_codigo():
    encontradas = {}
    for ruta in list(RAIZ.rglob("*.ts")) + list(RAIZ.rglob("*.tsx")):
        texto = str(ruta)
        if "node_modules" in texto or "/.next/" in texto:
            continue
        for coincidencia in _IMPORT.finditer(ruta.read_text(encoding="utf-8", errors="ignore")):
            especificador = coincidencia.group(1) or coincidencia.group(2)
            if especificador.startswith("@/"):
                continue  # alias interno del proyecto (tsconfig paths)
            base = _paquete_base(especificador)
            encontradas.setdefault(base, set()).add(ruta.relative_to(RAIZ).as_posix())
    return encontradas


class DependenciasFrontendTests(unittest.TestCase):
    def test_todo_lo_importado_esta_declarado_en_package_json(self):
        paquete = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
        declaradas = set(paquete.get("dependencies", {})) | set(paquete.get("devDependencies", {}))

        sin_declarar = {
            base: ficheros
            for base, ficheros in _importaciones_del_codigo().items()
            if base not in declaradas and base not in INTEGRADOS
        }

        if sin_declarar:
            detalle = "\n".join(
                f"  {base}  <- importado en {', '.join(sorted(ficheros)[:3])}"
                for base, ficheros in sorted(sin_declarar.items())
            )
            self.fail(
                "Dependencias importadas pero no declaradas en package.json.\n"
                "`next build` fallara con 'Module not found' y la imagen del "
                "frontend no se publicara:\n" + detalle
            )

    def test_el_lockfile_conoce_las_dependencias_declaradas(self):
        """El Dockerfile usa `npm ci`, que aborta si el lockfile no esta
        sincronizado con package.json."""
        paquete = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((RAIZ / "package-lock.json").read_text(encoding="utf-8"))

        raiz_lock = lock.get("packages", {}).get("", {})
        declaradas_lock = set(raiz_lock.get("dependencies", {})) | set(
            raiz_lock.get("devDependencies", {})
        )
        faltan = (
            set(paquete.get("dependencies", {})) | set(paquete.get("devDependencies", {}))
        ) - declaradas_lock

        self.assertFalse(
            faltan,
            f"package-lock.json desincronizado, `npm ci` fallara. Falta: {sorted(faltan)}. "
            "Ejecuta `npm install` para regenerarlo.",
        )


if __name__ == "__main__":
    unittest.main()
