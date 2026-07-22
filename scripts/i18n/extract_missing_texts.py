#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae todos los textos sin traducir de los templates y JavaScript
"""
import re
import json
from pathlib import Path

def extract_texts_from_html(html_content):
    """Extrae textos de placeholders, titles, labels, etc."""
    texts = set()

    # Placeholders
    for match in re.finditer(r'placeholder="([^"]+)"', html_content):
        texts.add(match.group(1))

    # Titles
    for match in re.finditer(r'title="([^"]+)"', html_content):
        texts.add(match.group(1))

    # Aria-labels
    for match in re.finditer(r'aria-label="([^"]+)"', html_content):
        texts.add(match.group(1))

    # Labels
    for match in re.finditer(r'<label[^>]*>([^<]+)<', html_content):
        text = match.group(1).strip()
        if text and len(text) > 2:
            texts.add(text)

    # Buttons y elementos con contenido de texto
    for match in re.finditer(r'<button[^>]*>([^<]+)</button>', html_content):
        text = match.group(1).strip()
        if text and len(text) > 2 and text != '+' and text != '✕' and text != '▾':
            texts.add(text)

    # H2, H3, span con texto
    for match in re.finditer(r'<(?:h2|h3|p|span)[^>]*>([^<]+)<', html_content):
        text = match.group(1).strip()
        if text and len(text) > 2 and '©' not in text and not text.startswith('$'):
            texts.add(text)

    # Options
    for match in re.finditer(r'<option[^>]*>([^<]+)<', html_content):
        text = match.group(1).strip()
        if text and len(text) > 2:
            texts.add(text)

    return texts

def load_translations(file_path):
    """Carga las traducciones actuales"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # Rutas
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')
    html_file = base_path / 'stockhogar\\templates\\index.html'
    translations_file = base_path / 'stockhogar\\translations.json'

    # Leer HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    # Extraer textos
    texts = extract_texts_from_html(html)

    # Cargar traducciones existentes
    translations = load_translations(translations_file)
    spanish_keys = set(translations.get('es', {}).keys())

    # Encontrar textos sin traducción
    missing = []
    for text in sorted(texts):
        # Limpiar el texto
        clean_text = text.strip()
        if not clean_text:
            continue

        # Buscar si existe una clave correspondiente
        found = False
        for key in spanish_keys:
            if translations['es'][key] == clean_text:
                found = True
                break

        if not found:
            missing.append(clean_text)

    print(f"Total de textos encontrados: {len(texts)}")
    print(f"Total de claves de traducción: {len(spanish_keys)}")
    print(f"Textos sin traducción: {len(missing)}")

    # Guardar a archivo JSON
    output_file = base_path / 'scripts' / 'i18n' / 'missing_texts.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'missing_texts': missing}, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado en: {output_file}")

if __name__ == '__main__':
    main()
