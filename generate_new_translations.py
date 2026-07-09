#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera nuevas claves de traducción a partir de los textos faltantes
"""
import json
import re
from pathlib import Path

def text_to_key(text):
    """Convierte un texto a una clave snake_case"""
    # Limpiar caracteres especiales
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    # Convertir a minúsculas y reemplazar espacios con guiones bajos
    key = text.lower().strip()
    key = re.sub(r'\s+', '_', key)
    # Limitar a 50 caracteres
    return key[:50]

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar textos faltantes
    with open(base_path / 'missing_texts.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        missing_texts = data['missing_texts']

    # Cargar traducciones actuales
    with open(base_path / 'stockhogar/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Generar nuevas claves
    new_keys = {}
    for text in missing_texts:
        # Limpiar el texto
        clean_text = text.strip()
        if not clean_text:
            continue

        # Generar clave
        key = text_to_key(clean_text)

        # Asegurar que la clave sea única
        counter = 1
        original_key = key
        while key in translations.get('es', {}) or key in new_keys:
            key = f"{original_key}_{counter}"
            counter += 1

        # Almacenar el mapeo
        new_keys[key] = clean_text

    print(f"Nuevas claves generadas: {len(new_keys)}")

    # Guardar mapeo
    with open(base_path / 'new_keys_mapping.json', 'w', encoding='utf-8') as f:
        json.dump({'es': new_keys}, f, ensure_ascii=False, indent=2)

    print(f"Guardado mapeo en: new_keys_mapping.json")
    print("\nPrimeras 10 claves:")
    for i, (key, text) in enumerate(list(new_keys.items())[:10]):
        print(f"  {key}: {text[:50]}")

if __name__ == '__main__':
    main()
