"""Cada llamada del frontend a /api/... existe en el backend con ese metodo.

Recorre el codigo TypeScript, extrae las URLs literales (con `${...}` como comodin) y comprueba contra
`app.url_map` que hay una ruta que las atiende con el metodo usado. Atrapa en el momento de moverlas o
renombrarlas las rutas que el frontend sigue llamando."""
import re
from pathlib import Path

from stockhogar import create_app

RAIZ = Path(__file__).resolve().parent.parent.parent
CARPETAS = ["app", "components", "lib", "hooks", "contexts"]
RE_INICIO = re.compile(r"(?P<fn>apiCall|apiUpload|apiDownload|fetch)\(")


def _argumentos(texto, i):
    """Texto entre el parentesis que abre en `i` y su pareja (ignora parentesis dentro de cadenas)."""
    nivel, comilla = 0, None
    for j in range(i, len(texto)):
        c = texto[j]
        if comilla:
            if c == comilla and texto[j - 1] != "\\":
                comilla = None
        elif c in "'`\"":
            comilla = c
        elif c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
            if nivel == 0:
                return texto[i + 1:j]
    return texto[i + 1:]


def _llamadas():
    for carpeta in CARPETAS:
        for ruta in (RAIZ / carpeta).rglob("*.ts*"):
            if "__tests__" in ruta.parts or "node_modules" in ruta.parts:
                continue
            texto = ruta.read_text(encoding="utf-8")
            for m in RE_INICIO.finditer(texto):
                args = _argumentos(texto, m.end() - 1).strip()
                if not args or args[0] not in "'`":
                    continue
                url = re.match(r"(['`])(/api/[^'`$]*)", args)
                if not url:
                    continue
                # `${...}` dentro de la ruta es un comodin; tras el primer `?` o un `${` de consulta no importa
                completa = re.match(r"(['`])(/api/(?:[^'`$?]|\$\{[^}]*\})*)", args).group(2)
                completa = re.split(r"(?<!/)\$\{", completa)[0]  # `${...}` tras un nombre: sufijo de consulta
                completa = re.sub(r"\$\{[^}]*\}", "X", completa)
                metodo = "GET"
                if m["fn"] == "apiUpload":
                    metodo = "POST"
                else:
                    mm = re.search(r"method:\s*'([A-Z]+)'", args)
                    if mm:
                        metodo = mm.group(1)
                yield str(ruta.relative_to(RAIZ)), metodo, completa


def _reglas():
    app = create_app()
    for r in app.url_map.iter_rules():
        patron = re.sub(r"<[^>]+>", "[^/]+", r.rule)
        yield re.compile("^" + patron + "$"), r.methods


def test_las_llamadas_del_frontend_existen_en_el_backend():
    reglas = list(_reglas())
    llamadas = set(_llamadas())
    assert len(llamadas) > 60, f"el extractor encontro solo {len(llamadas)} llamadas: revisa la expresion"
    huerfanas = [
        (f, m, u) for f, m, u in sorted(llamadas)
        if not any(rx.match(u) and m in metodos for rx, metodos in reglas)
    ]
    assert not huerfanas, huerfanas
