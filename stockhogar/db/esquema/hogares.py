"""Modelo de hogares (antes 'listas'): hogares, permisos, invitaciones, lista de la compra, stock y precios."""
from ...config import DIAS_AVISO_DEFECTO
from ..conexion import asegurar_columna


def aplicar(db):
    # Migración: renombrado conceptual "lista" -> "hogar" (la tabla `listas`
    # es y siempre fue el contenedor compartible; el nombre no reflejaba eso
    # para el usuario). No destructiva: se crean tablas nuevas y se copian
    # los datos; las tablas viejas (listas, permisos_lista, invitaciones_lista,
    # articulos_lista, stock_lista) se conservan intactas como backup hasta
    # que la reestructuración se valide en producción (ver docs/HOGAR_REESTRUCTURACION.md).
    # Va al final de la función para que articulos_lista ya tenga su forma
    # final (columna articulo_personalizado_id incluida) antes de copiarla.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS hogares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            privada INTEGER NOT NULL DEFAULT 1,
            icono TEXT NOT NULL DEFAULT '📋',
            color TEXT NOT NULL DEFAULT '#B5551A',
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        INSERT INTO hogares (id, nombre, descripcion, usuario_propietario_id, privada, icono, color, fecha_creacion, fecha_actualizacion)
        SELECT id, nombre, descripcion, usuario_propietario_id, privada, icono, color, fecha_creacion, fecha_actualizacion FROM listas
        WHERE id NOT IN (SELECT id FROM hogares)
        """
    )

    # Quien hizo el ultimo cambio de icono/color/nombre del hogar: permite
    # al resto de miembros ver "X ha cambiado el estilo del hogar" en vez
    # de un aviso anonimo. NULL en hogares creados antes de esta columna
    # o nunca editados tras crearse.
    asegurar_columna(db, "hogares", "actualizado_por_usuario_id", "INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS permisos_hogar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'editar')),
            fecha_otorgado TEXT NOT NULL,
            UNIQUE(hogar_id, usuario_id)
        )
        """
    )
    db.execute(
        """
        INSERT INTO permisos_hogar (id, hogar_id, usuario_id, nivel, fecha_otorgado)
        SELECT id, lista_id, usuario_id, nivel, fecha_otorgado FROM permisos_lista
        WHERE id NOT IN (SELECT id FROM permisos_hogar)
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS invitaciones_hogar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
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
        INSERT INTO invitaciones_hogar (id, hogar_id, email_destino, nivel, codigo_invitacion, usado, usuario_aceptacion_id, fecha_creacion, fecha_expiracion, fecha_aceptacion)
        SELECT id, lista_id, email_destino, nivel, codigo_invitacion, usado, usuario_aceptacion_id, fecha_creacion, fecha_expiracion, fecha_aceptacion FROM invitaciones_lista
        WHERE id NOT IN (SELECT id FROM invitaciones_hogar)
        """
    )

    columnas_articulos_lista = [f["name"] for f in db.execute("PRAGMA table_info(articulos_lista)").fetchall()]
    col_art_pers = "articulo_personalizado_id" if "articulo_personalizado_id" in columnas_articulos_lista else "NULL"
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS articulos_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
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
            fecha_creacion TEXT,
            articulo_personalizado_id INTEGER REFERENCES articulos_personalizados(id) ON DELETE CASCADE
        )
        """
    )
    consulta_migracion = f"""
        INSERT INTO articulos_compra (id, hogar_id, producto_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, origen, activo, fecha_completado, fecha_creacion, articulo_personalizado_id)
        SELECT id, lista_id, producto_id, nombre, unidad, categoria, icono, cantidad, sub_descripcion, origen, activo, fecha_completado, fecha_creacion, {col_art_pers} FROM articulos_lista
        WHERE id NOT IN (SELECT id FROM articulos_compra)
        """  # nosec B608 - col_art_pers es "articulo_personalizado_id" o "NULL", literales fijos
    db.execute(consulta_migracion)
    asegurar_columna(db, "articulos_compra", "dias_aviso", f"INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO}")
    asegurar_columna(db, "articulos_compra", "fecha_actualizacion", "TEXT")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_articulos_compra_hogar_id ON articulos_compra(hogar_id, activo)"
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_hogar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            cantidad INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT NOT NULL,
            UNIQUE(hogar_id, producto_id)
        )
        """
    )
    db.execute(
        """
        INSERT INTO stock_hogar (id, hogar_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion)
        SELECT id, lista_id, producto_id, cantidad, stock_minimo, fecha_creacion, fecha_actualizacion FROM stock_lista
        WHERE id NOT IN (SELECT id FROM stock_hogar)
        """
    )

    asegurar_columna(db, "movimientos_stock", "hogar_id", "INTEGER REFERENCES hogares(id) ON DELETE SET NULL")
    db.execute("UPDATE movimientos_stock SET hogar_id = lista_id WHERE hogar_id IS NULL AND lista_id IS NOT NULL")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimientos_stock_hogar_fecha "
        "ON movimientos_stock(hogar_id, fecha)"
    )

    asegurar_columna(db, "hogares", "simbolo_moneda", "TEXT NOT NULL DEFAULT '€'")
    # Presupuesto mensual de gastos compartidos (P-05): NULL = sin limite fijado.
    asegurar_columna(db, "hogares", "presupuesto_mensual", "REAL")
    # Mes ('YYYY-MM') del ultimo aviso push de presupuesto superado, para
    # no notificar mas de una vez por mes aunque se sigan anadiendo gastos.
    asegurar_columna(db, "hogares", "presupuesto_ultimo_aviso_mes", "TEXT")

    # Historico de precios por producto (P-04): una fila por cada vez que
    # se confirma un ticket con precio detectado para ese producto en un
    # hogar. Por hogar (no global) porque el precio pagado depende de la
    # tienda de cada uno.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            precio REAL NOT NULL,
            fecha TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_historial_precios_producto "
        "ON historial_precios(producto_id, hogar_id, fecha)"
    )
