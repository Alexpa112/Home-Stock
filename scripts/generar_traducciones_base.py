#!/usr/bin/env python3
"""Regenera lib/traduccionesBase.ts desde stockhogar/translations.json.

El frontend necesita las traducciones del idioma por defecto de forma SÍNCRONA:
TranslationProvider es un componente de cliente y hasta que
/api/idiomas/todos/<idioma> responde no tiene nada que mostrar, así que el HTML
del servidor y el primer pintado salían con las CLAVES en crudo
("titulo_login", "btn_iniciar_sesion"...). Además de verse feo, provocaba un
error de hidratación de React (#418) en todas las páginas, porque el texto del
servidor no coincidía con el del cliente.

Solo se copia el idioma por defecto (es): el resto se siguen pidiendo al
backend, y como partida se muestra el español en vez de las claves.

Uso:
    python scripts/generar_traducciones_base.py

tests/test_traducciones_completas.py falla si el fichero generado se
desincroniza de translations.json.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "stockhogar" / "translations.json"
DESTINO = RAIZ / "lib" / "traduccionesBase.ts"
IDIOMA_BASE = "es"

CABECERA = '''// GENERADO — no editar a mano.
//
// Copia del idioma por defecto (es) de stockhogar/translations.json, usada como
// estado inicial de TranslationContext. Sin ella, el HTML del servidor y el
// primer pintado salen con las CLAVES en crudo ("titulo_login",
// "btn_iniciar_sesion"...) hasta que /api/idiomas/todos/<idioma> responde: el
// usuario veia las claves y React tiraba el HTML del servidor con un error de
// hidratacion (#418) en todas las paginas.
//
// Regenerar con:
//   python scripts/generar_traducciones_base.py
// tests/test_traducciones_completas.py falla si este fichero se desincroniza.

const TRADUCCIONES_BASE: Record<string, string> = '''


def main():
    traducciones = json.loads(ORIGEN.read_text(encoding="utf-8"))
    base = traducciones[IDIOMA_BASE]
    cuerpo = json.dumps(base, ensure_ascii=False, indent=2, sort_keys=True)
    DESTINO.write_text(
        CABECERA + cuerpo + "\n\nexport default TRADUCCIONES_BASE\n",
        encoding="utf-8",
    )
    print(f"{DESTINO.relative_to(RAIZ)} regenerado con {len(base)} claves")


if __name__ == "__main__":
    main()
