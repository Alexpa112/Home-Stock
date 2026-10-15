#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualiza el HTML para usar atributos data-i18n
"""
import json
import re
from pathlib import Path

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar el mapeo de textos a claves
    with open(base_path / 'scripts' / 'i18n' / 'new_keys_mapping.json', 'r', encoding='utf-8') as f:
        new_keys_data = json.load(f)
        text_to_key = new_keys_data['es']

    # Crear mapeo inverso (texto -> clave)
    mapping = {}
    for key, text in text_to_key.items():
        mapping[text.strip()] = key

    print(f"Mapeo de {len(mapping)} textos a claves")

    # Leer HTML
    html_file = base_path / 'stockhogar\\templates\\index.html'
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    # Mostrar instrucciones (no modificamos directamente el HTML aquí)
    print("\nMapeosde textos a claves para data-i18n:")
    for i, (text, key) in enumerate(list(mapping.items())[:20]):
        print(f"  '{text[:40]}' -> {key}")

    print(f"\nTotal de mapeos disponibles: {len(mapping)}")
    print("\nAhora necesitas actualizar manualmente el HTML o usar un script más avanzado.")
    print("Guarda este mapeo en 'text_to_key_mapping.json'")

    # Guardar mapeo
    with open(base_path / 'scripts' / 'i18n' / 'text_to_key_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
