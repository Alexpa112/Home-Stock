"""Saldos entre miembros, simplificacion de deudas y liquidaciones."""
from .blueprint import bp
from .comunes import TOLERANCIA_REPARTO, miembros_hogar_ids
import heapq
from flask import session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...db import ahora, get_db
from ...servicios.stock import hogar_actual_con_permiso
from ...utils import Validator, ValidationError


def calcular_saldos(db, hogar_id):
    """Saldo neto por miembro del hogar: positivo = le deben, negativo = debe."""
    filas = db.execute(
        """SELECT u.id, COALESCE(u.nombre, u.nombre_usuario) AS nombre_usuario,
               COALESCE(pagado.total, 0) - COALESCE(debido.total, 0)
               - COALESCE(recibido.total, 0) + COALESCE(pagado_liq.total, 0) AS saldo
           FROM usuarios u
           LEFT JOIN (SELECT usuario_pagador_id AS uid, SUM(importe_total) AS total
                      FROM gastos WHERE hogar_id = ? GROUP BY uid) pagado ON pagado.uid = u.id
           LEFT JOIN (SELECT gp.usuario_id AS uid, SUM(gp.importe) AS total
                      FROM gastos_participantes gp, gastos g
                      WHERE gp.gasto_id = g.id AND g.hogar_id = ? GROUP BY gp.usuario_id) debido ON debido.uid = u.id
           LEFT JOIN (SELECT usuario_destino_id AS uid, SUM(importe) AS total
                      FROM liquidaciones WHERE hogar_id = ? GROUP BY uid) recibido ON recibido.uid = u.id
           LEFT JOIN (SELECT usuario_origen_id AS uid, SUM(importe) AS total
                      FROM liquidaciones WHERE hogar_id = ? GROUP BY uid) pagado_liq ON pagado_liq.uid = u.id
           WHERE u.id IN (
               SELECT usuario_propietario_id FROM hogares WHERE id = ?
               UNION SELECT usuario_id FROM permisos_hogar WHERE hogar_id = ?
           )
           ORDER BY COALESCE(u.nombre, u.nombre_usuario)""",
        (hogar_id, hogar_id, hogar_id, hogar_id, hogar_id, hogar_id),
    ).fetchall()

    return [
        {"usuario_id": f["id"], "nombre_usuario": f["nombre_usuario"], "saldo": round(f["saldo"], 2)}
        for f in filas
    ]


@bp.route("/saldo", methods=["GET"])
@requerir_sesion
@manejo_errores
def saldo_hogar():
    """Saldo neto por miembro del hogar activo: positivo = le deben, negativo = debe."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    return APIResponse.success(calcular_saldos(db, hogar_id))


def _simplificar_deudas(saldos):
    """Algoritmo voraz: en cada paso empareja al mayor acreedor con el mayor
    deudor, minimizando el número de pagos necesarios para saldar el grupo
    (como máximo N-1 transacciones, N = nº de miembros con saldo distinto de 0)."""
    acreedores = []
    deudores = []
    for s in saldos:
        saldo = s["saldo"]
        if saldo > TOLERANCIA_REPARTO:
            heapq.heappush(acreedores, (-saldo, s["usuario_id"], s["nombre_usuario"]))
        elif saldo < -TOLERANCIA_REPARTO:
            heapq.heappush(deudores, (saldo, s["usuario_id"], s["nombre_usuario"]))

    transacciones = []
    while acreedores and deudores:
        neg_credito, acreedor_id, acreedor_nombre = heapq.heappop(acreedores)
        neg_deuda, deudor_id, deudor_nombre = heapq.heappop(deudores)
        credito, deuda = -neg_credito, -neg_deuda
        importe = round(min(credito, deuda), 2)

        transacciones.append({
            "usuario_origen_id": deudor_id,
            "usuario_origen_nombre": deudor_nombre,
            "usuario_destino_id": acreedor_id,
            "usuario_destino_nombre": acreedor_nombre,
            "importe": importe,
        })

        credito_restante = round(credito - importe, 2)
        deuda_restante = round(deuda - importe, 2)
        if credito_restante > TOLERANCIA_REPARTO:
            heapq.heappush(acreedores, (-credito_restante, acreedor_id, acreedor_nombre))
        if deuda_restante > TOLERANCIA_REPARTO:
            heapq.heappush(deudores, (-deuda_restante, deudor_id, deudor_nombre))

    return transacciones


@bp.route("/simplificar", methods=["GET"])
@requerir_sesion
@manejo_errores
def simplificar_deudas():
    """Sugiere el conjunto mínimo de pagos para saldar el hogar activo."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    saldos = calcular_saldos(db, hogar_id)
    return APIResponse.success(_simplificar_deudas(saldos))


