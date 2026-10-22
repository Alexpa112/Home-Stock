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
    # Un trabajo "procesando" por usuario, garantizado por la BD: comprobarlo con un SELECT antes
    # del INSERT dejaba pasar peticiones simultaneas (cada una veia "ninguno en curso") y un
    # usuario podia lanzar N analisis a la vez y agotar los hilos del servidor.
    try:
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_trabajos_ticket_uno_por_usuario "
            "ON trabajos_ticket(usuario_id) WHERE estado = 'procesando'"
        )
    except Exception:
        # Ya habia dos "procesando" del mismo usuario (de antes del indice): se dan por perdidos
        # todos menos el mas reciente y se reintenta.
        db.execute(
            "UPDATE trabajos_ticket SET estado = 'error', error_clave = 'err_procesando_ticket', error_estado = 504 "
            "WHERE estado = 'procesando' AND rowid NOT IN ("
            "  SELECT MAX(rowid) FROM trabajos_ticket WHERE estado = 'procesando' GROUP BY usuario_id)"
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_trabajos_ticket_uno_por_usuario "
            "ON trabajos_ticket(usuario_id) WHERE estado = 'procesando'"
        )
