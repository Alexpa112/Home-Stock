#!/usr/bin/env python3
"""Ejecuta pytest y sale con os._exit() en vez de dejar que el interprete
termine normalmente.

Motivo (ver .github/workflows/ci.yml, job test-python): con las
dependencias nativas pesadas que arrastra argostranslate (torch,
ctranslate2, onnxruntime) conviviendo con la OpenMP de
opencv-python-headless, los tests pasan siempre, pero el proceso revienta
al cerrar Python (SIGABRT o SIGSEGV segun la combinacion de versiones) al
liberar esas librerias nativas en el cierre normal del interprete —
KMP_DUPLICATE_LIB_OK=TRUE mitiga el caso de SIGABRT pero no el de SIGSEGV.
os._exit() se salta ese cierre (atexit, __del__, GC de las extensiones C)
por completo, evitando el crash sin tocar el resultado real de los tests:
el codigo de salida que se propaga es el de pytest.main(), asi que un fallo
de test de verdad sigue haciendo fallar el job igual que antes.
"""
import os
import sys

import pytest

if __name__ == "__main__":
    # Añade el directorio raíz del proyecto a sys.path para que PYTHONPATH
    # se configure correctamente en CI (donde solo ejecutamos pytest sin
    # pip install -e . ni PYTHONPATH exportado).
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    codigo_salida = pytest.main(sys.argv[1:])
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(codigo_salida)
