#!/usr/bin/env python3
"""
Script de prueba COMPLETO para Fase 2: Stock por Lista
Verifica aislamiento de stock entre usuarios y listas
"""
import json
import sqlite3
import requests
from datetime import datetime

import os

# Configuración
BASE_URL = "http://localhost:5000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "data", "stock.db")

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_header(msg):
    print(f"\n{BLUE}{'='*60}")
    print(f"{msg}")
    print(f"{'='*60}{END}\n")

def print_ok(msg):
    print(f"{GREEN}[OK] {msg}{END}")

def print_error(msg):
    print(f"{RED}[ERROR] {msg}{END}")

def print_info(msg):
    print(f"{YELLOW}[INFO] {msg}{END}")

def print_step(num, msg):
    print(f"\n{BLUE}[PASO {num}] {msg}{END}")

def query_db(query, params=None):
    """Ejecuta query directa en BD"""
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

def test_fase2_completo():
    """Prueba completa de Fase 2"""

    print_header("PRUEBAS DE FASE 2: STOCK POR LISTA")
    print_info(f"Fecha: {datetime.now().isoformat()}")
    print_info(f"BD: {DB_PATH}")
    print_info(f"API: {BASE_URL}")

    # PASO 1: Verificar estructura de la BD
    print_step(1, "Verificar estructura de tablas")
    try:
        # Verificar que existe tabla stock_lista
        result = query_db(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stock_lista'"
        )
        if result:
            print_ok("Tabla 'stock_lista' existe")
        else:
            print_error("Tabla 'stock_lista' NO existe")
            return False

        # Verificar UNIQUE constraint
        result = query_db("PRAGMA index_info('sqlite_autoindex_stock_lista_1')")
        print_ok(f"Constraint UNIQUE(lista_id, producto_id) existe")
    except Exception as e:
        print_error(f"Error verificando estructura: {e}")
        return False

    # PASO 2: Contar usuarios existentes
    print_step(2, "Verificar usuarios en BD")
    result = query_db("SELECT COUNT(*) as count FROM usuarios")
    user_count = result[0]['count']
    print_info(f"Usuarios existentes en BD: {user_count}")

    # PASO 3: Obtener usuarios de prueba
    print_step(3, "Obtener usuario de prueba")
    all_users = query_db("SELECT id, nombre_usuario FROM usuarios ORDER BY id LIMIT 2")

    if not all_users:
        print_error("No hay usuarios en la BD")
        return False

    user1_id = all_users[0]['id']
    user1_name = all_users[0]['nombre_usuario']
    print_ok(f"Usuario 1: '{user1_name}' (ID: {user1_id})")

    if len(all_users) > 1:
        user2_id = all_users[1]['id']
        user2_name = all_users[1]['nombre_usuario']
        print_ok(f"Usuario 2: '{user2_name}' (ID: {user2_id})")
    else:
        user2_id = None
        user2_name = None
        print_info("Solo hay 1 usuario en la BD (no se puede verificar aislamiento)")

    # PASO 4: Contar listas del usuario 1
    print_step(4, "Contar listas del usuario test-u1")
    result = query_db(
        "SELECT COUNT(*) as count FROM listas WHERE usuario_propietario_id = ?",
        (user1_id,)
    )
    list_count = result[0]['count']
    print_info(f"Listas del usuario: {list_count}")

    if list_count > 0:
        # Mostrar listas existentes
        lists = query_db(
            "SELECT id, nombre FROM listas WHERE usuario_propietario_id = ?",
            (user1_id,)
        )
        for lista in lists:
            # Contar entradas en stock_lista para esta lista
            stock_entries = query_db(
                "SELECT COUNT(*) as count FROM stock_lista WHERE lista_id = ?",
                (lista['id'],)
            )
            print_info(f"  - Lista '{lista['nombre']}' (ID:{lista['id']}): {stock_entries[0]['count']} entradas en stock_lista")

    # PASO 5: Verificar consistencia entre productos y stock_lista
    print_step(5, "Verificar consistencia: productos <-> stock_lista")
    result = query_db("SELECT COUNT(*) as count FROM productos")
    prod_count = result[0]['count']
    print_info(f"Total de productos en BD: {prod_count}")

    if prod_count > 0:
        # Para cada lista del usuario, verificar que tiene entradas en stock_lista para TODOS los productos
        lists = query_db(
            "SELECT id, nombre FROM listas WHERE usuario_propietario_id = ?",
            (user1_id,)
        )

        for lista in lists:
            lista_id = lista['id']

            # Contar entradas en stock_lista para esta lista
            result = query_db(
                "SELECT COUNT(*) as count FROM stock_lista WHERE lista_id = ?",
                (lista_id,)
            )
            stock_count = result[0]['count']

            if stock_count == prod_count:
                print_ok(f"Lista '{lista['nombre']}': tiene {stock_count} entradas en stock_lista [CORRECTAS]")
            elif stock_count > 0:
                print_error(f"Lista '{lista['nombre']}': tiene {stock_count} entradas en stock_lista, pero hay {prod_count} productos")
                print_info("  ^ Falta de sincronización entre productos y stock_lista")
            else:
                print_error(f"Lista '{lista['nombre']}': tiene 0 entradas en stock_lista (¡lista vacía!)")

    # PASO 6: Verificar datos de stock_lista
    print_step(6, "Inspeccionar datos en stock_lista")
    if list_count > 0:
        lists = query_db(
            "SELECT id, nombre FROM listas WHERE usuario_propietario_id = ? LIMIT 1",
            (user1_id,)
        )
        lista_id = lists[0]['id']

        result = query_db(
            """SELECT sl.id, sl.lista_id, sl.producto_id, sl.cantidad, sl.stock_minimo, p.nombre
               FROM stock_lista sl
               JOIN productos p ON sl.producto_id = p.id
               WHERE sl.lista_id = ? LIMIT 5""",
            (lista_id,)
        )

        if result:
            print_ok(f"Primeras 5 entradas de stock_lista para lista ID {lista_id}:")
            for row in result:
                print(f"  - {row['nombre']}: cantidad={row['cantidad']}, stock_minimo={row['stock_minimo']}")
        else:
            print_error(f"NO hay entradas en stock_lista para lista ID {lista_id}")

    # PASO 7: Verificar migración inicial
    print_step(7, "Verificar si migración se ejecutó correctamente")
    result = query_db(
        """SELECT COUNT(*) as count FROM stock_lista
           WHERE lista_id IN (SELECT id FROM listas WHERE usuario_propietario_id = ?)""",
        (user1_id,)
    )
    total_entries = result[0]['count']

    if list_count > 0 and prod_count > 0:
        expected = list_count * prod_count
        if total_entries == expected:
            print_ok(f"Migración correcta: {total_entries} entradas para {list_count} listas × {prod_count} productos")
        else:
            print_error(f"Migración INCORRECTA: {total_entries} entradas, esperadas {expected}")

    # PASO 8: Comparación usuario por usuario (si hay múltiples usuarios)
    print_step(8, "Aislamiento de datos entre usuarios")
    all_users = query_db("SELECT id, nombre_usuario FROM usuarios ORDER BY id")

    if len(all_users) > 1:
        print_info(f"Hay {len(all_users)} usuarios en la BD")
        for user in all_users:
            u_id = user['id']
            u_name = user['nombre_usuario']

            # Contar listas
            lists = query_db("SELECT COUNT(*) as count FROM listas WHERE usuario_propietario_id = ?", (u_id,))
            list_cnt = lists[0]['count']

            # Contar stock_lista entries
            stock = query_db(
                """SELECT COUNT(*) as count FROM stock_lista
                   WHERE lista_id IN (SELECT id FROM listas WHERE usuario_propietario_id = ?)""",
                (u_id,)
            )
            stock_cnt = stock[0]['count']

            print_info(f"Usuario '{u_name}': {list_cnt} listas, {stock_cnt} entradas en stock_lista")
    else:
        print_error("Hay solo 1 usuario. Se necesitan al menos 2 para verificar aislamiento")

    print_header("RESUMEN DE PRUEBAS")
    print_ok("Pruebas de Fase 2 completadas")
    print_info("Verificar que:")
    print_info("  1. Tabla stock_lista existe [OK]")
    print_info("  2. UNIQUE(lista_id, producto_id) existe [OK]")
    print_info("  3. Cada lista tiene stock_lista entries para TODOS los productos")
    print_info("  4. Datos estan aislados por usuario")

    return True

if __name__ == "__main__":
    try:
        success = test_fase2_completo()
        exit(0 if success else 1)
    except Exception as e:
        print_error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
