"""El mapa de rutas (URL, metodos, endpoint) no cambia al reorganizar el codigo.

`tests/datos/mapa_rutas.json` es la foto de las 122 rutas. Si anades, quitas o renombras una ruta a
proposito, regenera el fichero: `python tests/test_mapa_de_rutas.py --regenerar`."""
import json
import sys
from pathlib import Path

from stockhogar import create_app

FOTO = Path(__file__).parent / "datos" / "mapa_rutas.json"


def _mapa_actual():
    app = create_app()
    return sorted([r.rule, sorted(r.methods - {"HEAD", "OPTIONS"}), r.endpoint] for r in app.url_map.iter_rules())


def test_el_mapa_de_rutas_no_cambia():
    esperado = json.loads(FOTO.read_text(encoding="utf-8"))
    actual = _mapa_actual()
    assert actual == esperado, (
        "Cambio en las rutas. Sobran: %s. Faltan: %s"
        % ([r for r in actual if r not in esperado], [r for r in esperado if r not in actual])
    )


if __name__ == "__main__" and "--regenerar" in sys.argv:
    FOTO.write_text(json.dumps(_mapa_actual(), ensure_ascii=False), encoding="utf-8")
    print("regenerado", FOTO)
