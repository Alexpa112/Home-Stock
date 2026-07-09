#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplica las traducciones manuales de alta calidad a translations.json
"""
import json
from pathlib import Path

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar traducciones manuales
    with open(base_path / 'manual_translations.json', 'r', encoding='utf-8') as f:
        manual = json.load(f)
        professional = manual['professional_translations']

    # Cargar traducciones existentes
    with open(base_path / 'stockhogar/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Aplicar traducciones manuales
    applied = 0
    for key, trans_dict in professional.items():
        for lang, text in trans_dict.items():
            if lang not in translations:
                translations[lang] = {}
            translations[lang][key] = text
            applied += 1

    # Guardar
    with open(base_path / 'stockhogar/translations.json', 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"Traducciones manuales aplicadas: {applied}")
    print(f"Total de claves en español: {len(translations.get('es', {}))}")

if __name__ == '__main__':
    main()
