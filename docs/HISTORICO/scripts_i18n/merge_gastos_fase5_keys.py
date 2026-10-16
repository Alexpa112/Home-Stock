#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 5 del rediseno de gastos
(docs/REDISENO_GASTOS.md: balance hero 1A, deudas simplificadas 9A, menu de
acciones secundarias 6A) en stockhogar/translations.json para los 7 idiomas
soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "tu_balance": {"es": "Tu balance", "gl": "O teu balance", "en": "Your balance", "pt": "O teu saldo", "fr": "Ton solde", "it": "Il tuo saldo", "de": "Dein Saldo"},
    "te_deben_total": {"es": "Te deben en total", "gl": "Débenche en total", "en": "You're owed overall", "pt": "Devem-te no total", "fr": "On te doit en tout", "it": "Ti devono in totale", "de": "Man schuldet dir insgesamt"},
    "debes_total": {"es": "Debes en total", "gl": "Debes en total", "en": "You owe overall", "pt": "Deves no total", "fr": "Tu dois en tout", "it": "Devi in totale", "de": "Du schuldest insgesamt"},
    "estas_en_paz": {"es": "Estás en paz", "gl": "Estás en paz", "en": "You're all settled up", "pt": "Estás em dia", "fr": "Tu es à jour", "it": "Sei in pari", "de": "Du bist ausgeglichen"},
    "paga_a": {"es": "paga a", "gl": "paga a", "en": "pays", "pt": "paga a", "fr": "paie", "it": "paga a", "de": "zahlt an"},
    "saldar": {"es": "Saldar", "gl": "Saldar", "en": "Settle", "pt": "Liquidar", "fr": "Régler", "it": "Salda", "de": "Ausgleichen"},
    "acciones_gastos": {"es": "Más acciones", "gl": "Máis accións", "en": "More actions", "pt": "Mais ações", "fr": "Plus d'actions", "it": "Altre azioni", "de": "Weitere Aktionen"},
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
