#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la Fase 3 del rediseno de gastos
(docs/REDISENO_GASTOS.md: alta en hoja completa 7A, fecha editable, gestion
de categorias movida a ajustes) en stockhogar/translations.json para los 7
idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "categorias_gasto": {"es": "Categorías de gasto", "gl": "Categorías de gasto", "en": "Expense categories", "pt": "Categorias de despesa", "fr": "Catégories de dépense", "it": "Categorie di spesa", "de": "Ausgabenkategorien"},
    "fecha_gasto": {"es": "Fecha", "gl": "Data", "en": "Date", "pt": "Data", "fr": "Date", "it": "Data", "de": "Datum"},
    "concepto_placeholder": {"es": "¿En qué se ha gastado?", "gl": "¿En que se gastou?", "en": "What was it spent on?", "pt": "Em que foi gasto?", "fr": "Pour quoi cette dépense ?", "it": "Per cosa è stata spesa?", "de": "Wofür wurde es ausgegeben?"},
    "se_divide": {"es": "Se divide", "gl": "Divídese", "en": "Split", "pt": "Divide-se", "fr": "Se répartit", "it": "Si divide", "de": "Aufteilung"},
    "reparto_cuadra": {"es": "El reparto cuadra", "gl": "O reparto cadra", "en": "The split adds up", "pt": "A divisão está correta", "fr": "La répartition est correcte", "it": "La divisione è corretta", "de": "Die Aufteilung stimmt"},
    "reparto_no_cuadra": {"es": "El reparto no cuadra con el importe total", "gl": "O reparto non cadra co importe total", "en": "The split doesn't add up to the total", "pt": "A divisão não corresponde ao valor total", "fr": "La répartition ne correspond pas au montant total", "it": "La divisione non corrisponde all'importo totale", "de": "Die Aufteilung stimmt nicht mit dem Gesamtbetrag überein"},
    "excluido": {"es": "Excluido", "gl": "Excluído", "en": "Excluded", "pt": "Excluído", "fr": "Exclu", "it": "Escluso", "de": "Ausgeschlossen"},
    "gestionar_categorias_gasto": {"es": "Gestionar categorías de gasto", "gl": "Xestionar categorías de gasto", "en": "Manage expense categories", "pt": "Gerir categorias de despesa", "fr": "Gérer les catégories de dépense", "it": "Gestisci categorie di spesa", "de": "Ausgabenkategorien verwalten"},
    "sin_categorias_aun": {"es": "Todavía no hay categorías propias.", "gl": "Aínda non hai categorías propias.", "en": "No custom categories yet.", "pt": "Ainda não há categorias próprias.", "fr": "Pas encore de catégories personnalisées.", "it": "Ancora nessuna categoria personalizzata.", "de": "Noch keine eigenen Kategorien."},
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
