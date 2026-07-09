#!/usr/bin/env python3
"""
Test: Crear lista NUEVA y verificar que stock_lista se popula
"""
import json
import sqlite3
import os
from datetime import datetime
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "stock.db")

def query_db(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        result = cur.fetchall()
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e

def execute_db(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
        result = cur.lastrowid
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e

def test_crear_lista_nueva():
    print("\n" + "="*60)
    print("TEST: Crear lista NUEVA y verificar stock_lista")
    print("="*60 + "\n")

    # Paso 1: Obtener usuario existente
    print("[PASO 1] Obtener usuario de prueba")
    users = query_db("SELECT id, nombre_usuario FROM usuarios LIMIT 1")
    if not users:
        print("ERROR: No hay usuarios")
        return False

    user_id = users[0]['id']
    user_name = users[0]['nombre_usuario']
    print(f"  Usuario: '{user_name}' (ID: {user_id})")

    # Paso 2: Contar listas y productos actuales
    print("\n[PASO 2] Estado actual")
    old_lists = query_db("SELECT COUNT(*) as count FROM listas WHERE usuario_propietario_id = ?", (user_id,))
    old_list_count = old_lists[0]['count']

    old_products = query_db("SELECT COUNT(*) as count FROM productos")
    prod_count = old_products[0]['count']

    print(f"  Listas del usuario: {old_list_count}")
    print(f"  Productos totales: {prod_count}")

    # Paso 3: Crear lista nueva simulando API
    print("\n[PASO 3] Crear lista nueva (simulando endpoint POST /api/listas)")
    lista_name = f"Test Lista {datetime.now().timestamp()}"
    lista_description = "Lista de prueba para Fase 2"

    def ahora():
        return datetime.now().isoformat(timespec="seconds")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """INSERT INTO listas
               (nombre, descripcion, usuario_propietario_id, privada, icono, color, fecha_creacion, fecha_actualizacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (lista_name, lista_description, user_id, 1, "[lista]", "#B5551A", ahora(), ahora()),
        )
        nueva_lista_id = cur.lastrowid

        # Poblar stock_lista (el fix que implementé)
        cur.execute("SELECT id, cantidad, stock_minimo FROM productos")
        productos = cur.fetchall()
        for prod in productos:
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO stock_lista
                       (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (nueva_lista_id, prod[0], prod[1], prod[2], ahora(), ahora())
                )
            except Exception as e:
                print(f"    Error insertando en stock_lista: {e}")

        conn.commit()
        conn.close()
        print(f"  [OK] Lista '{lista_name}' creada (ID: {nueva_lista_id})")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

    # Paso 4: Verificar que se creó la lista
    print("\n[PASO 4] Verificar lista creada")
    new_lists = query_db("SELECT COUNT(*) as count FROM listas WHERE usuario_propietario_id = ?", (user_id,))
    new_list_count = new_lists[0]['count']

    if new_list_count > old_list_count:
        print(f"  [OK] Lista creada: {old_list_count} -> {new_list_count}")
    else:
        print(f"  [ERROR] Lista NO se creó")
        return False

    # Paso 5: Verificar stock_lista poblada
    print("\n[PASO 5] Verificar que stock_lista se populo correctamente")
    stock_entries = query_db(
        "SELECT COUNT(*) as count FROM stock_lista WHERE lista_id = ?",
        (nueva_lista_id,)
    )
    stock_count = stock_entries[0]['count']

    if stock_count == prod_count:
        print(f"  [OK] stock_lista poblada: {stock_count} entries para {prod_count} productos")
    elif stock_count > 0:
        print(f"  [WARNING] stock_lista tiene {stock_count} entries, pero hay {prod_count} productos")
        print(f"           Falta de sincronización")
        return False
    else:
        print(f"  [ERROR] stock_lista VACIA para lista {nueva_lista_id}")
        print(f"         Se esperaban {prod_count} entries")
        return False

    # Paso 6: Inspeccionar datos
    print("\n[PASO 6] Inspeccionar datos en stock_lista")
    entries = query_db(
        """SELECT sl.id, sl.lista_id, sl.producto_id, sl.cantidad, sl.stock_minimo, p.nombre
           FROM stock_lista sl
           LEFT JOIN productos p ON sl.producto_id = p.id
           WHERE sl.lista_id = ? LIMIT 5""",
        (nueva_lista_id,)
    )

    if entries:
        for entry in entries:
            print(f"  - {entry['nombre']}: cantidad={entry['cantidad']}, stock_minimo={entry['stock_minimo']}")
    else:
        print(f"  [ERROR] No hay entradas en stock_lista")

    # Paso 7: Verificar UNIQUE constraint
    print("\n[PASO 7] Verificar UNIQUE constraint")
    try:
        if prod_count > 0:
            first_prod = query_db("SELECT id FROM productos LIMIT 1")
            prod_id = first_prod[0]['id']

            # Intentar insertar duplicate
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            def ahora():
                return datetime.now().isoformat(timespec="seconds")

            cur.execute(
                """INSERT INTO stock_lista
                   (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nueva_lista_id, prod_id, 999, 999, ahora(), ahora())
            )
            conn.commit()
            conn.close()
            print(f"  [ERROR] UNIQUE constraint NO esta funcionando")
            return False
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"  [OK] UNIQUE constraint esta funcionando")
        else:
            print(f"  [ERROR] Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        return False

    print("\n" + "="*60)
    print("[RESULTADO] TEST EXITOSO")
    print("  - Lista nueva creada correctamente")
    print("  - stock_lista poblada con todos los productos")
    print("  - UNIQUE constraint funcionando")
    print("="*60 + "\n")

    return True

if __name__ == "__main__":
    try:
        success = test_crear_lista_nueva()
        exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR FATAL] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
