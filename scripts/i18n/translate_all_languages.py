#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traduce las nuevas claves a todos los idiomas
"""
import json
from pathlib import Path

# Diccionario de traducciones manuales para palabras comunes
TRANSLATION_DICT = {
    # Español -> (Gallego, Inglés, Portugués, Francés, Italiano, Alemán)
    "Ajustes": ("Axustes", "Settings", "Configurações", "Paramètres", "Impostazioni", "Einstellungen"),
    "Analizar": ("Analizar", "Analyze", "Analisar", "Analyser", "Analizzare", "Analysieren"),
    "Cambiar": ("Cambiar", "Change", "Mudar", "Changer", "Cambiare", "Ändern"),
    "Categoría": ("Categoría", "Category", "Categoria", "Catégorie", "Categoria", "Kategorie"),
    "Categorías": ("Categorías", "Categories", "Categorias", "Catégories", "Categorie", "Kategorien"),
    "Cerrar": ("Pechar", "Close", "Fechar", "Fermer", "Chiudere", "Schließen"),
    "Crear": ("Crear", "Create", "Criar", "Créer", "Creare", "Erstellen"),
    "Email": ("Email", "Email", "Email", "Email", "Email", "Email"),
    "Editar": ("Editar", "Edit", "Editar", "Modifier", "Modificare", "Bearbeiten"),
    "Elegir": ("Elixir", "Choose", "Escolher", "Choisir", "Scegliere", "Wählen"),
    "Icono": ("Icona", "Icon", "Ícone", "Icône", "Icona", "Symbol"),
    "Listo": ("Listo", "Done", "Pronto", "Terminé", "Fatto", "Fertig"),
    "Mis Listas": ("Miñas listas", "My Lists", "Minhas Listas", "Mes Listes", "Le mie liste", "Meine Listen"),
    "Nueva": ("Nova", "New", "Nova", "Nouveau", "Nuovo", "Neue"),
    "Nuevo": ("Novo", "New", "Novo", "Nouveau", "Nuovo", "Neuer"),
    "Pon 0": ("Pon 0", "Set to 0", "Coloque 0", "Mettez 0", "Imposta 0", "Setzen Sie 0"),
    "Región": ("Rexión", "Region", "Região", "Région", "Regione", "Region"),
    "Salir": ("Saír", "Exit", "Sair", "Quitter", "Uscire", "Beenden"),
    "Stock": ("Stock", "Stock", "Estoque", "Stock", "Stock", "Bestand"),
    "Sub-descripción": ("Sub-descrición", "Sub-description", "Sub-descrição", "Sous-description", "Sotto-descrizione", "Unterbeschreibung"),
    "Teléfono": ("Teléfono", "Phone", "Telefone", "Téléphone", "Telefono", "Telefon"),
    "Tu": ("Tu", "Your", "Seu", "Votre", "Tuo", "Dein"),
    "Tus": ("Teus", "Your", "Seus", "Vos", "I tuoi", "Deine"),
    "Unidad": ("Unidade", "Unit", "Unidade", "Unité", "Unità", "Einheit"),
    "Usar": ("Usar", "Use", "Usar", "Utiliser", "Usare", "Verwenden"),
    "Volver": ("Volver", "Back", "Voltar", "Retour", "Tornare", "Zurück"),
}

def translate_text(text, language_index):
    """Traduce un texto a un idioma específico"""
    # language_index: 0=Gallego, 1=Inglés, 2=Portugués, 3=Francés, 4=Italiano, 5=Alemán

    # Buscar palabras conocidas
    for es_word, translations in TRANSLATION_DICT.items():
        if es_word.lower() in text.lower():
            # Reemplazar la palabra
            translated = translations[language_index]
            # Mantener la capitalización original
            if text[0].isupper() and not translated[0].isupper():
                text = text.replace(es_word, translated.capitalize(), 1)
            else:
                text = text.replace(es_word, translated, 1)
            return text

    # Si no hay traducción, devolver el texto original
    return text

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar el mapeo de nuevas claves
    with open(base_path / 'scripts' / 'i18n' / 'new_keys_mapping.json', 'r', encoding='utf-8') as f:
        new_keys_data = json.load(f)
        new_keys_es = new_keys_data['es']

    # Cargar traducciones existentes
    with open(base_path / 'stockhogar/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    languages = ['gl', 'en', 'pt', 'fr', 'it', 'de']

    # Para cada lenguaje
    for lang_idx, lang in enumerate(languages):
        if lang not in translations:
            translations[lang] = {}

        # Para cada nueva clave
        for key, text_es in new_keys_es.items():
            if key not in translations[lang]:
                # Intentar traducir
                translated = translate_text(text_es, lang_idx)
                translations[lang][key] = translated

    # Agregar el idioma español
    if 'es' not in translations:
        translations['es'] = {}
    for key, text_es in new_keys_es.items():
        if key not in translations['es']:
            translations['es'][key] = text_es

    # Guardar las traducciones actualizadas
    with open(base_path / 'stockhogar/translations.json', 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print("Traducciones actualizadas en translations.json")
    print(f"Nuevas claves agregadas: {len(new_keys_es)}")
    print("Idiomas actualizados: es, gl, en, pt, fr, it, de")

if __name__ == '__main__':
    main()
