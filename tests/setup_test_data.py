#!/usr/bin/env python3
"""
Setup datos de prueba para validar Fase 2 y 3
Crea usuarios, listas y productos directamente en BD
"""
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "stock.db")

def ahora():
    return datetime.now().isoformat(timespec="seconds")

def hash_password(password):
    """Mismo hash que usa la app real (stockhogar/rutas/auth.py)."""
    return generate_password_hash(password)

def setup_test_data():
    """Crea datos de prueba"""
    print("\n" + "="*60)
    print("Setup: Crear datos de prueba para Fase 2/3")
    print("="*60 + "\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Crear Usuario 1
    print("[1] Crear Usuario 1: 'test-user-1'")
    cur.execute(
        """INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion, idioma_preferido)
           VALUES (?, ?, ?, ?, ?)""",
        ("test-user-1", hash_password("TestPass123"), "user1@test.com", ahora(), "es")
    )
    user1_id = cur.lastrowid
    print(f"    ID: {user1_id}")

    # Crear Usuario 2
    print("\n[2] Crear Usuario 2: 'test-user-2'")
    cur.execute(
        """INSERT INTO usuarios (nombre_usuario, password_hash, email, fecha_creacion, idioma_preferido)
           VALUES (?, ?, ?, ?, ?)""",
        ("test-user-2", hash_password("TestPass123"), "user2@test.com", ahora(), "es")
    )
    user2_id = cur.lastrowid
    print(f"    ID: {user2_id}")

    # Crear Producto 1
    print("\n[3] Crear Producto 1: 'Leche'")
    cur.execute(
        """INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo,
                                   dias_aviso, icono, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Leche", "Lácteos y Huevos", 5, "L", 2, 30, "🥛", ahora(), ahora())
    )
    prod1_id = cur.lastrowid
    print(f"    ID: {prod1_id}, cantidad=5, stock_minimo=2")

    # Crear Producto 2
    print("\n[4] Crear Producto 2: 'Pan'")
    cur.execute(
        """INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo,
                                   dias_aviso, icono, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Pan", "Panadería y Bollería", 3, "piezas", 1, 30, "🥖", ahora(), ahora())
    )
    prod2_id = cur.lastrowid
    print(f"    ID: {prod2_id}, cantidad=3, stock_minimo=1")

    # Crear Lista 1 para Usuario 1
    print("\n[5] Crear Lista 1 (Usuario 1): 'Cocina'")
    cur.execute(
        """INSERT INTO listas (nombre, descripcion, usuario_propietario_id, privada, icono, color,
                               fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Cocina", "Lista de cocina", user1_id, 1, "🍳", "#FF6B35", ahora(), ahora())
    )
    lista1_id = cur.lastrowid
    print(f"    ID: {lista1_id} para Usuario {user1_id}")

    # Crear entrada en stock_lista para Lista 1 × Producto 1
    print(f"\n[6] Poblar stock_lista para Lista 1")
    cur.execute(
        """INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (lista1_id, prod1_id, 5, 2, ahora(), ahora())
    )
    print(f"    - Leche: cantidad=5, stock_minimo=2")

    cur.execute(
        """INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (lista1_id, prod2_id, 3, 1, ahora(), ahora())
    )
    print(f"    - Pan: cantidad=3, stock_minimo=1")

    # Crear Lista 2 para Usuario 2
    print("\n[7] Crear Lista 2 (Usuario 2): 'Bano'")
    cur.execute(
        """INSERT INTO listas (nombre, descripcion, usuario_propietario_id, privada, icono, color,
                               fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Bano", "Lista de bano", user2_id, 1, "🧼", "#4ECDC4", ahora(), ahora())
    )
    lista2_id = cur.lastrowid
    print(f"    ID: {lista2_id} para Usuario {user2_id}")

    # Crear entradas en stock_lista para Lista 2
    print(f"\n[8] Poblar stock_lista para Lista 2")
    cur.execute(
        """INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (lista2_id, prod1_id, 5, 2, ahora(), ahora())
    )
    print(f"    - Leche: cantidad=5, stock_minimo=2")

    cur.execute(
        """INSERT INTO stock_lista (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (lista2_id, prod2_id, 3, 1, ahora(), ahora())
    )
    print(f"    - Pan: cantidad=3, stock_minimo=1")

    conn.commit()
    conn.close()

    print("\n" + "="*60)
    print("[RESUMEN]")
    print(f"  Usuarios: 2 (User1:ID{user1_id}, User2:ID{user2_id})")
    print(f"  Productos: 2 (Leche:ID{prod1_id}, Pan:ID{prod2_id})")
    print(f"  Listas: 2 (Lista1:ID{lista1_id} User1, Lista2:ID{lista2_id} User2)")
    print(f"  stock_lista entries: 4 (2 listas × 2 productos)")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        setup_test_data()
        print("[OK] Datos de prueba creados")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
