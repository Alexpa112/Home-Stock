"""Conexion a SQLite, migraciones del esquema y utilidades de fecha."""
import sqlite3
from datetime import datetime

from flask import g

from .config import CATALOGO_DEFECTO, CATEGORIAS_DEFECTO, DB_PATH, DIAS_AVISO_DEFECTO


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def asegurar_columna(db, tabla, columna, definicion):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna not in columnas:
        db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def quitar_columna_si_existe(db, tabla, columna):
    columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if columna in columnas:
        try:
            db.execute(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
        except sqlite3.OperationalError:
            pass  # Version de SQLite anterior a 3.35: se queda la columna, pero sin usarse.


# Mapeo de los emojis usados antes de la migración a iconos SVG (Lucide) a su
# nombre de icono equivalente. Debe coincidir con
# stockhogar/static/icons/mapeo-emoji-legacy.js (mismo propósito, lado JS).
MAPEO_EMOJI_A_ICONO_LUCIDE = {
    "🍎": "apple", "🍏": "apple", "🍌": "banana", "🍊": "citrus", "🍋": "citrus",
    "🍉": "cherry", "🍇": "grape", "🍓": "cherry", "🫐": "cherry", "🍒": "cherry",
    "🍑": "ice-cream", "🥭": "ice-cream", "🍍": "ice-cream", "🥝": "ice-cream",
    "🥑": "salad", "🍅": "carrot", "🥦": "salad", "🥬": "salad", "🥒": "salad",
    "🌶️": "carrot", "🫑": "carrot", "🌽": "carrot", "🥕": "carrot",
    "🧄": "sprout", "🧅": "sprout", "🥔": "sprout", "🍠": "sprout",
    "🥐": "croissant", "🥖": "wheat", "🍞": "wheat", "🧀": "wheat",
    "🥚": "egg", "🥩": "beef", "🍗": "drumstick", "🍖": "drumstick",
    "🥓": "sandwich", "🌭": "sandwich", "🍔": "sandwich", "🍕": "pizza",
    "🐟": "fish", "🦐": "fish-symbol", "🍱": "soup", "🍚": "soup", "🍜": "soup",
    "🥣": "container", "🥫": "container", "🫙": "package-2",
    "🍫": "candy-cane", "🍬": "candy", "🍩": "donut", "🍪": "cookie",
    "🎂": "cake", "🍯": "cake-slice", "🥜": "nut", "🧈": "wheat", "🧂": "container",
    "🫒": "droplet", "☕": "coffee", "🍵": "coffee", "🧃": "cup-soda",
    "🥤": "cup-soda", "🧋": "cup-soda", "🍶": "wine", "🍾": "wine",
    "🍷": "wine", "🍺": "beer", "🥛": "milk", "💧": "droplet",
    "🧴": "spray-can", "🧼": "spray-can", "🧽": "waves-ladder",
    "🪥": "shower-head", "🦷": "shower-head", "🧻": "toilet", "🧺": "waves-ladder",
    "🪣": "toilet", "🚽": "toilet", "🛁": "shower-head", "🚿": "shower-head",
    "🕯️": "flame", "🔥": "flame", "🧯": "flame-kindling",
    "💊": "pill", "🩹": "bandage", "🩺": "stethoscope", "🌡️": "thermometer",
    "👶": "baby", "🍼": "baby", "🧸": "toy-brick", "🐶": "dog", "🐱": "cat",
    "🐹": "paw-print", "🦴": "paw-print", "🐾": "paw-print",
    "👕": "shirt", "👖": "footprints", "🧦": "footprints", "🧣": "footprints",
    "🧤": "footprints", "👗": "shirt", "👟": "footprints", "🧥": "shirt",
    "🔧": "wrench", "🔩": "hammer", "🔨": "hammer", "🪛": "hammer", "🪜": "drill",
    "🖨️": "printer", "📱": "smartphone", "💻": "laptop", "🔌": "plug",
    "🔋": "battery", "💡": "lightbulb", "📷": "camera", "🎧": "headphones",
    "⌚": "watch", "🔦": "flashlight", "🗝️": "key", "📓": "notebook",
    "✏️": "pencil", "🖊️": "pencil", "📎": "paperclip", "✂️": "scissors",
    "📚": "book", "🌱": "sprout", "🪴": "flower", "🌻": "flower", "🍀": "clover",
    "🪵": "trees", "⚽": "volleyball", "🏀": "volleyball", "🚴": "bike",
    "🎮": "gamepad-2", "🎲": "dices", "🧩": "puzzle", "🚗": "car",
    "⛽": "fuel", "🎁": "gift", "🧳": "luggage", "🎈": "party-popper",
    "📦": "h-archive-box", "🛒": "h-shopping-cart", "🗂️": "h-folder",
    "🏠": "h-home", "📋": "h-clipboard-document-list",
    # Emojis adicionales usados en config.py (CATEGORIAS_DEFECTO/CATALOGO_DEFECTO)
    # que no estaban en el selector original de 144 iconos.
    "🍄": "salad", "🍆": "salad", "🍐": "apple", "🍈": "cherry", "🎃": "carrot",
    "🌰": "nut", "🫛": "salad", "🧁": "cake-slice", "🍮": "cake-slice",
    "🦃": "drumstick", "🦑": "fish-symbol", "🦪": "fish-symbol", "🐙": "fish-symbol",
    "🧊": "container", "🍦": "ice-cream", "🍟": "sandwich", "🥟": "soup",
    "🍰": "cake-slice", "🌾": "wheat", "🌿": "sprout", "🍿": "candy",
    "🍘": "cookie", "🥃": "wine", "🪒": "spray-can", "🍝": "soup",
    "🥞": "wheat", "🫓": "wheat", "🗑️": "h-trash", "😷": "stethoscope",
}


# Iconos que en un primer momento se asignaron a Lucide y luego se
# reasignaron a Heroicons (nombres "h-...") por preferencia visual.
RENOMBRES_ICONO = {
    "folder": "h-folder",
    "home": "h-home",
    "clipboard-list": "h-clipboard-document-list",
    "package": "h-archive-box",
    "shopping-cart": "h-shopping-cart",
    "trash-2": "h-trash",
}


def migrar_iconos_emoji_a_lucide(db):
    """Traduce los emojis guardados en columnas `icono` a su nombre de icono
    Lucide equivalente (ver MAPEO_EMOJI_A_ICONO_LUCIDE). Idempotente: tras la
    primera ejecución ya no quedan filas con emoji, por lo que reejecutarla en
    cada arranque es un no-op seguro."""
    tablas_con_icono = [
        "categorias", "productos", "listas", "espacios",
        "historial_articulos", "articulos_lista",
    ]
    for tabla in tablas_con_icono:
        columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
        if "icono" not in columnas:
            continue
        for emoji, nombre_lucide in MAPEO_EMOJI_A_ICONO_LUCIDE.items():
            db.execute(
                f"UPDATE {tabla} SET icono = ? WHERE icono = ?",
                (nombre_lucide, emoji),
            )
        # Renombrados posteriores: algunos conceptos "hogar/UI" pasaron de
        # Lucide a Heroicons (ver catalogo-iconos.js), así que filas ya
        # migradas al nombre Lucide antiguo se reasignan al nuevo nombre.
        for nombre_viejo, nombre_nuevo in RENOMBRES_ICONO.items():
            db.execute(
                f"UPDATE {tabla} SET icono = ? WHERE icono = ?",
                (nombre_nuevo, nombre_viejo),
            )


def _migrar_lista_compra_a_articulos(db, espacio_defecto_id):
    """
    Migra datos de la tabla antigua lista_compra a articulos_lista.

    Crea una lista 'por defecto' para cada usuario con sus artículos existentes.
    Esta función se ejecuta solo si encuentra la tabla antigua.
    """
    # Obtener todos los usuarios
    usuarios = db.execute("SELECT id, nombre_usuario FROM usuarios").fetchall()

    for usuario in usuarios:
        usuario_id = usuario["id"]
        nombre_usuario = usuario["nombre_usuario"]

        # Crear lista 'por defecto' para este usuario si no existe
        lista_existente = db.execute(
            "SELECT id FROM listas WHERE usuario_propietario_id = ? AND nombre = 'Mi lista'",
            (usuario_id,),
        ).fetchone()

        if not lista_existente:
            cur = db.execute(
                "INSERT INTO listas (nombre, descripcion, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion, icono) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("Mi lista", "Lista de compra principal", usuario_id, 1, ahora(), ahora(), "📋"),
            )
            lista_id = cur.lastrowid
        else:
            lista_id = lista_existente["id"]

        # Migrar artículos de lista_compra que pertenecían a este usuario/espacio
        # (Asumimos que todos los artículos sin usuario explícito son del primer usuario)
        if usuario_id == usuarios[0]["id"]:
            # Verificar qué columnas existen en la tabla antigua
            columnas_existentes = {
                col["name"] for col in db.execute(
                    "PRAGMA table_info(lista_compra)"
                ).fetchall()
            }

            # Construir el SELECT dinámicamente según las columnas disponibles
            campos = ["?", "producto_id", "nombre", "unidad"]

            if "categoria" in columnas_existentes:
                campos.append("COALESCE(categoria, 'Otros')")
            else:
                campos.append("'Otros'")

            if "icono" in columnas_existentes:
                campos.append("icono")
            else:
                campos.append("NULL")

            if "cantidad" in columnas_existentes:
                campos.append("COALESCE(cantidad, 1)")
            else:
                campos.append("1")

            if "sub_descripcion" in columnas_existentes:
                campos.append("sub_descripcion")
            else:
                campos.append("NULL")

            campos.append("origen")

            if "activo" in columnas_existentes:
                campos.append("COALESCE(activo, 1)")
            else:
                campos.append("1")

            if "fecha_completado" in columnas_existentes:
                campos.append("fecha_completado")
            else:
                campos.append("NULL")

            campos.append("?")  # fecha_creacion

            select_clause = f"SELECT {', '.join(campos)} FROM lista_compra"

            db.execute(
                f"""
                INSERT INTO articulos_lista
                (lista_id, producto_id, nombre, unidad, categoria, icono, cantidad,
                 sub_descripcion, origen, activo, fecha_completado, fecha_creacion)
                {select_clause}
                """,
                (lista_id, ahora()),
            )

    # Después de migrar, renombrar la tabla antigua para que no interfiera
    try:
        db.execute("ALTER TABLE lista_compra RENAME TO lista_compra_backup")
    except sqlite3.OperationalError:
        pass  # Si no se puede renombrar, simplemente continuar


def _reparar_fk_articulos_personalizados_old(db):
    """Corrige una instalación afectada por un bug de una migración previa: al
    renombrar articulos_personalizados a un nombre temporal, SQLite reescribió
    automáticamente la FK de articulos_lista para que apuntara a ese nombre
    temporal ("articulos_personalizados_old"), y se quedó rota al borrar la
    tabla vieja. No se puede arreglar con ALTER TABLE; se reescribe el texto
    del CREATE TABLE guardado en sqlite_master (autoreparable, no destructivo).
    """
    fila = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='articulos_lista'"
    ).fetchone()
    if not fila or "articulos_personalizados_old" not in fila["sql"]:
        return
    db.commit()
    db.execute("PRAGMA writable_schema = ON")
    db.execute(
        "UPDATE sqlite_master SET sql = REPLACE(sql, '\"articulos_personalizados_old\"', 'articulos_personalizados') "
        "WHERE type='table' AND name='articulos_lista'"
    )
    db.commit()
    db.execute("PRAGMA writable_schema = OFF")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    _reparar_fk_articulos_personalizados_old(db)

    # Tabla de usuarios (debe existir antes de crear listas, ya que las listas
    # tienen una relación con usuarios)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            fecha_creacion TEXT NOT NULL,
            email TEXT
        )
        """
    )
    asegurar_columna(db, "usuarios", "email", "TEXT")
    asegurar_columna(db, "usuarios", "idioma_preferido", "TEXT NOT NULL DEFAULT 'es'")

    # Tabla para cuentas OAuth (Google, Apple)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            proveedor TEXT NOT NULL CHECK (proveedor IN ('google', 'apple')),
            id_proveedor TEXT NOT NULL,
            email TEXT NOT NULL,
            nombre TEXT,
            foto_perfil TEXT,
            fecha_creacion TEXT NOT NULL,
            UNIQUE(proveedor, id_proveedor)
        )
        """
    )

    # Tabla listas: contenedor principal de artículos, similar a Bring!
    # Cada lista pertenece a un usuario (propietario) y puede compartirse
    # con otros usuarios mediante permisos_lista
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS listas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            privada INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "listas", "icono", "TEXT NOT NULL DEFAULT '📋'")
    asegurar_columna(db, "listas", "color", "TEXT NOT NULL DEFAULT '#B5551A'")

    # Tabla permisos_lista: relación usuario ↔ lista con niveles de acceso
    # niveles: 'ver' (solo lectura) o 'editar' (lectura + escritura)
    # El propietario tiene control total sin necesidad de estar aquí
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS permisos_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'editar')),
            fecha_otorgado TEXT NOT NULL,
            UNIQUE(lista_id, usuario_id)
        )
        """
    )

    # Tabla de invitaciones para compartir listas por email
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS invitaciones_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            email_destino TEXT NOT NULL,
            nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'editar')),
            codigo_invitacion TEXT NOT NULL UNIQUE,
            usado INTEGER NOT NULL DEFAULT 0,
            usuario_aceptacion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            fecha_creacion TEXT NOT NULL,
            fecha_expiracion TEXT NOT NULL,
            fecha_aceptacion TEXT
        )
        """
    )

    # Espacios: ahora son opcionales (podría usarse para categorizar listas después)
    # Se mantiene para compatibilidad hacia atrás
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS espacios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono TEXT NOT NULL DEFAULT '🏠',
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "espacios", "color", "TEXT NOT NULL DEFAULT '#B5551A'")
    if db.execute("SELECT COUNT(*) AS n FROM espacios").fetchone()["n"] == 0:
        db.execute(
            "INSERT INTO espacios (nombre, icono, color, fecha_creacion) VALUES (?, ?, ?, ?)",
            ("Mi casa", "🏠", "#B5551A", ahora()),
        )
    espacio_defecto_id = db.execute("SELECT id FROM espacios ORDER BY id LIMIT 1").fetchone()["id"]

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL DEFAULT 'Otros',
            cantidad INTEGER NOT NULL DEFAULT 0,
            unidad TEXT NOT NULL DEFAULT 'ud',
            stock_minimo INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    asegurar_columna(db, "productos", "fecha_creacion", "TEXT")
    asegurar_columna(db, "productos", "fecha_actualizacion", "TEXT")
    asegurar_columna(db, "productos", "dias_aviso", f"INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO}")
    asegurar_columna(db, "productos", "icono", "TEXT")
    asegurar_columna(db, "productos", "espacio_id", "INTEGER")
    # Rellena fechas de productos ya existentes que no las tuvieran (migraciones previas).
    db.execute("UPDATE productos SET fecha_creacion = ? WHERE fecha_creacion IS NULL", (ahora(),))
    db.execute("UPDATE productos SET fecha_actualizacion = ? WHERE fecha_actualizacion IS NULL", (ahora(),))
    db.execute("UPDATE productos SET espacio_id = ? WHERE espacio_id IS NULL", (espacio_defecto_id,))

    # Tabla articulos_lista: artículos dentro de cada lista
    # Migración: originalmente era lista_compra, ahora vinculada a listas
    # en lugar de espacios
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS articulos_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
            nombre TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT 'ud',
            categoria TEXT NOT NULL DEFAULT 'Otros',
            icono TEXT,
            cantidad INTEGER NOT NULL DEFAULT 1,
            sub_descripcion TEXT,
            origen TEXT NOT NULL DEFAULT 'manual',
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_completado TEXT,
            fecha_creacion TEXT
        )
        """
    )

    # Tabla stock_lista: NUEVA - stock POR LISTA, no global
    # Modelo B: cada lista tiene su propio stock independiente
    # Listas compartidas comparten las mismas filas de stock
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_lista (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_id INTEGER NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            cantidad INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT NOT NULL,
            UNIQUE(lista_id, producto_id)
        )
        """
    )

    # Migración de datos: si stock_lista está vacía, poblarla desde productos
    # Para cada lista del usuario, crear entrada de stock para todos los productos
    stock_count = db.execute("SELECT COUNT(*) AS n FROM stock_lista").fetchone()["n"]
    if stock_count == 0:
        listas = db.execute("SELECT id FROM listas").fetchall()
        productos = db.execute("SELECT id, cantidad, stock_minimo FROM productos").fetchall()

        for lista in listas:
            lista_id = lista["id"]
            for prod in productos:
                try:
                    db.execute(
                        """INSERT OR IGNORE INTO stock_lista
                           (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (lista_id, prod["id"], prod["cantidad"], prod["stock_minimo"], ahora(), ahora())
                    )
                except Exception as e:
                    # Ignorar errores de duplicados o constraints
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"[stock_lista migration] Ignorando error: {e}")

        db.commit()

    # Compatibilidad: si existe lista_compra antigua, no hacer nada por ahora
    # (se migrará después con la función _migrar_lista_compra_a_articulos)
    tabla_existe = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lista_compra'"
    ).fetchone()
    if tabla_existe:
        # Tabla antigua existe, es una instalación anterior
        _migrar_lista_compra_a_articulos(db, espacio_defecto_id)
    db.execute("DROP TABLE IF EXISTS ajustes")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono TEXT NOT NULL DEFAULT '🗂️'
        )
        """
    )
    db.executemany(
        "INSERT OR IGNORE INTO categorias (nombre, icono) VALUES (?, ?)",
        CATEGORIAS_DEFECTO,
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_articulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            espacio_id INTEGER REFERENCES espacios(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL COLLATE NOCASE,
            icono TEXT NOT NULL,
            categoria TEXT,
            unidad TEXT NOT NULL DEFAULT 'ud',
            sub_descripcion TEXT,
            cantidad_defecto INTEGER NOT NULL DEFAULT 1,
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )
    asegurar_columna(db, "historial_articulos", "unidad", "TEXT NOT NULL DEFAULT 'ud'")
    asegurar_columna(db, "historial_articulos", "sub_descripcion", "TEXT")
    asegurar_columna(db, "historial_articulos", "cantidad_defecto", "INTEGER NOT NULL DEFAULT 1")
    # espacio_id NULL = catálogo por defecto compartido (CATALOGO_DEFECTO); no NULL = aprendido
    # por ese espacio en concreto, y no debe filtrarse a otros espacios.
    asegurar_columna(db, "historial_articulos", "espacio_id", "INTEGER REFERENCES espacios(id) ON DELETE CASCADE")

    # Migración: el UNIQUE(nombre) original (una instalación antigua sin espacio_id) no
    # distingue espacios y bloquearía nombres repetidos entre espacios distintos. SQLite no
    # permite eliminar el índice autogenerado de un UNIQUE inline con DROP INDEX, así que
    # reconstruimos la tabla si detectamos ese índice.
    tiene_unique_antiguo = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND tbl_name='historial_articulos' "
        "AND name='sqlite_autoindex_historial_articulos_1'"
    ).fetchone()
    if tiene_unique_antiguo:
        db.execute("ALTER TABLE historial_articulos RENAME TO historial_articulos_old")
        db.execute(
            """
            CREATE TABLE historial_articulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espacio_id INTEGER REFERENCES espacios(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL COLLATE NOCASE,
                icono TEXT NOT NULL,
                categoria TEXT,
                unidad TEXT NOT NULL DEFAULT 'ud',
                sub_descripcion TEXT,
                cantidad_defecto INTEGER NOT NULL DEFAULT 1,
                fecha_actualizacion TEXT NOT NULL
            )
            """
        )
        db.execute(
            "INSERT INTO historial_articulos "
            "(espacio_id, nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
            "SELECT espacio_id, nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion "
            "FROM historial_articulos_old"
        )
        db.execute("DROP TABLE historial_articulos_old")

    # El UNIQUE ahora se aplica con dos índices parciales: uno para el catálogo global
    # (espacio_id NULL) y otro por espacio, en vez de un UNIQUE(nombre) global.
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_historial_global ON historial_articulos(nombre COLLATE NOCASE) "
        "WHERE espacio_id IS NULL"
    )
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_historial_espacio ON historial_articulos(espacio_id, nombre COLLATE NOCASE) "
        "WHERE espacio_id IS NOT NULL"
    )

    # Tabla articulos_personalizados: artículos únicos de cada cliente/espacio
    # NO se comparten entre clientes, disponibles en múltiples listas del mismo espacio
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS articulos_personalizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            espacio_id INTEGER NOT NULL REFERENCES espacios(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL COLLATE NOCASE,
            categoria TEXT NOT NULL DEFAULT 'Otros',
            icono TEXT,
            unidad TEXT NOT NULL DEFAULT 'ud',
            sub_descripcion TEXT,
            cantidad_defecto INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT,
            UNIQUE(espacio_id, nombre)
        )
        """
    )
    asegurar_columna(db, "articulos_personalizados", "fecha_creacion", "TEXT")
    asegurar_columna(db, "articulos_personalizados", "fecha_actualizacion", "TEXT")

    # Migración: el UNIQUE(espacio_id, nombre) original era sensible a mayúsculas (la
    # columna no tenía COLLATE NOCASE), aunque las búsquedas de la app sí usan
    # COLLATE NOCASE. Bajo concurrencia esto permitía crear duplicados tipo "Leche"/"leche".
    # SQLite no permite cambiar la colación de una columna con ALTER TABLE, así que
    # reconstruimos la tabla, fusionando duplicados case-insensitive si los hubiera.
    sql_actual = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='articulos_personalizados'"
    ).fetchone()
    if sql_actual and "COLLATE NOCASE" not in sql_actual["sql"]:
        # OJO: articulos_lista.articulo_personalizado_id tiene una FK hacia esta tabla.
        # Si la renombrásemos primero (RENAME TO ..._old), SQLite reescribe automáticamente
        # esa FK para que apunte al nombre temporal, y se queda rota al borrar la tabla vieja.
        # Seguimos el procedimiento oficial de SQLite: creamos la tabla nueva con un nombre
        # temporal, copiamos los datos, borramos la tabla vieja (con su nombre original) y
        # solo al final renombramos la nueva a ese mismo nombre original; así la FK de
        # articulos_lista (que nunca cambia de texto) sigue resolviendo correctamente.
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            """
            CREATE TABLE articulos_personalizados_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espacio_id INTEGER NOT NULL REFERENCES espacios(id) ON DELETE CASCADE,
                nombre TEXT NOT NULL COLLATE NOCASE,
                categoria TEXT NOT NULL DEFAULT 'Otros',
                icono TEXT,
                unidad TEXT NOT NULL DEFAULT 'ud',
                sub_descripcion TEXT,
                cantidad_defecto INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT,
                fecha_actualizacion TEXT,
                UNIQUE(espacio_id, nombre)
            )
            """
        )
        # Por cada (espacio_id, nombre case-insensitive) nos quedamos con el id más antiguo.
        db.execute(
            "INSERT INTO articulos_personalizados_new "
            "(id, espacio_id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
            "fecha_creacion, fecha_actualizacion) "
            "SELECT id, espacio_id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
            "fecha_creacion, fecha_actualizacion FROM articulos_personalizados o "
            "WHERE o.id = (SELECT MIN(id) FROM articulos_personalizados "
            "WHERE espacio_id = o.espacio_id AND nombre = o.nombre COLLATE NOCASE)"
        )
        # Repuntar los artículos de lista que apuntaban a un duplicado descartado hacia el
        # id que sobrevivió, para no perderlos por el ON DELETE CASCADE al borrar la tabla vieja.
        db.execute(
            "UPDATE articulos_lista SET articulo_personalizado_id = ("
            "  SELECT MIN(o2.id) FROM articulos_personalizados o2, articulos_personalizados o1 "
            "  WHERE o1.id = articulos_lista.articulo_personalizado_id "
            "  AND o2.espacio_id = o1.espacio_id AND o2.nombre = o1.nombre COLLATE NOCASE"
            ") "
            "WHERE articulo_personalizado_id IS NOT NULL"
        )
        db.execute("DROP TABLE articulos_personalizados")
        db.execute("ALTER TABLE articulos_personalizados_new RENAME TO articulos_personalizados")
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

    # Actualizar articulos_lista para vincular artículos personalizados
    asegurar_columna(db, "articulos_lista", "articulo_personalizado_id", "INTEGER REFERENCES articulos_personalizados(id) ON DELETE CASCADE")

    # Tabla traducciones_productos: almacena traducciones de nombres y descripciones
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS traducciones_productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            articulo_id INTEGER REFERENCES articulos_lista(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,
            idioma TEXT NOT NULL,
            texto_original TEXT NOT NULL,
            texto_traducido TEXT NOT NULL,
            fecha_creacion TEXT,
            UNIQUE(producto_id, articulo_id, tipo, idioma)
        )
        """
    )
    asegurar_columna(db, "traducciones_productos", "fecha_creacion", "TEXT")

    # Tabla movimientos_stock: auditoria de cambios de cantidad, para poder
    # consultar el historial de un producto y graficar consumo por periodo.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS movimientos_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            lista_id INTEGER REFERENCES listas(id) ON DELETE SET NULL,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            delta INTEGER NOT NULL,
            cantidad_resultante INTEGER NOT NULL,
            origen TEXT NOT NULL DEFAULT 'ajuste',
            fecha TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimientos_stock_producto_fecha "
        "ON movimientos_stock(producto_id, fecha)"
    )

    # Catalogo de productos habituales de supermercado (ver config.py): se
    # siembra una vez via INSERT OR IGNORE, asi que nunca pisa un articulo
    # que el usuario ya haya personalizado con el mismo nombre.
    db.executemany(
        "INSERT OR IGNORE INTO historial_articulos "
        "(nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, ?, 1, ?)",
        [(n, c, i, u, s, ahora()) for (n, c, i, u, s) in CATALOGO_DEFECTO],
    )

    migrar_iconos_emoji_a_lucide(db)

    db.commit()
    db.close()
