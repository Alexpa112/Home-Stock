"""Todos los imports relativos del paquete (tambien los de dentro de funciones) apuntan a un modulo
que existe. Un `from .x import y` dentro de una funcion no falla al importar el modulo: si se mueve
el fichero de carpeta, falla (o se traga un `except`) solo cuando la funcion se ejecuta."""
import ast
import importlib.util
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent


def _imports_relativos():
    for dp, dn, fn in os.walk(RAIZ / "stockhogar"):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if not f.endswith(".py"):
                continue
            ruta = Path(dp) / f
            modulo = ".".join(ruta.relative_to(RAIZ).with_suffix("").parts)
            if f == "__init__.py":
                modulo = modulo[: -len(".__init__")]
                paquete = modulo
            else:
                paquete = modulo.rpartition(".")[0]
            for n in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
                if isinstance(n, ast.ImportFrom) and n.level:
                    base = paquete.split(".")
                    base = base[: len(base) - (n.level - 1)]
                    yield ruta, n.lineno, ".".join(base + ([n.module] if n.module else []))


def test_los_imports_relativos_existen():
    rotos = [
        f"{ruta.relative_to(RAIZ)}:{linea} -> {destino}"
        for ruta, linea, destino in _imports_relativos()
        if importlib.util.find_spec(destino) is None
    ]
    assert not rotos, rotos
