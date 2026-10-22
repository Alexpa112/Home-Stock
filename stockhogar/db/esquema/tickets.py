"""Trabajos de analisis de tickets (escaner asincrono)."""


def aplicar(db):
    # El analisis de un ticket tarda entre unos segundos y minutos (Claude Vision,
    # o el lector local en una Raspberry Pi). Hacerlo dentro de UNA peticion HTTP
    # chocaba con cada intermediario (proxy de Next 30 s, Cloudflare 100 s): el
    # usuario recibia un 500/524 aunque el backend siguiera trabajando. Ahora la
    # peticion solo crea el trabajo y devuelve su id; el hilo lo rellena aqui y el
    # cliente consulta el estado. Una tabla (y no memoria del proceso) porque
    # gunicorn corre varios workers y el GET puede caer en otro distinto.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS trabajos_ticket (
            id TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            estado TEXT NOT NULL DEFAULT 'procesando',
            resultado TEXT,
            error_clave TEXT,
            error_estado INTEGER,
            creado INTEGER NOT NULL,
            actualizado INTEGER NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_trabajos_ticket_usuario ON trabajos_ticket(usuario_id, estado)"
    )
