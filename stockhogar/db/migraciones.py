"""Migraciones de datos (no de estructura): se ejecutan en cada arranque y son idempotentes."""
import sqlite3

from ..config import CATALOGO_DEFECTO
from .conexion import ahora, asegurar_columna


def migrar_lista_compra_a_articulos(db):
    """
    Migra datos de la tabla antigua lista_compra a articulos_lista.

    Crea una lista 'por defecto' para cada usuario con sus artículos existentes.
    Esta función se ejecuta solo si encuentra la tabla antigua.
    """
    # Obtener todos los usuarios
    usuarios = db.execute("SELECT id FROM usuarios").fetchall()

    for usuario in usuarios:
        usuario_id = usuario["id"]

        # Crear lista 'por defecto' para este usuario si no existe
        lista_existente = db.execute(
            "SELECT id FROM listas WHERE usuario_propietario_id = ? AND nombre = 'Mi lista'",
            (usuario_id,),
        ).fetchone()

        if not lista_existente:
            cur = db.execute(
                "INSERT INTO listas (nombre, descripcion, usuario_propietario_id, privada, "
                "fecha_creacion, fecha_actualizacion, icono) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
                ("Mi lista", "Lista de compra principal", usuario_id, 1, ahora(), ahora(), "📋"),
            )
            lista_id = cur.fetchone()["id"]
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

            select_clause = f"SELECT {', '.join(campos)} FROM lista_compra"  # nosec B608 - campos son literales fijos del código

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


def renombrar_categoria(db, nombre_viejo, nombre_nuevo):
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
        db.execute(f"UPDATE {tabla} SET categoria = ? WHERE categoria = ?", (nombre_nuevo, nombre_viejo))  # nosec B608 - tabla viene de tupla literal fija


def reparar_fk_articulos_personalizados_old(db):
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


def aislar_catalogos_por_hogar(db):
    """Pasa a POR HOGAR lo que antes era compartido entre todos (idempotente).

    - articulos_personalizados.hogar_id: el hogar donde se creo. Si solo lo usa un hogar se
      deduce de sus articulos de compra; si se usa en varios (o en ninguno) queda NULL y
      sigue visible para los hogares de su propietario, como hasta ahora.
    - historial_articulos aprendido (no del catalogo de serie) en hogar_id = 0: se copia a
      cada hogar que tiene un producto o un articulo de compra con ese nombre y se borra
      de lo global, donde cualquiera lo veia.
    """
    asegurar_columna(db, "articulos_personalizados", "hogar_id", "INTEGER")
    db.execute(
        "UPDATE articulos_personalizados SET hogar_id = ("
        "  SELECT MIN(ac.hogar_id) FROM articulos_compra ac WHERE ac.articulo_personalizado_id = articulos_personalizados.id) "
        "WHERE hogar_id IS NULL AND ("
        "  SELECT COUNT(DISTINCT ac.hogar_id) FROM articulos_compra ac "
        "  WHERE ac.articulo_personalizado_id = articulos_personalizados.id) = 1"
    )

    de_serie = {n.lower() for (n, *_resto) in CATALOGO_DEFECTO}
    aprendidos = [
        f for f in db.execute("SELECT * FROM historial_articulos WHERE hogar_id = 0").fetchall()
        if f["nombre"].lower() not in de_serie
    ]
    for fila in aprendidos:
        hogares = {
            h["hogar_id"] for h in db.execute(
                "SELECT sh.hogar_id FROM stock_hogar sh, productos p WHERE sh.producto_id = p.id AND LOWER(p.nombre) = LOWER(?) "
                "UNION SELECT hogar_id FROM articulos_compra WHERE LOWER(nombre) = LOWER(?)",
                (fila["nombre"], fila["nombre"]),
            ).fetchall()
        }
        for hogar in hogares:
            db.execute(
                "INSERT INTO historial_articulos (nombre, icono, categoria, unidad, sub_descripcion, cantidad_defecto, "
                "dias_aviso, codigo_barras, fecha_actualizacion, hogar_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(nombre, hogar_id) DO NOTHING",
                (fila["nombre"], fila["icono"], fila["categoria"], fila["unidad"], fila["sub_descripcion"],
                 fila["cantidad_defecto"], fila["dias_aviso"], fila["codigo_barras"], fila["fecha_actualizacion"], hogar),
            )
        db.execute("DELETE FROM historial_articulos WHERE id = ?", (fila["id"],))
