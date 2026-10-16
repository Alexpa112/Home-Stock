"""Arranque en frio con varios workers: todos deben terminar con las mismas claves."""
import subprocess
import sys
import textwrap
import time


def test_arranque_en_frio_concurrente_mismas_claves(tmp_path):
    codigo = textwrap.dedent("""
        import sys, time, pathlib
        from stockhogar import config
        config.CLAVES_PATH = pathlib.Path(sys.argv[1]) / "data" / "secret.json"
        from stockhogar.nucleo import seguridad  # noqa: F401 (precarga dependencias)
        import importlib
        time.sleep(max(0, float(sys.argv[2]) - time.time()))
        importlib.reload(seguridad)
        print(seguridad.FLASK_SECRET_KEY, seguridad.CLAVE_CIFRADO)
    """)
    salida = time.time() + 3  # todos recargan el modulo a la vez
    procs = [
        subprocess.Popen([sys.executable, "-c", codigo, str(tmp_path), str(salida)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(8)
    ]
    salidas = [p.communicate() for p in procs]
    assert all(p.returncode == 0 for p in procs), [e for _, e in salidas]
    assert len({o.strip() for o, _ in salidas}) == 1