@bp.route("/liquidaciones", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_liquidacion():
    """Registra que un miembro ha pagado a otro para saldar (parte de) el saldo."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = cuerpo_json()
    usuario_origen_id = datos.get("usuario_origen_id")
    usuario_destino_id = datos.get("usuario_destino_id")
    importe = Validator.decimal_positivo(datos.get("importe"), "importe")
    nota = Validator.string_opcional(datos.get("nota"), None, 200)

    if usuario_origen_id == usuario_destino_id:
        raise ValidationError("El origen y el destino de la liquidación deben ser distintos")

    miembros_ids = miembros_hogar_ids(db, hogar_id)
    if usuario_origen_id not in miembros_ids or usuario_destino_id not in miembros_ids:
        raise ValidationError("Origen y destino deben ser miembros del hogar")

    db.execute(
        """INSERT INTO liquidaciones (hogar_id, usuario_origen_id, usuario_destino_id, importe, fecha, nota)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (hogar_id, usuario_origen_id, usuario_destino_id, importe, ahora(), nota),
    )
    db.commit()
    return APIResponse.success({"exito": True}, 201)


def _liquidacion_a_dict(liquidacion):
    return {
        "id": liquidacion["id"],
        "usuario_origen_id": liquidacion["usuario_origen_id"],
        "origen_nombre": liquidacion["origen_nombre"],
        "usuario_destino_id": liquidacion["usuario_destino_id"],
        "destino_nombre": liquidacion["destino_nombre"],
        "importe": liquidacion["importe"],
        "fecha": liquidacion["fecha"],
        "nota": liquidacion["nota"],
    }


@bp.route("/liquidaciones", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_liquidaciones():
    """Histórico de liquidaciones del hogar activo, más recientes primero."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    liquidaciones = db.execute(
        """SELECT l.*, COALESCE(uo.nombre, uo.nombre_usuario) AS origen_nombre,
               COALESCE(ud.nombre, ud.nombre_usuario) AS destino_nombre
           FROM liquidaciones l, usuarios uo, usuarios ud
           WHERE l.usuario_origen_id = uo.id AND l.usuario_destino_id = ud.id AND l.hogar_id = ?
           ORDER BY l.fecha DESC, l.id DESC""",
        (hogar_id,),
    ).fetchall()

    return APIResponse.success([_liquidacion_a_dict(l) for l in liquidaciones])


@bp.route("/liquidaciones/<int:liquidacion_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_liquidacion(liquidacion_id):
    """Elimina una liquidación (requiere nivel editar sobre el hogar)."""
    db = get_db()
    liquidacion = db.execute("SELECT * FROM liquidaciones WHERE id = ?", (liquidacion_id,)).fetchone()
    if not liquidacion:
        return APIResponse.no_encontrado("recurso_liquidacion")

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id or liquidacion["hogar_id"] != hogar_id:
        return APIResponse.no_permitido()

    db.execute("DELETE FROM liquidaciones WHERE id = ?", (liquidacion_id,))
    db.commit()
    return APIResponse.success()
