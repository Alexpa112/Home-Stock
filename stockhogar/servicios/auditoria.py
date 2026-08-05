"""Registro de eventos de seguridad (S-09): login, cambios de contraseña/2FA,
altas y bajas de cuenta, invitaciones a hogares... Sin esto, no habia forma de
responder "quien hizo esto" ni de detectar fuerza bruta en curso.
"""
import json
import time


def registrar(db, evento, usuario_id=None, ip=None, resultado="ok", **metadatos):
    """Inserta una fila en eventos_seguridad SIN hacer commit: se deja en la
    misma transaccion que la accion auditada, para que quede constancia solo
    si esa accion tambien se confirma (o se pierda junto con ella si falla)."""
    db.execute(
        "INSERT INTO eventos_seguridad (usuario_id, evento, ip, resultado, metadatos, fecha) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario_id, evento, ip, resultado, json.dumps(metadatos, default=str) if metadatos else None, int(time.time())),
    )
