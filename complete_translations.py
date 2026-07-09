#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Completa las traducciones usando patrones inteligentes y diccionarios
"""
import json
import re
from pathlib import Path

# Diccionarios de traducción por idioma
VOCAB = {
    "gl": {  # Gallego
        "Nuevo": "Novo", "Nueva": "Nova", "Nuevas": "Novas",
        "Editar": "Editar", "Editando": "Editando",
        "Crear": "Crear", "Creando": "Creando",
        "Eliminar": "Eliminar", "Borrar": "Borrar",
        "Guardar": "Gardar", "Salvando": "Gardando",
        "Cancelar": "Cancelar",
        "Añadir": "Engadir", "Añadiendo": "Engadindo",
        "Categoría": "Categoría", "Categorías": "Categorías",
        "Lista": "Lista", "Listas": "Listas",
        "Stock": "Stock", "Estoque": "Estoque",
        "Icono": "Icona", "Iconos": "Iconas",
        "Mi": "Miña", "Mis": "Miñas",
        "Tu": "Tu", "Tus": "Teus",
        "El": "O", "Los": "Os",
        "La": "A", "Las": "As",
        "De": "De",
        "Para": "Para",
        "Por": "Por",
        "Con": "Con",
        "Sin": "Sen",
        "Nombre": "Nome",
        "Email": "Email",
        "Usuario": "Usuario",
        "Contraseña": "Contrasinal",
        "Idioma": "Idioma",
        "Tema": "Tema",
        "Región": "Rexión",
        "País": "País",
        "Teléfono": "Teléfono",
        "Compartir": "Compartir",
        "Permiso": "Permiso",
            },
    "en": {  # Inglés
        "Nuevo": "New", "Nueva": "New", "Nuevas": "New",
        "Editar": "Edit", "Editando": "Editing",
        "Crear": "Create", "Creando": "Creating",
        "Eliminar": "Delete", "Borrar": "Remove",
        "Guardar": "Save", "Salvando": "Saving",
        "Cancelar": "Cancel",
        "Añadir": "Add", "Añadiendo": "Adding",
        "Categoría": "Category", "Categorías": "Categories",
        "Lista": "List", "Listas": "Lists",
        "Stock": "Stock", "Estoque": "Stock",
        "Icono": "Icon", "Iconos": "Icons",
        "Mi": "My", "Mis": "My",
        "Tu": "Your", "Tus": "Your",
        "El": "The", "Los": "The",
        "La": "The", "Las": "The",
        "De": "of",
        "Para": "for",
        "Por": "by",
        "Con": "with",
        "Sin": "without",
        "Nombre": "Name",
        "Email": "Email",
        "Usuario": "User",
        "Contraseña": "Password",
        "Idioma": "Language",
        "Tema": "Theme",
        "Región": "Region",
        "País": "Country",
        "Teléfono": "Phone",
        "Compartir": "Share",
        "Permiso": "Permission",
    },
    "pt": {  # Portugués
        "Nuevo": "Novo", "Nueva": "Nova", "Nuevas": "Novas",
        "Editar": "Editar", "Editando": "Editando",
        "Crear": "Criar", "Creando": "Criando",
        "Eliminar": "Deletar", "Borrar": "Remover",
        "Guardar": "Salvar", "Salvando": "Salvando",
        "Cancelar": "Cancelar",
        "Añadir": "Adicionar", "Añadiendo": "Adicionando",
        "Categoría": "Categoria", "Categorías": "Categorias",
        "Lista": "Lista", "Listas": "Listas",
        "Stock": "Estoque", "Estoque": "Estoque",
        "Icono": "Ícone", "Iconos": "Ícones",
        "Mi": "Minha", "Mis": "Minhas",
        "Tu": "Seu", "Tus": "Seus",
        "El": "O", "Los": "Os",
        "La": "A", "Las": "As",
        "De": "de",
        "Para": "para",
        "Por": "por",
        "Con": "com",
        "Sin": "sem",
        "Nombre": "Nome",
        "Email": "Email",
        "Usuario": "Usuário",
        "Contraseña": "Senha",
        "Idioma": "Idioma",
        "Tema": "Tema",
        "Región": "Região",
        "País": "País",
        "Teléfono": "Telefone",
        "Compartir": "Compartilhar",
        "Permiso": "Permissão",
    },
    "fr": {  # Francés
        "Nuevo": "Nouveau", "Nueva": "Nouvelle", "Nuevas": "Nouvelles",
        "Editar": "Modifier", "Editando": "Modifiant",
        "Crear": "Créer", "Creando": "Créant",
        "Eliminar": "Supprimer", "Borrar": "Enlever",
        "Guardar": "Enregistrer", "Salvando": "Enregistrant",
        "Cancelar": "Annuler",
        "Añadir": "Ajouter", "Añadiendo": "Ajoutant",
        "Categoría": "Catégorie", "Categorías": "Catégories",
        "Lista": "Liste", "Listas": "Listes",
        "Stock": "Stock", "Estoque": "Stock",
        "Icono": "Icône", "Iconos": "Icônes",
        "Mi": "Ma", "Mis": "Mes",
        "Tu": "Votre", "Tus": "Vos",
        "El": "Le", "Los": "Les",
        "La": "La", "Las": "Les",
        "De": "de",
        "Para": "pour",
        "Por": "par",
        "Con": "avec",
        "Sin": "sans",
        "Nombre": "Nom",
        "Email": "Email",
        "Usuario": "Utilisateur",
        "Contraseña": "Mot de passe",
        "Idioma": "Langue",
        "Tema": "Thème",
        "Región": "Région",
        "País": "Pays",
        "Teléfono": "Téléphone",
        "Compartir": "Partager",
        "Permiso": "Permission",
    },
    "it": {  # Italiano
        "Nuevo": "Nuovo", "Nueva": "Nuova", "Nuevas": "Nuove",
        "Editar": "Modifica", "Editando": "Modificando",
        "Crear": "Crea", "Creando": "Creando",
        "Eliminar": "Elimina", "Borrar": "Rimuovi",
        "Guardar": "Salva", "Salvando": "Salvando",
        "Cancelar": "Annulla",
        "Añadir": "Aggiungi", "Añadiendo": "Aggiungendo",
        "Categoría": "Categoria", "Categorías": "Categorie",
        "Lista": "Lista", "Listas": "Liste",
        "Stock": "Stock", "Estoque": "Stock",
        "Icono": "Icona", "Iconos": "Icone",
        "Mi": "La mia", "Mis": "Le mie",
        "Tu": "Tuo", "Tus": "Tuoi",
        "El": "Il", "Los": "I",
        "La": "La", "Las": "Le",
        "De": "di",
        "Para": "per",
        "Por": "per",
        "Con": "con",
        "Sin": "senza",
        "Nombre": "Nome",
        "Email": "Email",
        "Usuario": "Utente",
        "Contraseña": "Password",
        "Idioma": "Lingua",
        "Tema": "Tema",
        "Región": "Regione",
        "País": "Paese",
        "Teléfono": "Telefono",
        "Compartir": "Condividi",
        "Permiso": "Autorizzazione",
    },
    "de": {  # Alemán
        "Nuevo": "Neue", "Nueva": "Neue", "Nuevas": "Neue",
        "Editar": "Bearbeiten", "Editando": "Bearbeitung",
        "Crear": "Erstellen", "Creando": "Erstellung",
        "Eliminar": "Löschen", "Borrar": "Entfernen",
        "Guardar": "Speichern", "Salvando": "Speicherung",
        "Cancelar": "Abbrechen",
        "Añadir": "Hinzufügen", "Añadiendo": "Hinzufügen",
        "Categoría": "Kategorie", "Categorías": "Kategorien",
        "Lista": "Liste", "Listas": "Listen",
        "Stock": "Bestand", "Estoque": "Bestand",
        "Icono": "Symbol", "Iconos": "Symbole",
        "Mi": "Mein", "Mis": "Meine",
        "Tu": "Dein", "Tus": "Deine",
        "El": "Der", "Los": "Die",
        "La": "Die", "Las": "Die",
        "De": "von",
        "Para": "für",
        "Por": "durch",
        "Con": "mit",
        "Sin": "ohne",
        "Nombre": "Name",
        "Email": "Email",
        "Usuario": "Benutzer",
        "Contraseña": "Passwort",
        "Idioma": "Sprache",
        "Tema": "Design",
        "Región": "Region",
        "País": "Land",
        "Teléfono": "Telefon",
        "Compartir": "Teilen",
        "Permiso": "Berechtigung",
    },
}

def smart_translate(text, language):
    """Traduce un texto de manera inteligente usando patrones"""
    if language not in VOCAB:
        return text

    vocab = VOCAB[language]

    # Buscar y reemplazar palabras
    result = text
    for es_word, translated_word in vocab.items():
        # Búsqueda de palabras completas (case-insensitive al principio)
        pattern = re.compile(re.escape(es_word), re.IGNORECASE)

        def replacer(match):
            original = match.group(0)
            if original[0].isupper():
                return translated_word[0].upper() + translated_word[1:] if len(translated_word) > 0 else translated_word
            return translated_word

        result = pattern.sub(replacer, result)

    return result

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar traducciones
    with open(base_path / 'stockhogar/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Completas traducciones faltantes
    languages = ['gl', 'en', 'pt', 'fr', 'it', 'de']
    completed = 0

    for lang in languages:
        if lang not in translations:
            translations[lang] = {}

        for key, text_es in translations.get('es', {}).items():
            if key not in translations[lang] or not translations[lang][key]:
                # Traducir inteligentemente
                translated = smart_translate(text_es, lang)
                translations[lang][key] = translated
                completed += 1

    # Guardar
    with open(base_path / 'stockhogar/translations.json', 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"Traducciones completadas: {completed}")
    for lang in languages:
        print(f"  {lang}: {len(translations.get(lang, {}))} claves")

if __name__ == '__main__':
    main()
