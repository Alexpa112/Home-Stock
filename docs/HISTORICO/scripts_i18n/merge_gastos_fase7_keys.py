#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 7 del rediseno de gastos
(docs/REDISENO_GASTOS.md: historial de liquidaciones listable y reversible)
en stockhogar/translations.json para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

# "historial_pagos" y "recurso_liquidacion" ya existen (el sistema de
# liquidaciones equivalente se implemento en paralelo en otra sesion); solo
# se añade "deshacer", que la version remota no tenia (usaba confirmar +
# eliminar sin un verbo propio).
NUEVAS = {
    "deshacer": {"es": "Deshacer", "gl": "Desfacer", "en": "Undo", "pt": "Desfazer", "fr": "Annuler", "it": "Annulla", "de": "Rückgängig"},
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
