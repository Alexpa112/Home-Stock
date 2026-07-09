#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualiza i18n.js con los nuevos mapeos de traducción
"""
import json
import re
from pathlib import Path

def main():
    base_path = Path('C:\\Users\\alejandro.paz\\Desktop\\Claude Pruebas\\StockHogar')

    # Cargar mapeos
    with open(base_path / 'text_to_key_mapping.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # Leer i18n.js
    i18n_path = base_path / 'stockhogar\\static\\i18n.js'
    with open(i18n_path, 'r', encoding='utf-8') as f:
        i18n_content = f.read()

    # Encontrar el objeto botonesMapeo
    botones_pattern = r'const botonesMapeo = \{([^}]+)\};'
    match = re.search(botones_pattern, i18n_content)

    if match:
        # Extraer los mapeos existentes
        existing_content = match.group(1)

        # Crear nuevas líneas de mapeo
        new_mappings = []
        for text, key in sorted(mapping.items()):
            if text and key:
                # Escapar comillas simples
                text_safe = text.replace("'", "\\'")
                # Solo agregar si no existe
                if f"'{text_safe}'" not in existing_content:
                    new_mappings.append(f"      '{text_safe}': '{key}',")

        if new_mappings:
            # Encontrar la última línea de mapeo
            lines = existing_content.strip().split('\n')
            # Agregar nuevos mapeos antes de la última línea
            insert_pos = len(lines) - 1
            lines.insert(insert_pos, '      // Nuevos mapeos agregados automáticamente')
            lines.extend(new_mappings)

            # Reconstruir el objeto
            new_botones = '{\n' + '\n'.join(lines) + '\n    }'

            # Reemplazar en el contenido
            new_i18n = i18n_content.replace(
                f'const botonesMapeo = {match.group(0)[len("const botonesMapeo = "):]}',
                f'const botonesMapeo = {new_botones}'
            )

            # Guardar
            with open(i18n_path, 'w', encoding='utf-8') as f:
                f.write(new_i18n)

            print("OK: Actualizado i18n.js")
            print(f"  Nuevos mapeos agregados: {len(new_mappings)}")
        else:
            print("OK: Todos los mapeos ya existen en i18n.js")
    else:
        print("ERROR: No se encontro el objeto botonesMapeo en i18n.js")
        print("  Actualiza manualmente usando new_i18n_mappings.js")

if __name__ == '__main__':
    main()
