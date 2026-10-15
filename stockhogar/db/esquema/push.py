"""Suscripciones a notificaciones push del navegador."""


def aplicar(db):
    # Suscripciones a notificaciones push del navegador (P-01). endpoint
    # es UNIQUE porque el navegador puede volver a mandarlo (p.ej. tras
    # reinstalar la PWA) y hay que sobrescribir las claves antiguas, no
    # duplicar la fila.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_usuario ON push_subscriptions(usuario_id)"
    )
