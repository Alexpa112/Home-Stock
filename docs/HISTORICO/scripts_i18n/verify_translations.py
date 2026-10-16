#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica que todas las claves de traducción existan en todos los idiomas
"""
import json
from pathlib import Path
from collections import defaultdict

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar traducciones
    with open(base_path / 'stockhogar/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Obtener todas las claves del español
    spanish_keys = set(translations.get('es', {}).keys())
    languages = ['gl', 'en', 'pt', 'fr', 'it', 'de']

    print(f"Claves en Español (es): {len(spanish_keys)}")
    print(f"Idiomas a verificar: {', '.join(languages)}")

    missing_by_lang = defaultdict(list)

    # Verificar cada idioma
    for lang in languages:
        if lang not in translations:
            print(f"\nERROR: Idioma {lang} no existe en translations.json")
            continue

        lang_keys = set(translations[lang].keys())
        missing = spanish_keys - lang_keys

        if missing:
            missing_by_lang[lang] = sorted(list(missing))
            print(f"\nIDIROMA {lang}: {len(lang_keys)} claves ({len(missing)} faltantes)")
            if len(missing) <= 10:
                for key in sorted(missing):
                    print(f"  - {key}")
        else:
            print(f"\nIDIOMA {lang}: {len(lang_keys)} claves - OK")

    # Mostrar resumen
    total_missing = sum(len(v) for v in missing_by_lang.values())
    print(f"\n========================================")
    print(f"RESUMEN: {total_missing} claves faltantes en total")

    if total_missing == 0:
        print("✓ TODAS LAS CLAVES ESTAN COMPLETAS EN TODOS LOS IDIOMAS")
    else:
        print("NECESITA COMPLETAR LAS TRADUCCIONES FALTANTES")

    return total_missing == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
