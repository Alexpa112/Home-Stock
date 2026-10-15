"""Catalogo: categorias, historial de articulos, articulos personalizados, traducciones, movimientos de stock y semillas."""
from ...config import CATALOGO_DEFECTO, CATEGORIAS_DEFECTO, DIAS_AVISO_DEFECTO
from ..conexion import ahora, asegurar_columna, quitar_columna_si_existe
from ..iconos import migrar_iconos_emoji_a_lucide
from ..migraciones import renombrar_categoria


def aplicar(db):
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
        "INSERT INTO categorias (nombre, icono) VALUES (?, ?) ON CONFLICT(nombre) DO NOTHING",
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
    asegurar_columna(db, "historial_articulos", "dias_aviso", f"INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO}")
    asegurar_columna(db, "historial_articulos", "codigo_barras", "TEXT")

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

    # hogar_id = 0: catalogo estandar (sembrado, nadie lo modifica). hogar_id > 0:
    # lo que aprendio ese hogar; solo lo ven y lo cambian sus miembros. Antes todo
    # era global y un hogar podia leer los articulos de otro o cambiar el icono de
    # "Leche entera" para todos.
    asegurar_columna(db, "historial_articulos", "hogar_id", "INTEGER NOT NULL DEFAULT 0")
    db.execute("DROP INDEX IF EXISTS idx_historial_nombre")
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_historial_nombre_hogar "
        "ON historial_articulos(nombre COLLATE NOCASE, hogar_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_historial_codigo_barras ON historial_articulos(codigo_barras) "
        "WHERE codigo_barras IS NOT NULL"
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
            usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            UNIQUE(nombre, usuario_propietario_id)
        )
        """
    )
    asegurar_columna(db, "articulos_personalizados", "fecha_creacion", "TEXT")
    asegurar_columna(db, "articulos_personalizados", "fecha_actualizacion", "TEXT")
    asegurar_columna(db, "articulos_personalizados", "dias_aviso", f"INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO}")

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
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                    (original["nombre"], original["categoria"], original["icono"], original["unidad"],
                     original["sub_descripcion"], original["cantidad_defecto"], original["fecha_creacion"],
                     original["fecha_actualizacion"], propietario_extra)
                )
                nuevo_id = cur.fetchone()["id"]

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
                usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
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

    # Migración: usuario_propietario_id no tenía ON DELETE CASCADE, así que
    # borrar un usuario con artículos personalizados propios fallaba con
    # FOREIGN KEY constraint failed (500) en vez de arrastrar el borrado
    # como ocurre con el resto de tablas de usuario (hogares, gastos, etc.).
    sql_actual = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='articulos_personalizados'"
    ).fetchone()
    if sql_actual and "usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE" not in sql_actual["sql"]:
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            f"""
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
                usuario_propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                dias_aviso INTEGER NOT NULL DEFAULT {DIAS_AVISO_DEFECTO},
                UNIQUE(nombre, usuario_propietario_id)
            )
            """
        )
        db.execute(
            "INSERT INTO articulos_personalizados_new "
            "(id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
            "fecha_creacion, fecha_actualizacion, usuario_propietario_id, dias_aviso) "
            "SELECT id, nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, "
            "fecha_creacion, fecha_actualizacion, usuario_propietario_id, dias_aviso FROM articulos_personalizados"
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
    # resumen_consumo() (rutas/inventario/consumo.py) filtra por lista_id+fecha para
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
        "INSERT INTO historial_articulos "
        "(nombre, categoria, icono, unidad, sub_descripcion, cantidad_defecto, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, ?, 1, ?) "
        "ON CONFLICT(nombre, hogar_id) DO NOTHING",
        [(n, c, i, u, s, ahora()) for (n, c, i, u, s) in CATALOGO_DEFECTO],
    )

    migrar_iconos_emoji_a_lucide(db)
    renombrar_categoria(db, "Alimentacion", "Alimentación")
