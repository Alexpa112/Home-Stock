#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 2 del rediseno de gastos
(docs/REDISENO_GASTOS.md: segmented control 2A, estado vacio 12A) en
stockhogar/translations.json para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "balances": {"es": "Balances", "gl": "Balances", "en": "Balances", "pt": "Saldos", "fr": "Balances", "it": "Saldi", "de": "Salden"},
    "resumen": {"es": "Resumen", "gl": "Resumo", "en": "Summary", "pt": "Resumo", "fr": "Résumé", "it": "Riepilogo", "de": "Übersicht"},
    "sin_gastos_titulo": {"es": "Aún no hay gastos", "gl": "Aínda non hai gastos", "en": "No expenses yet", "pt": "Ainda não há despesas", "fr": "Pas encore de dépenses", "it": "Ancora nessuna spesa", "de": "Noch keine Ausgaben"},
    "sin_gastos_descripcion": {"es": "Apunta el primer gasto compartido y calcularemos quién debe a quién.", "gl": "Apunta o primeiro gasto compartido e calcularemos quen lle debe a quen.", "en": "Log the first shared expense and we'll work out who owes whom.", "pt": "Registe a primeira despesa partilhada e calcularemos quem deve a quem.", "fr": "Enregistrez la première dépense partagée et nous calculerons qui doit quoi à qui.", "it": "Registra la prima spesa condivisa e calcoleremo chi deve cosa a chi.", "de": "Erfasse die erste gemeinsame Ausgabe, und wir berechnen, wer wem etwas schuldet."},
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
