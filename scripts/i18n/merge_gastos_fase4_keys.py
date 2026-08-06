#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 4 del rediseno de gastos
(docs/REDISENO_GASTOS.md: detalle de gasto 5A) en stockhogar/translations.json
para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "ver_detalle_gasto": {"es": "Ver detalle del gasto", "gl": "Ver detalle do gasto", "en": "View expense detail", "pt": "Ver detalhe da despesa", "fr": "Voir le détail de la dépense", "it": "Visualizza dettaglio spesa", "de": "Ausgabendetails anzeigen"},
}


def main():
    datos = json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    for idioma, bloque in datos.items():
        for clave, traducciones in NUEVAS.items():
            bloque[clave] = traducciones.get(idioma, traducciones["es"])
    TRANSLATIONS_FILE.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Añadidas {len(NUEVAS)} claves en {len(datos)} idiomas.")


if __name__ == "__main__":
    main()
