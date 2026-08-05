#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 6 del rediseno de gastos
(docs/REDISENO_GASTOS.md: KPIs del resumen 10A) en stockhogar/translations.json
para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "total_mes": {"es": "Este mes", "gl": "Este mes", "en": "This month", "pt": "Este mês", "fr": "Ce mois-ci", "it": "Questo mese", "de": "Diesen Monat"},
    "vs_mes_anterior": {"es": "vs. mes anterior", "gl": "vs. mes anterior", "en": "vs. last month", "pt": "vs. mês anterior", "fr": "vs. mois précédent", "it": "vs. mese precedente", "de": "ggü. Vormonat"},
    "tu_parte": {"es": "Tu parte", "gl": "A túa parte", "en": "Your share", "pt": "A tua parte", "fr": "Ta part", "it": "La tua parte", "de": "Dein Anteil"},
    "del_total": {"es": "del total", "gl": "do total", "en": "of the total", "pt": "do total", "fr": "du total", "it": "del totale", "de": "der Gesamtsumme"},
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
