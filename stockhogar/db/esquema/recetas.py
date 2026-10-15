"""Recetas del hogar y sus ingredientes."""


def aplicar(db):
    # Recetas del hogar (P-06): lista de ingredientes que se pueden
    # anadir de golpe a la lista de la compra con un boton.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL,
            icono TEXT,
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_recetas_hogar ON recetas(hogar_id)")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS receta_ingredientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receta_id INTEGER NOT NULL REFERENCES recetas(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            unidad TEXT NOT NULL DEFAULT 'ud'
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_receta_ingredientes_receta ON receta_ingredientes(receta_id)"
    )
