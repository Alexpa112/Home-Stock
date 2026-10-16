"""Usuarios, 2FA, OAuth y el modelo antiguo de listas (productos, articulos_lista, stock_lista)."""
from ...config import DIAS_AVISO_DEFECTO
from ..conexion import ahora, asegurar_columna, quitar_columna_si_existe
from ..migraciones import migrar_lista_compra_a_articulos


def aplicar(db):
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
    asegurar_columna(db, "usuarios", "nombre", "TEXT")
    asegurar_columna(db, "usuarios", "idioma_preferido", "TEXT NOT NULL DEFAULT 'es'")
    asegurar_columna(db, "usuarios", "tema_preferido", "TEXT NOT NULL DEFAULT 'auto'")
    asegurar_columna(db, "usuarios", "teclado_virtual_activo", "TEXT NOT NULL DEFAULT 'on'")
    asegurar_columna(db, "usuarios", "vista_lista_compra", "TEXT NOT NULL DEFAULT 'lista'")
    asegurar_columna(db, "usuarios", "agrupar_categorias", "TEXT NOT NULL DEFAULT 'off'")
    asegurar_columna(db, "usuarios", "doble_factor_activo", "INTEGER NOT NULL DEFAULT 0")
    # Aceptacion de Terminos y Condiciones / Politica de Privacidad (ver
    # config.VERSION_TERMINOS): NULL significa que el usuario aun no ha
    # aceptado la version vigente (usuarios ya existentes al desplegar
    # esto, o cuentas creadas por OAuth antes de pasar por la pantalla
    # de aceptacion).
    asegurar_columna(db, "usuarios", "terminos_version_aceptada", "TEXT")
    asegurar_columna(db, "usuarios", "terminos_fecha_aceptacion", "TEXT")

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

    # Tabla para cuentas OAuth (Google)
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
    # Ultimo aviso de caducidad enviado por push (P-07): evita re-notificar
    # cada dia mientras el producto siga sin tocarse, ver
    # scripts/enviar_avisos_caducidad.py.
    asegurar_columna(db, "productos", "fecha_ultimo_aviso_caducidad", "TEXT")
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
                        """INSERT INTO stock_lista
                           (lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(lista_id, producto_id) DO NOTHING""",
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
        migrar_lista_compra_a_articulos(db)
    db.execute("DROP TABLE IF EXISTS ajustes")
