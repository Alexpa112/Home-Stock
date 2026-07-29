"""Conexion a SQLite, migraciones del esquema y utilidades de fecha."""
import sqlite3
from datetime import datetime

from flask import g

from .config import CATALOGO_DEFECTO, CATEGORIAS_DEFECTO, DB_PATH, DIAS_AVISO_DEFECTO

try:
    import fcntl  # No disponible en Windows; solo se usa en el contenedor Linux.
except ImportError:
    fcntl = None


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        # WAL + synchronous=NORMAL: en la SD de la Raspberry Pi el modo por
        # defecto (rollback journal + synchronous=FULL) hace un fsync costoso
        # en cada commit y bloquea lectores mientras hay una escritura.
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA synchronous = NORMAL")
        # Si otra conexion tiene una escritura en curso, esperar hasta 5s en
        # vez de fallar al instante con "database is locked" (relevante sobre
        # todo bajo tests, que abren/cierran conexiones muy seguido contra el
        # mismo fichero).
        g.db.execute("PRAGMA busy_timeout = 5000")
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
        "categorias", "productos", "listas",
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


def _migrar_lista_compra_a_articulos(db):
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


def _renombrar_categoria(db, nombre_viejo, nombre_nuevo):
    """Renombra una categoria ya sembrada (p.ej. correccion de un typo en
    CATEGORIAS_DEFECTO) y actualiza el texto libre 'categoria' en las tablas
    que lo guardan por nombre en vez de por FK."""
    vieja = db.execute("SELECT id FROM categorias WHERE nombre = ?", (nombre_viejo,)).fetchone()
    if vieja is None:
        return

    nueva = db.execute("SELECT id FROM categorias WHERE nombre = ?", (nombre_nuevo,)).fetchone()
    if nueva is None:
        db.execute("UPDATE categorias SET nombre = ? WHERE id = ?", (nombre_nuevo, vieja["id"]))
    else:
        db.execute("DELETE FROM categorias WHERE id = ?", (vieja["id"],))

    for tabla in ("productos", "articulos_lista", "historial_articulos", "articulos_personalizados"):
        db.execute(f"UPDATE {tabla} SET categoria = ? WHERE categoria = ?", (nombre_nuevo, nombre_viejo))


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
    """Ejecuta las migraciones protegidas por un flock sobre un fichero aparte.

    gunicorn arranca --workers 2 (procesos separados, ver el CMD de
    Dockerfile.raspbian) y cada uno llama a create_app() -> init_db() al
    bootear. Sin este lock, los dos ejecutan las mismas sentencias
    'ALTER TABLE ... ADD COLUMN' casi a la vez contra el mismo fichero
    SQLite; aunque hay un PRAGMA busy_timeout, se ha visto en produccion
    (2026-07-29) que la sucesion de varias ALTER TABLE seguidas puede agotar
    igualmente el timeout con "database is locked", tumbando el worker y
    disparando el rollback automatico del deploy. Con el flock, el segundo
    worker simplemente espera a que el primero termine las migraciones antes
    de arrancar las suyas (que entonces son no-ops, las columnas ya existen).
    """
    if fcntl is None:
        _init_db_impl()
        return
    lock_path = DB_PATH.parent / ".init_db.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            _init_db_impl()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _init_db_impl():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 5000")
    # Si una migracion falla a mitad (p.ej. contencion transitoria bajo
    # tests que comparten el mismo fichero SQLite), el try/finally
    # garantiza que esta conexion se cierra igualmente: sin esto, una
    # unica fila fallida dejaba la conexion abierta para siempre,
    # bloqueando con "database is locked" TODAS las llamadas
    # posteriores a init_db() (cada test que llama a create_app()).
    try:
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
        asegurar_columna(db, "usuarios", "tema_preferido", "TEXT NOT NULL DEFAULT 'auto'")
        asegurar_columna(db, "usuarios", "teclado_virtual_activo", "TEXT NOT NULL DEFAULT 'on'")
        asegurar_columna(db, "usuarios", "vista_lista_compra", "TEXT NOT NULL DEFAULT 'lista'")
        asegurar_columna(db, "usuarios", "agrupar_categorias", "TEXT NOT NULL DEFAULT 'off'")
        asegurar_columna(db, "usuarios", "doble_factor_activo", "INTEGER NOT NULL DEFAULT 0")

        # Codigos de verificacion en dos pasos (login por email + codigo).
        # Una fila por usuario (se sobrescribe en cada intento de login, no
        # hace falta historial). En tabla en vez de en memoria porque gunicorn
        # corre 2 workers (procesos separados, ver Dockerfile.raspbian): un
        # dict en memoria dejaria el codigo solo visible para el worker que
        # lo genero, y la peticion de verificacion podria caer en el otro.
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS codigos_dos_factor (
                usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
                codigo_hash TEXT NOT NULL,
                expira INTEGER NOT NULL,
                intentos INTEGER NOT NULL DEFAULT 0
            )
            """
        )

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
        # Rellena fechas de productos ya existentes que no las tuvieran (migraciones previas).
        db.execute("UPDATE productos SET fecha_creacion = ? WHERE fecha_creacion IS NULL", (ahora(),))
        db.execute("UPDATE productos SET fecha_actualizacion = ? WHERE fecha_actualizacion IS NULL", (ahora(),))
        quitar_columna_si_existe(db, "productos", "espacio_id")

        # Tabla articulos_lista: artículos dentro de cada lista
        # Migración: originalmente era lista_compra, ahora vinculada a listas
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
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_articulos_lista_lista_id ON articulos_lista(lista_id, activo)"
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
        #
        # NOTA: esto siembra CADA lista existente con TODOS los productos del
        # catálogo (que en el modelo antiguo, previo a stock_lista, no tenía
        # ninguna columna de propietario: cantidad/stock_minimo vivían
        # directamente en `productos`, compartidos por toda la instalación).
        # No hay forma de inferir retroactivamente "de quién" era cada
        # producto porque esa distinción nunca existió antes de esta
        # migración; sembrar todas las listas con el valor que ya era visible
        # para todos preserva los datos existentes en la actualización, no
        # crea una fuga nueva. Es un puente de una sola vez (solo corre si
        # stock_lista está vacía): a partir de aquí cada fila de stock_lista
        # es independiente por lista, que es lo que realmente aísla el stock.
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
            _migrar_lista_compra_a_articulos(db)
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

        # Migración: instalaciones que aún tengan la columna espacio_id (de cuando existían
        # "espacios" como stocks independientes, funcionalidad eliminada por no tener UI y
        # estar ya cubierta por "listas") se consolidan a un catálogo global único por nombre.
        # Antes de borrar la columna, fusionamos duplicados nombre-case-insensitive quedándonos
        # con la fila "aprendida" (espacio_id NOT NULL, la más reciente/específica) si existe,
        # o si no con la fila del catálogo por defecto (espacio_id NULL).
        columnas_historial = [f["name"] for f in db.execute("PRAGMA table_info(historial_articulos)").fetchall()]
        if "espacio_id" in columnas_historial:
            db.execute(
                "DELETE FROM historial_articulos WHERE id NOT IN ("
                "  SELECT ("
                "    SELECT h2.id FROM historial_articulos h2"
                "    WHERE h2.nombre = h1.nombre COLLATE NOCASE"
                "    ORDER BY h2.espacio_id IS NULL ASC, h2.id ASC LIMIT 1"
                "  )"
                "  FROM historial_articulos h1"
                "  GROUP BY h1.nombre COLLATE NOCASE"
                ")"
            )
            db.execute("DROP INDEX IF EXISTS idx_historial_global")
            db.execute("DROP INDEX IF EXISTS idx_historial_espacio")
            quitar_columna_si_existe(db, "historial_articulos", "espacio_id")

        # UNIQUE(nombre) global: ya no hay espacios entre los que distinguir.
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_historial_nombre ON historial_articulos(nombre COLLATE NOCASE)"
        )

        # Tabla articulos_personalizados: artículos únicos del catálogo de cada
        # usuario/hogar (usuario_propietario_id), NO se comparten entre hogares,
        # disponibles en múltiples listas del mismo hogar.
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS articulos_personalizados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL COLLATE NOCASE,
                categoria TEXT NOT NULL DEFAULT 'Otros',
                icono TEXT,
                unidad TEXT NOT NULL DEFAULT 'ud',
                sub_descripcion TEXT,
                cantidad_defecto INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT,
                fecha_actualizacion TEXT,
                usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id),
                UNIQUE(nombre, usuario_propietario_id)
            )
            """
        )
        asegurar_columna(db, "articulos_personalizados", "fecha_creacion", "TEXT")
        asegurar_columna(db, "articulos_personalizados", "fecha_actualizacion", "TEXT")

        # Migración: instalaciones antiguas tenían la columna espacio_id (funcionalidad de
        # "espacios" ya eliminada, ver historial_articulos más arriba) y/o un UNIQUE
        # sensible a mayúsculas (sin COLLATE NOCASE), aunque las búsquedas de la app sí usan
        # COLLATE NOCASE; bajo concurrencia eso permitía duplicados tipo "Leche"/"leche".
        # SQLite no permite quitar una columna de un UNIQUE ni cambiar la colación con
        # ALTER TABLE, así que reconstruimos la tabla, fusionando duplicados si los hubiera.
        sql_actual = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='articulos_personalizados'"
        ).fetchone()
        if sql_actual and ("espacio_id" in sql_actual["sql"] or "COLLATE NOCASE" not in sql_actual["sql"]):
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
                    nombre TEXT NOT NULL COLLATE NOCASE,
                    categoria TEXT NOT NULL DEFAULT 'Otros',
                    icono TEXT,
                    unidad TEXT NOT NULL DEFAULT 'ud',
                    sub_descripcion TEXT,
                    cantidad_defecto INTEGER NOT NULL DEFAULT 1,
                    fecha_creacion TEXT,
                    fecha_actualizacion TEXT,
                    UNIQUE(nombre)
                )
                """
            )
            # Por cada nombre case-insensitive (antes distinguido también por espacio_id, ya
            # eliminado) nos quedamos con el id más antiguo.
            db.execute(
                "INSERT INTO articulos_personalizados_new "
                "(id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
                "fecha_creacion, fecha_actualizacion) "
                "SELECT id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
                "fecha_creacion, fecha_actualizacion FROM articulos_personalizados o "
                "WHERE o.id = (SELECT MIN(id) FROM articulos_personalizados "
                "WHERE nombre = o.nombre COLLATE NOCASE)"
            )
            # Repuntar los artículos de lista que apuntaban a un duplicado descartado hacia el
            # id que sobrevivió, para no perderlos por el ON DELETE CASCADE al borrar la tabla vieja.
            db.execute(
                "UPDATE articulos_lista SET articulo_personalizado_id = ("
                "  SELECT MIN(o2.id) FROM articulos_personalizados o2, articulos_personalizados o1 "
                "  WHERE o1.id = articulos_lista.articulo_personalizado_id "
                "  AND o2.nombre = o1.nombre COLLATE NOCASE"
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
        # articulo_personalizado_id es distinto de articulo_id: articulo_id referencia
        # articulos_lista(id) (traduccion de un item concreto de una lista), mientras que
        # articulo_personalizado_id referencia articulos_personalizados(id) (traduccion del
        # articulo reutilizable del catalogo personal, compartida por todas las listas).
        asegurar_columna(
            db, "traducciones_productos", "articulo_personalizado_id",
            "INTEGER REFERENCES articulos_personalizados(id) ON DELETE CASCADE"
        )

        # Migración: articulos_personalizados se deduplicaba por nombre a nivel de
        # TODA la instalación, sin ninguna columna de propietario (pese a que el
        # comentario original de la tabla decía "no se comparten entre clientes").
        # Dos hogares no relacionados con un artículo del mismo nombre (p.ej.
        # "Leche") acababan compartiendo la misma fila: cualquiera podía
        # renombrarla, cambiarle el icono/categoría o borrarla, afectando al otro
        # hogar. Añadimos usuario_propietario_id (el dueño de alguna de las listas
        # que referencian el artículo) y cambiamos el UNIQUE a
        # (nombre, usuario_propietario_id) para que cada hogar tenga su propio
        # catálogo aislado, igual que ya ocurre con las listas y el stock.
        sql_actual = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='articulos_personalizados'"
        ).fetchone()
        if sql_actual and "usuario_propietario_id" not in sql_actual["sql"]:
            # 1) Backfill: para cada fila, averiguar qué usuarios son dueños de
            # las listas que la referencian. Primero se añade la columna (sin
            # NOT NULL todavía, para poder rellenarla fila a fila antes de
            # reconstruir la tabla con la restricción definitiva).
            asegurar_columna(db, "articulos_personalizados", "usuario_propietario_id", "INTEGER")
            filas = db.execute("SELECT id FROM articulos_personalizados").fetchall()
            for fila in filas:
                articulo_id = fila["id"]
                propietarios = db.execute(
                    """SELECT DISTINCT l.usuario_propietario_id AS propietario_id,
                              MIN(al.id) AS primera_referencia
                       FROM articulos_lista al, listas l
                       WHERE al.articulo_personalizado_id = ? AND al.lista_id = l.id
                       GROUP BY l.usuario_propietario_id""",
                    (articulo_id,)
                ).fetchall()

                if not propietarios:
                    # Huérfano: ninguna lista lo referencia, es inalcanzable desde
                    # cualquier endpoint. Se limpia junto con sus traducciones.
                    db.execute(
                        "DELETE FROM traducciones_productos WHERE articulo_personalizado_id = ?",
                        (articulo_id,)
                    )
                    db.execute("DELETE FROM articulos_personalizados WHERE id = ?", (articulo_id,))
                    continue

                propietarios_ordenados = sorted(propietarios, key=lambda p: p["primera_referencia"])
                propietario_original = propietarios_ordenados[0]["propietario_id"]
                db.execute(
                    "UPDATE articulos_personalizados SET usuario_propietario_id = ? WHERE id = ?",
                    (propietario_original, articulo_id)
                )

                # Para cada propietario adicional (el caso realmente roto: varios
                # hogares compartiendo la misma fila), clonar el artículo y
                # repuntar sus referencias y traducciones al nuevo id.
                original = db.execute(
                    "SELECT * FROM articulos_personalizados WHERE id = ?", (articulo_id,)
                ).fetchone()
                for extra in propietarios_ordenados[1:]:
                    propietario_extra = extra["propietario_id"]
                    cur = db.execute(
                        """INSERT INTO articulos_personalizados
                           (nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto,
                            fecha_creacion, fecha_actualizacion, usuario_propietario_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (original["nombre"], original["categoria"], original["icono"], original["unidad"],
                         original["sub_descripcion"], original["cantidad_defecto"], original["fecha_creacion"],
                         original["fecha_actualizacion"], propietario_extra)
                    )
                    nuevo_id = cur.lastrowid

                    db.execute(
                        """UPDATE articulos_lista SET articulo_personalizado_id = ?
                           WHERE articulo_personalizado_id = ? AND lista_id IN (
                               SELECT id FROM listas WHERE usuario_propietario_id = ?
                           )""",
                        (nuevo_id, articulo_id, propietario_extra)
                    )

                    for trad in db.execute(
                        "SELECT tipo, idioma, texto_original, texto_traducido FROM traducciones_productos "
                        "WHERE articulo_personalizado_id = ?",
                        (articulo_id,)
                    ).fetchall():
                        db.execute(
                            """INSERT INTO traducciones_productos
                               (articulo_personalizado_id, tipo, idioma, texto_original, texto_traducido, fecha_creacion)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (nuevo_id, trad["tipo"], trad["idioma"], trad["texto_original"],
                             trad["texto_traducido"], ahora())
                        )

            # 2) Reconstruir la tabla con la columna NOT NULL y el nuevo UNIQUE
            # (mismo procedimiento que la migración de espacio_id de más arriba:
            # nombre temporal + DROP de la vieja + RENAME, para no romper la FK
            # de articulos_lista).
            db.commit()
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute(
                """
                CREATE TABLE articulos_personalizados_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL COLLATE NOCASE,
                    categoria TEXT NOT NULL DEFAULT 'Otros',
                    icono TEXT,
                    unidad TEXT NOT NULL DEFAULT 'ud',
                    sub_descripcion TEXT,
                    cantidad_defecto INTEGER NOT NULL DEFAULT 1,
                    fecha_creacion TEXT,
                    fecha_actualizacion TEXT,
                    usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id),
                    UNIQUE(nombre, usuario_propietario_id)
                )
                """
            )
            db.execute(
                "INSERT INTO articulos_personalizados_new "
                "(id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
                "fecha_creacion, fecha_actualizacion, usuario_propietario_id) "
                "SELECT id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
                "fecha_creacion, fecha_actualizacion, usuario_propietario_id FROM articulos_personalizados"
            )
            db.execute("DROP TABLE articulos_personalizados")
            db.execute("ALTER TABLE articulos_personalizados_new RENAME TO articulos_personalizados")
            db.commit()
            db.execute("PRAGMA foreign_keys = ON")

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
        # resumen_consumo() (rutas/consumo.py) filtra por lista_id+fecha para
        # el grafico de consumo; sin este indice es un full table scan, y la
        # tabla crece sin limite (cada sumar_stock/edicion/ticket añade una
        # fila, sin purga).
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_movimientos_stock_lista_fecha "
            "ON movimientos_stock(lista_id, fecha)"
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
        _renombrar_categoria(db, "Alimentacion", "Alimentación")

        # "Espacios" (stocks independientes tipo casa/oficina) se eliminó: nunca tuvo UI y
        # su función de aislamiento ya la cubren las "listas". Se borra la tabla una vez
        # migrados los datos que dependían de ella (productos, historial_articulos,
        # articulos_personalizados, más arriba).
        db.execute("DROP TABLE IF EXISTS espacios")

        db.commit()
    finally:
        db.close()
