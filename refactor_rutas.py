#!/usr/bin/env python3
"""Script para refactorizar TODAS las rutas automáticamente."""
import re
import sys
from pathlib import Path

RUTAS_DIR = Path("stockhogar/rutas")

# Patrones de reemplazo
REPLACEMENTS = [
    # Imports
    (r'from flask import Blueprint, jsonify, request, session',
     'from flask import Blueprint, request, session\nfrom ..api import APIResponse, manejo_errores, requerir_sesion\nfrom ..utils import Validator, DataConverter'),

    (r'from flask import Blueprint, jsonify, request',
     'from flask import Blueprint, request\nfrom ..api import APIResponse, manejo_errores, requerir_sesion\nfrom ..utils import Validator, DataConverter'),

    # Decoradores
    (r'(@bp\.route\([^)]+\)\s*\ndef )',
     r'@requerir_sesion\n    @manejo_errores\n    \1'),

    # Validaciones
    (r'\(datos\.get\("([^"]+)"\) or ""\)\.strip\(\)',
     r'Validator.string_opcional(datos.get("\1"), "", 100)'),

    # jsonify() → APIResponse
    (r'return jsonify\((.+?)\)(, \d+)?',
     lambda m: f'return APIResponse.success({m.group(1)})' if not m.group(2) else f'return APIResponse.success({m.group(1)}, {m.group(2)[2:]})',
     0),

    # jsonify({"error": ...}) → APIResponse.error()
    (r'return jsonify\(\{"error": "([^"]+)"\}\)(, \d+)?',
     lambda m: f'return APIResponse.error("{m.group(1)}", {m.group(2)[2:] if m.group(2) else "400"})',
     0),
]

def refactor_file(filepath):
    """Refactoriza un archivo de ruta."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Aplicar reemplazos
    for pattern, replacement, _ in REPLACEMENTS[:2]:  # Solo imports por ahora
        content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE | re.DOTALL)

    if content != original:
        print(f"  Refactorizado: {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    rutas_files = sorted(RUTAS_DIR.glob("*.py"))
    already_done = {
        "productos.py",  # Ya refactorizado manualmente
        "categorias.py", # Ya refactorizado
        "listas.py",     # Parcialmente refactorizado
    }

    print("🚀 Refactorizando rutas...\n")

    count = 0
    for filepath in rutas_files:
        if filepath.name in ("__init__.py",) or filepath.name in already_done:
            continue

        if refactor_file(filepath):
            count += 1

    print(f"\n✅ {count} archivos refactorizados")

if __name__ == "__main__":
    main()
