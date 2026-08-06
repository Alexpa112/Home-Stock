"""Envia notificaciones push de "revisa la caducidad" (P-07) para los
productos cuyo stock lleva sin tocarse mas dias que su dias_aviso
configurado.

Pensado para ejecutarse una vez al dia via cron del sistema (mismo patron
que scripts/auto_update.sh en la Raspberry Pi), no desde la propia app: el
envio de decenas/centenas de push por HTTP puede tardar mas de lo razonable
dentro de una peticion web.

Uso:
    python scripts/enviar_avisos_caducidad.py

No revive avisos ya mandados: tras notificar un producto, se marca su
fecha_ultimo_aviso_caducidad y no se vuelve a avisar de el hasta pasados
REPETIR_AVISO_TRAS_DIAS dias (para no espamear a diario mientras el usuario
simplemente no ha vuelto a tocar ese producto).
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stockhogar.config import DB_PATH  # noqa: E402
from stockhogar.db import ahora  # noqa: E402
from stockhogar.servicios.push_service import enviar_push_a_usuario  # noqa: E402

REPETIR_AVISO_TRAS_DIAS = 7


def _dias_desde(fecha_iso):
    if not fecha_iso:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(fecha_iso)).days
    except ValueError:
        return None


def _miembros_del_hogar(db, hogar_id):
    filas = db.execute(
        "SELECT usuario_propietario_id AS id FROM hogares WHERE id = ? "
        "UNION SELECT usuario_id AS id FROM permisos_hogar WHERE hogar_id = ?",
        (hogar_id, hogar_id),
    ).fetchall()
    return [f["id"] for f in filas]


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    productos = db.execute(
        """SELECT p.id, p.nombre, p.dias_aviso, p.fecha_actualizacion,
                  p.fecha_ultimo_aviso_caducidad, sh.hogar_id
           FROM productos p
           JOIN stock_hogar sh ON sh.producto_id = p.id
           WHERE p.dias_aviso IS NOT NULL AND p.dias_aviso > 0
             AND p.fecha_actualizacion IS NOT NULL"""
    ).fetchall()

    enviados = 0
    revisados = 0
    for producto in productos:
        dias_desde_actualizacion = _dias_desde(producto["fecha_actualizacion"])
        if dias_desde_actualizacion is None or dias_desde_actualizacion < producto["dias_aviso"]:
            continue

        dias_desde_ultimo_aviso = _dias_desde(producto["fecha_ultimo_aviso_caducidad"])
        if dias_desde_ultimo_aviso is not None and dias_desde_ultimo_aviso < REPETIR_AVISO_TRAS_DIAS:
            continue

        revisados += 1
        for usuario_id in _miembros_del_hogar(db, producto["hogar_id"]):
            enviados += enviar_push_a_usuario(
                db,
                usuario_id,
                titulo="Revisa la caducidad",
                cuerpo=f"Hace tiempo que no tocas «{producto['nombre']}»: puede que caduque pronto.",
                url="/dashboard",
            )

        db.execute(
            "UPDATE productos SET fecha_ultimo_aviso_caducidad = ? WHERE id = ?",
            (ahora(), producto["id"]),
        )

    db.commit()
    db.close()
    print(f"[OK] {revisados} productos revisados, {enviados} notificaciones push enviadas")


if __name__ == "__main__":
    main()
