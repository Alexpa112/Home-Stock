"""Seguridad y cuotas: intentos de login, sesiones revocadas, 2FA, uso diario de OCR, tokens de verificacion, auditoria y niveles de permiso."""
from ..conexion import asegurar_columna


def aplicar(db):
    # Intentos de login fallidos, persistidos (en vez de en memoria del
    # proceso) porque gunicorn corre --workers 2 (procesos separados que
    # no comparten memoria, ver Dockerfile.raspbian): un dict en memoria
    # dejaria el contador visible solo para el worker que registro el
    # fallo. clave = ip, o "ip:usuario" para el cubo por-cuenta (ver
    # servicios/intentos_login.py).
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS intentos_login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT NOT NULL,
            fecha_intento INTEGER NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_intentos_login_clave ON intentos_login(clave, fecha_intento)"
    )

    # Sesiones cerradas con "cerrar sesion": la cookie es autocontenida, asi que sin
    # esta lista una cookie copiada antes del logout seguia valiendo hasta caducar.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS sesiones_revocadas (
            sid_hash TEXT PRIMARY KEY,
            expira TEXT NOT NULL
        )
        """
    )

    # Intentos y reenvios de codigos 2FA (A-5): contador independiente por
    # usuario con maximo 10 intentos y 3 reenvios por hora. Diferente de
    # intentos_login: este registra el tipo (verificar/reenvio) para poder
    # contarlos independientemente.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS intentos_2fa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,
            fecha INTEGER NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_intentos_2fa_usuario ON intentos_2fa(usuario_id, tipo, fecha)"
    )

    # Uso diario de OCR por usuario, para el limite de cuota (ver config.py
    # LIMITE_OCR_DIARIO y rutas/escaner/ocr_tickets.py).
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS uso_ocr_diario (
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            fecha TEXT NOT NULL,
            contador INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (usuario_id, fecha)
        )
        """
    )

    # Uso diario de subida de recibos por usuario (S-21), mismo patron
    # que uso_ocr_diario pero en tabla separada: son cuotas de conceptos
    # distintos (escaneo OCR vs. adjuntar foto de un gasto ya existente),
    # mezclarlas en la misma tabla confundiria el limite de cada una.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS uso_recibos_diario (
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            fecha TEXT NOT NULL,
            contador INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (usuario_id, fecha)
        )
        """
    )

    # Verificacion de email de-facto nunca comprobada hasta ahora (S-07):
    # el campo usuarios.email se rellenaba por OAuth o desde el panel sin
    # confirmar que su dueño realmente controla esa direccion, aunque ya
    # se le enviara el codigo de doble factor.
    asegurar_columna(db, "usuarios", "email_verificado", "INTEGER NOT NULL DEFAULT 0")

    # Opt-out del OCR en la nube (S-26): con esto activo, el escaneo de
    # tickets usa solo el pipeline local (Tesseract), sin enviar la foto
    # a Anthropic. Ver stockhogar/rutas/escaner/tickets.py::analizar_ticket.
    asegurar_columna(db, "usuarios", "usuario_ocr_local", "INTEGER NOT NULL DEFAULT 0")

    # session_version (S-08): alternativa minima a una tabla de sesiones
    # completa. Se guarda en la cookie de sesion junto a usuario_id; un
    # valor que no coincida con el de la BD invalida esa sesion (ver
    # api/base.py::requerir_sesion). Se incrementa al cambiar password,
    # al restablecerla, al desactivar el 2FA o al pedir explicitamente
    # "cerrar sesion en otros dispositivos".
    asegurar_columna(db, "usuarios", "session_version", "INTEGER NOT NULL DEFAULT 0")

    # Tokens de un solo uso para verificar email y restablecer password
    # (S-07). Se guarda el hash (SHA-256), nunca el token en claro, mismo
    # patron que codigos_dos_factor.codigo_hash de arriba.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens_verificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL CHECK (tipo IN ('verificar_email', 'reset_password')),
            token_hash TEXT NOT NULL,
            expira INTEGER NOT NULL,
            usado INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tokens_verificacion_hash ON tokens_verificacion(token_hash)"
    )

    # Auditoria de eventos de seguridad (S-09): login, cambios de
    # password/2FA, altas/bajas de cuenta, invitaciones... usuario_id
    # nullable con ON DELETE SET NULL para que el evento sobreviva al
    # borrado de la cuenta (auditoria util incluso de una cuenta ya
    # eliminada).
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS eventos_seguridad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            evento TEXT NOT NULL,
            ip TEXT,
            resultado TEXT NOT NULL DEFAULT 'ok',
            metadatos TEXT,
            fecha INTEGER NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_eventos_seguridad_usuario_fecha ON eventos_seguridad(usuario_id, fecha)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_eventos_seguridad_fecha ON eventos_seguridad(fecha)"
    )

    # Invitaciones a un hogar dirigidas a un usuario YA registrado (S-10):
    # antes, compartir por nombre de usuario daba acceso INMEDIATO sin
    # que el destinatario aceptase nada, y el 404 al no encontrarlo
    # permitia enumerar usuarios existentes. Ahora ese camino crea una
    # fila aqui igual que el camino por email (ver invitaciones_hogar),
    # con el mismo mensaje de exito exista o no el usuario.
    asegurar_columna(db, "invitaciones_hogar", "usuario_destino_id", "INTEGER REFERENCES usuarios(id) ON DELETE CASCADE")

    # Nivel de permiso intermedio "comprar" (P-08): puede marcar
    # articulos de la lista como comprados y mover stock, pero no crear/
    # editar gastos ni artículos de la lista en sí (ver
    # stockhogar/autorizacion.py). El CHECK de SQLite no se puede
    # ampliar con ALTER TABLE, asi que en instalaciones con el CHECK
    # antiguo ('ver','editar') se recrea la tabla conservando los datos.
    for tabla in ("permisos_hogar", "invitaciones_hogar"):
        esquema = db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
        ).fetchone()
        if esquema and "'comprar'" not in esquema["sql"]:
            db.execute(f"ALTER TABLE {tabla} RENAME TO {tabla}_old")
            if tabla == "permisos_hogar":
                db.execute(
                    """
                    CREATE TABLE permisos_hogar (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
                        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                        nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'comprar', 'editar')),
                        fecha_otorgado TEXT NOT NULL,
                        UNIQUE(hogar_id, usuario_id)
                    )
                    """
                )
            else:
                db.execute(
                    """
                    CREATE TABLE invitaciones_hogar (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hogar_id INTEGER NOT NULL REFERENCES hogares(id) ON DELETE CASCADE,
                        email_destino TEXT NOT NULL,
                        nivel TEXT NOT NULL CHECK (nivel IN ('ver', 'comprar', 'editar')),
                        codigo_invitacion TEXT NOT NULL UNIQUE,
                        usado INTEGER NOT NULL DEFAULT 0,
                        usuario_aceptacion_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                        fecha_creacion TEXT NOT NULL,
                        fecha_expiracion TEXT NOT NULL,
                        fecha_aceptacion TEXT,
                        usuario_destino_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
                    )
                    """
                )
            columnas = [f["name"] for f in db.execute(f"PRAGMA table_info({tabla}_old)").fetchall()]
            cols_sql = ", ".join(columnas)
            db.execute(f"INSERT INTO {tabla} ({cols_sql}) SELECT {cols_sql} FROM {tabla}_old")  # nosec B608 - tabla y cols_sql vienen de introspeccion del propio esquema, no de input externo
            db.execute(f"DROP TABLE {tabla}_old")
            db.commit()
