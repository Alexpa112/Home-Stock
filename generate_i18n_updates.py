#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el código JavaScript necesario para actualizar i18n.js
"""
import json
from pathlib import Path

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar el mapeo de textos a claves
    with open(base_path / 'text_to_key_mapping.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # Generar mapeo JavaScript para botonesMapeo
    print("// Nuevos mapeos para agregar a i18n.js - botonesMapeo")
    print("const nuevosBotonesMapeo = {")
    for text, key in sorted(mapping.items()):
        if text and key and len(text) < 80:  # Solo textos cortos para botones
            # Escapar comillas
            text_escaped = text.replace("'", "\\'")
            print(f"  '{text_escaped}': '{key}',")
    print("};")

    print("\n// Para agregar al textoVacioMapeo:")
    print("const nuevoTextoVacioMapeo = {")
    for text, key in sorted(mapping.items()):
        if text and key and len(text) > 30:  # Solo textos largos
            text_escaped = text.replace("'", "\\'").replace("\n", " ")
            print(f"  '{text_escaped}': '{key}',")
    print("};")

    # Guardar mapeos en JSON
    botones_cortos = {}
    textos_largos = {}

    for text, key in mapping.items():
        if not text or not key:
            continue
        if len(text) < 80:
            botones_cortos[text] = key
        if len(text) > 30:
            textos_largos[text] = key

    output = {
        "botones_mapeo": botones_cortos,
        "texto_vacio_mapeo": textos_largos
    }

    with open(base_path / 'i18n_mapeos.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nMapeos guardados en i18n_mapeos.json")
    print(f"Total de mapeos de botones: {len(botones_cortos)}")
    print(f"Total de mapeos de textos largos: {len(textos_largos)}")

if __name__ == '__main__':
    main()
