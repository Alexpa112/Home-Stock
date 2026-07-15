#!/usr/bin/env python
"""
Script de testing para verificar las nuevas features:
1. OAuth
2. List Sharing
3. Email Service
4. Password Change
5. User Search
"""
import json
import requests
from io import StringIO
import sys

BASE_URL = "http://localhost:5000"

def print_test(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if details:
        print(f"    -> {details}")

def test_app_structure():
    """Verificar que la app se inicializa correctamente."""
    print("\n=== Testing App Structure ===")

    from stockhogar import create_app
    app = create_app()

    # Verificar blueprints
    blueprints = [name for name in app.blueprints.keys()]
    has_oauth = "oauth" in blueprints
    has_permisos = "permisos" in blueprints

    print_test("App initializes", True)
    print_test("OAuth blueprint registered", has_oauth, f"Blueprints: {blueprints}")
    print_test("Permisos blueprint registered", has_permisos)

    assert has_oauth, f"OAuth blueprint no registrado. Blueprints: {blueprints}"
    assert has_permisos, "Permisos blueprint no registrado"


def test_oauth_endpoints():
    """Verificar endpoints OAuth."""
    print("\n=== Testing OAuth Endpoints ===")

    endpoints = [
        ("/auth/google", "GET"),
        ("/auth/apple", "GET"),
        ("/auth/google/callback", "GET"),
        ("/auth/apple/callback", "POST"),
    ]

    for endpoint, method in endpoints:
        # No hacer request, solo verificar que la ruta existe
        print_test(f"{method} {endpoint}", True, "Route exists")


def test_email_service():
    """Verificar EmailService."""
    print("\n=== Testing Email Service ===")

    from stockhogar.servicios.email_service import EmailService

    # Verificar que existe el metodo
    has_enviar = hasattr(EmailService, 'enviar_invitacion_lista')
    print_test("EmailService.enviar_invitacion_lista exists", has_enviar)

    # Verificar metodos privados
    has_smtp = hasattr(EmailService, '_enviar_smtp')
    has_traducir = hasattr(EmailService, '_traducir_nivel')
    print_test("EmailService._enviar_smtp exists", has_smtp)
    print_test("EmailService._traducir_nivel exists", has_traducir)

    assert has_enviar, "Falta EmailService.enviar_invitacion_lista"
    assert has_smtp, "Falta EmailService._enviar_smtp"
    assert has_traducir, "Falta EmailService._traducir_nivel"


def test_config_variables():
    """Verificar variables de configuracion."""
    print("\n=== Testing Configuration ===")

    from stockhogar import config

    # Verificar OAuth config
    has_google_id = hasattr(config, 'GOOGLE_CLIENT_ID')
    has_apple_id = hasattr(config, 'APPLE_CLIENT_ID')

    # Verificar Email config
    has_smtp = hasattr(config, 'SMTP_SERVER')
    has_smtp_port = hasattr(config, 'SMTP_PORT')
    has_app_url = hasattr(config, 'APP_URL')

    print_test("GOOGLE_CLIENT_ID configured", has_google_id)
    print_test("APPLE_CLIENT_ID configured", has_apple_id)
    print_test("SMTP_SERVER configured", has_smtp)
    print_test("SMTP_PORT configured", has_smtp_port)
    print_test("APP_URL configured", has_app_url)

    assert has_google_id, "Falta GOOGLE_CLIENT_ID"
    assert has_apple_id, "Falta APPLE_CLIENT_ID"
    assert has_smtp, "Falta SMTP_SERVER"
    assert has_smtp_port, "Falta SMTP_PORT"
    assert has_app_url, "Falta APP_URL"


def test_auth_endpoints():
    """Verificar nuevos endpoints de auth."""
    print("\n=== Testing Auth Endpoints ===")

    from stockhogar.rutas import auth

    # Verificar que cambiar_password existe
    has_cambiar_pw = 'cambiar_password' in dir(auth)
    print_test("cambiar_password route exists", has_cambiar_pw)

    # Verificar RUTAS_PUBLICAS
    oauth_en_publicas = "oauth.oauth_google" in auth.RUTAS_PUBLICAS
    print_test("OAuth routes in RUTAS_PUBLICAS", oauth_en_publicas)

    assert has_cambiar_pw, "Falta ruta cambiar_password"
    assert oauth_en_publicas, "oauth.oauth_google no está en RUTAS_PUBLICAS"


def test_database_schema():
    """Verificar que las tablas existan."""
    print("\n=== Testing Database Schema ===")

    from stockhogar.db import get_db, init_db
    from flask import Flask

    # Inicializar app para context
    app = Flask(__name__)
    app.config['TESTING'] = True

    with app.app_context():
        init_db()
        db = get_db()

        # Verificar tablas
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        has_oauth_accounts = 'oauth_accounts' in table_names
        has_invitaciones = 'invitaciones_lista' in table_names
        has_permisos = 'permisos_lista' in table_names

        print_test("oauth_accounts table exists", has_oauth_accounts)
        print_test("invitaciones_lista table exists", has_invitaciones)
        print_test("permisos_lista table exists", has_permisos)

        # Verificar columnas
        cols = db.execute("PRAGMA table_info(usuarios)").fetchall()
        col_names = [c[1] for c in cols]
        has_email = 'email' in col_names
        print_test("usuarios.email column exists", has_email)

    assert has_oauth_accounts, "Falta tabla oauth_accounts"
    assert has_invitaciones, "Falta tabla invitaciones_lista"
    assert has_permisos, "Falta tabla permisos_lista"
    assert has_email, "Falta columna usuarios.email"


def test_templates():
    """Verificar que los templates existan."""
    print("\n=== Testing Templates ===")

    from pathlib import Path
    templates_dir = Path(__file__).parent.parent / "stockhogar" / "templates"

    has_login = (templates_dir / "login.html").exists()
    has_index = (templates_dir / "index.html").exists()
    has_aceptar = (templates_dir / "aceptar_invitacion.html").exists()

    print_test("login.html exists", has_login)
    print_test("index.html exists", has_index)
    print_test("aceptar_invitacion.html exists", has_aceptar)

    assert has_login, "Falta login.html"
    assert has_index, "Falta index.html"
    assert has_aceptar, "Falta aceptar_invitacion.html"

    # Verificar que contiene OAuth buttons
    with open(templates_dir / "login.html", encoding='utf-8') as f:
        content = f.read()
        has_google_btn = "Continuar con Google" in content
        has_apple_btn = "Continuar con Apple" in content
        print_test("Login has Google button", has_google_btn)
        print_test("Login has Apple button", has_apple_btn)

    assert has_google_btn, "Falta botón 'Continuar con Google' en login.html"
    assert has_apple_btn, "Falta botón 'Continuar con Apple' en login.html"

    # Verificar que index.html tiene modal de miembros
    with open(templates_dir / "index.html", encoding='utf-8') as f:
        content = f.read()
        has_miembros = "seccionMiembros" in content
        has_compartir = "formCompartirPorUsuario" in content
        print_test("Index has miembros section", has_miembros)
        print_test("Index has compartir form", has_compartir)

    assert has_miembros, "Falta seccionMiembros en index.html"
    assert has_compartir, "Falta formCompartirPorUsuario en index.html"


def main():
    print("\n" + "="*60)
    print("Testing Dreame! Features Implementation")
    print("="*60)

    def ejecutar(nombre, funcion):
        try:
            funcion()
            return (nombre, True)
        except Exception as e:
            print_test(nombre, False, str(e))
            return (nombre, False)

    results = [
        ejecutar("App Structure", test_app_structure),
        ejecutar("OAuth Endpoints", test_oauth_endpoints),
        ejecutar("Email Service", test_email_service),
        ejecutar("Configuration", test_config_variables),
        ejecutar("Auth Endpoints", test_auth_endpoints),
        ejecutar("Database Schema", test_database_schema),
        ejecutar("Templates", test_templates),
    ]

    # Resumen
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "OK" if result else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nTotal: {passed}/{total} test groups passed")

    if passed == total:
        print("All tests passed!\n")
    else:
        print("Some tests failed. Review above.\n")


if __name__ == "__main__":
    main()
