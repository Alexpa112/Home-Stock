"""Datos personales del usuario (RGPD): eventos de seguridad, exportacion y baja de la cuenta."""
from .blueprint import bp
from .comunes import falta_reautenticar
import io
import json
import zipfile
from flask import Response, session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...nucleo import cifrado
from ...db import get_db
from ...nucleo.red import ip_cliente
from ...servicios.cuenta import auditoria


@bp.route("/api/auth/mis-eventos-seguridad", methods=["GET"])
@requerir_sesion
@manejo_errores
def mis_eventos_seguridad():
    """Los ultimos 50 eventos de seguridad DEL PROPIO usuario autenticado
    (S-09): informacion legitima para el dueño de la cuenta, nunca de otros."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    filas = db.execute(
        "SELECT evento, resultado, fecha FROM eventos_seguridad WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 50",
        (usuario_id,),
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])


def _filas_a_lista(db, sql, params):
    return [dict(f) for f in db.execute(sql, params).fetchall()]


@bp.route("/api/auth/exportar-mis-datos", methods=["GET"])
@requerir_sesion
@manejo_errores
def exportar_mis_datos():
    """Exportacion completa de los datos personales del usuario (S-22,
    RGPD art. 15 y 20): un ZIP con toda su informacion en JSON, mas los
    binarios de recibos que tenga adjuntos. Las fotos de tickets escaneados
    no se guardan en ningun lado tras el OCR (ver tickets.py, se procesan
    desde un fichero temporal que se borra al terminar), asi que no hay
    nada que exportar de esas.
    """
    usuario_id = session.get("usuario_id")
    db = get_db()

    perfil = db.execute(
        "SELECT id, nombre_usuario, nombre, email, email_verificado, fecha_creacion, "
        "idioma_preferido, tema_preferido, doble_factor_activo, usuario_ocr_local "
        "FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()

    hogares_propios = _filas_a_lista(
        db, "SELECT id, nombre, descripcion, fecha_creacion FROM hogares WHERE usuario_propietario_id = ?", (usuario_id,)
    )
    hogares_compartidos = _filas_a_lista(
        db,
        "SELECT h.id, h.nombre, p.nivel, p.fecha_otorgado FROM hogares h "
        "JOIN permisos_hogar p ON p.hogar_id = h.id WHERE p.usuario_id = ?",
        (usuario_id,),
    )
    ids_hogares = [h["id"] for h in hogares_propios] + [h["id"] for h in hogares_compartidos]
    placeholders = ",".join("?" for _ in ids_hogares) or "NULL"

    inventario = []
    articulos_compra = []
    if ids_hogares:
        inventario = _filas_a_lista(
            db,
            f"SELECT sh.hogar_id, p.nombre, sh.cantidad, sh.stock_minimo, sh.fecha_actualizacion "  # nosec B608 - placeholders solo contiene "?" y ",", nunca input directo
            f"FROM stock_hogar sh JOIN productos p ON p.id = sh.producto_id WHERE sh.hogar_id IN ({placeholders})",
            ids_hogares,
        )
        articulos_compra = _filas_a_lista(
            db,
            f"SELECT hogar_id, nombre, cantidad, unidad, activo, fecha_creacion FROM articulos_compra "  # nosec B608 - placeholders solo contiene "?" y ",", nunca input directo
            f"WHERE hogar_id IN ({placeholders})",
            ids_hogares,
        )

    gastos_pagados = _filas_a_lista(
        db, "SELECT id, hogar_id, descripcion, importe_total, fecha FROM gastos WHERE usuario_pagador_id = ?", (usuario_id,)
    )
    gastos_participados = _filas_a_lista(
        db,
        "SELECT g.id, g.hogar_id, g.descripcion, gp.importe FROM gastos_participantes gp "
        "JOIN gastos g ON g.id = gp.gasto_id WHERE gp.usuario_id = ?",
        (usuario_id,),
    )
    liquidaciones = _filas_a_lista(
        db,
        "SELECT id, hogar_id, usuario_origen_id, usuario_destino_id, importe, fecha, nota FROM liquidaciones "
        "WHERE usuario_origen_id = ? OR usuario_destino_id = ?",
        (usuario_id, usuario_id),
    )
    movimientos_stock = _filas_a_lista(
        db,
        "SELECT producto_id, hogar_id, delta, cantidad_resultante, origen, fecha FROM movimientos_stock WHERE usuario_id = ?",
        (usuario_id,),
    )

    recibos = db.execute(
        "SELECT id, imagen_recibo, imagen_recibo_mime FROM gastos WHERE usuario_pagador_id = ? AND imagen_recibo IS NOT NULL",
        (usuario_id,),
    ).fetchall()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("perfil.json", json.dumps(dict(perfil) if perfil else {}, default=str, ensure_ascii=False, indent=2))
        zf.writestr(
            "hogares.json",
            json.dumps({"propios": hogares_propios, "compartidos": hogares_compartidos}, default=str, ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "inventario.json",
            json.dumps({"stock": inventario, "lista_de_la_compra": articulos_compra}, default=str, ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "gastos.json",
            json.dumps(
                {"pagados_por_mi": gastos_pagados, "en_los_que_participo": gastos_participados, "liquidaciones": liquidaciones},
                default=str, ensure_ascii=False, indent=2,
            ),
        )
        zf.writestr("movimientos_stock.json", json.dumps(movimientos_stock, default=str, ensure_ascii=False, indent=2))
        for recibo in recibos:
            extension = (recibo["imagen_recibo_mime"] or "").split("/")[-1] or "jpg"
            zf.writestr(f"recibos/gasto_{recibo['id']}.{extension}", cifrado.descifrar_bytes(recibo["imagen_recibo"]) or b"")

    buffer.seek(0)
    return Response(
        buffer.read(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=mis-datos-dreame.zip"},
    )


@bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_usuario(usuario_id):
    if session.get("usuario_id") != usuario_id:
        return APIResponse.no_permitido()

    db = get_db()
    error_reauth = falta_reautenticar(db, usuario_id, cuerpo_json())
    if error_reauth:
        return error_reauth
    total = db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    if total <= 1:
        return APIResponse.error("err_ultimo_usuario", 400)

    # El evento se inserta ANTES del DELETE, en la misma transaccion: la FK
    # de eventos_seguridad.usuario_id es ON DELETE SET NULL, asi que la fila
    # sobrevive al borrado (queda con usuario_id NULL) en vez de perderse.
    auditoria.registrar(db, "baja_cuenta", usuario_id=usuario_id, ip=ip_cliente())
    db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    db.commit()
    session.clear()
    return APIResponse.success()
