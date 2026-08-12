"""Cuota diaria de escaneo de tickets (LIMITE_OCR_DIARIO).

Vivia dentro de rutas/ocr_tickets.py, es decir, protegia
`POST /api/ocr/procesar-ticket`... que es el endpoint que el frontend NO usa:
la app escanea por `POST /api/tickets/analizar` (ver lib/api.ts), que no tenia
ninguna cuota. El test que la cubria tambien atacaba la ruta muerta, asi que
pasaba en verde sin comprobar nada (hallazgo A-6 de la auditoria 2026-08).

Sin cuota, cualquier usuario autenticado podia llamar en bucle a la operacion
mas cara de la app -- 16.000 tokens de salida con esfuerzo alto, hasta 10
imagenes de 2576 px o un PDF de 10 MB, facturada a una clave de Anthropic que
es global al despliegue -- agotando la cuota del escaner para TODOS los
usuarios y reteniendo un worker de gunicorn hasta 180 s por peticion.

Al vivir en un servicio, la cuota es de "escanear un ticket", no de una ruta
concreta: cualquier endpoint que llegue a llamar al motor de nube la comparte.
"""
from datetime import date


def uso_hoy(db, usuario_id):
    fila = db.execute(
        "SELECT contador FROM uso_ocr_diario WHERE usuario_id = ? AND fecha = ?",
        (usuario_id, date.today().isoformat()),
    ).fetchone()
    return fila["contador"] if fila else 0


def incrementar(db, usuario_id):
    db.execute(
        "INSERT INTO uso_ocr_diario (usuario_id, fecha, contador) VALUES (?, ?, 1) "
        "ON CONFLICT(usuario_id, fecha) DO UPDATE SET contador = contador + 1",
        (usuario_id, date.today().isoformat()),
    )
    db.commit()
