#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fusiona las claves de traduccion de la funcionalidad de gastos compartidos
del hogar en stockhogar/translations.json para los 7 idiomas soportados."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
TRANSLATIONS_FILE = BASE / "stockhogar" / "translations.json"

NUEVAS = {
    "recurso_gasto": {"es": "Gasto", "gl": "Gasto", "en": "Expense", "pt": "Despesa", "fr": "Dépense", "it": "Spesa", "de": "Ausgabe"},
    "nav_gastos": {"es": "Gastos", "gl": "Gastos", "en": "Expenses", "pt": "Despesas", "fr": "Dépenses", "it": "Spese", "de": "Ausgaben"},
    "nuevo_gasto": {"es": "Nuevo gasto", "gl": "Novo gasto", "en": "New expense", "pt": "Nova despesa", "fr": "Nouvelle dépense", "it": "Nuova spesa", "de": "Neue Ausgabe"},
    "editar_gasto": {"es": "Editar gasto", "gl": "Editar gasto", "en": "Edit expense", "pt": "Editar despesa", "fr": "Modifier la dépense", "it": "Modifica spesa", "de": "Ausgabe bearbeiten"},
    "descripcion": {"es": "Descripción", "gl": "Descrición", "en": "Description", "pt": "Descrição", "fr": "Description", "it": "Descrizione", "de": "Beschreibung"},
    "importe_total": {"es": "Importe total", "gl": "Importe total", "en": "Total amount", "pt": "Valor total", "fr": "Montant total", "it": "Importo totale", "de": "Gesamtbetrag"},
    "pagado_por": {"es": "Pagado por", "gl": "Pagado por", "en": "Paid by", "pt": "Pago por", "fr": "Payé par", "it": "Pagato da", "de": "Bezahlt von"},
    "participantes": {"es": "Participantes", "gl": "Participantes", "en": "Participants", "pt": "Participantes", "fr": "Participants", "it": "Partecipanti", "de": "Teilnehmer"},
    "dividir_partes_iguales": {"es": "Dividir a partes iguales", "gl": "Dividir a partes iguais", "en": "Split equally", "pt": "Dividir igualmente", "fr": "Répartir également", "it": "Dividi in parti uguali", "de": "Gleichmäßig aufteilen"},
    "saldo_neto": {"es": "Saldo", "gl": "Saldo", "en": "Balance", "pt": "Saldo", "fr": "Solde", "it": "Saldo", "de": "Saldo"},
    "le_deben": {"es": "Le deben", "gl": "Débenlle", "en": "Owed to them", "pt": "Devem a ele/ela", "fr": "On lui doit", "it": "Gli/le devono", "de": "Wird geschuldet"},
    "debe": {"es": "Debe", "gl": "Debe", "en": "Owes", "pt": "Deve", "fr": "Doit", "it": "Deve", "de": "Schuldet"},
    "sin_gastos_aun": {"es": "Todavía no hay gastos registrados.", "gl": "Aínda non hai gastos rexistrados.", "en": "No expenses recorded yet.", "pt": "Ainda não há despesas registradas.", "fr": "Aucune dépense enregistrée pour le moment.", "it": "Nessuna spesa registrata ancora.", "de": "Noch keine Ausgaben erfasst."},
    "registrar_pago": {"es": "Registrar pago", "gl": "Rexistrar pago", "en": "Record payment", "pt": "Registrar pagamento", "fr": "Enregistrer un paiement", "it": "Registra pagamento", "de": "Zahlung erfassen"},
    "importe": {"es": "Importe", "gl": "Importe", "en": "Amount", "pt": "Valor", "fr": "Montant", "it": "Importo", "de": "Betrag"},
    "nota_opcional": {"es": "Nota (opcional)", "gl": "Nota (opcional)", "en": "Note (optional)", "pt": "Nota (opcional)", "fr": "Note (facultatif)", "it": "Nota (facoltativa)", "de": "Notiz (optional)"},
    "guardar": {"es": "Guardar", "gl": "Gardar", "en": "Save", "pt": "Salvar", "fr": "Enregistrer", "it": "Salva", "de": "Speichern"},
    "cancelar": {"es": "Cancelar", "gl": "Cancelar", "en": "Cancel", "pt": "Cancelar", "fr": "Annuler", "it": "Annulla", "de": "Abbrechen"},
    "confirmar_eliminar_gasto": {"es": "¿Eliminar este gasto?", "gl": "¿Eliminar este gasto?", "en": "Delete this expense?", "pt": "Excluir esta despesa?", "fr": "Supprimer cette dépense ?", "it": "Eliminare questa spesa?", "de": "Diese Ausgabe löschen?"},
    "err_importe_no_cuadra": {"es": "La suma del reparto no coincide con el importe total", "gl": "A suma do reparto non coincide co importe total", "en": "The split total doesn't match the total amount", "pt": "A soma da divisão não corresponde ao valor total", "fr": "La somme de la répartition ne correspond pas au montant total", "it": "La somma della ripartizione non corrisponde all'importo totale", "de": "Die Summe der Aufteilung stimmt nicht mit dem Gesamtbetrag überein"},
}


def main():
    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        translations = json.load(f)

    idiomas = list(translations.keys())
    añadidas = 0
    for clave, textos in NUEVAS.items():
        for idioma in idiomas:
            if clave not in translations[idioma]:
                translations[idioma][clave] = textos.get(idioma, textos["es"])
                añadidas += 1

    with open(TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Claves nuevas: {len(NUEVAS)}. Entradas añadidas: {añadidas}.")
    for idioma in idiomas:
        print(f"  {idioma}: {len(translations[idioma])} claves totales")


if __name__ == "__main__":
    main()
