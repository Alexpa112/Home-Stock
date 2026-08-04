"""Gastos compartidos del hogar (division tipo Tricount): registro de quien
pago que y como se reparte entre los miembros, y saldo neto de cada uno."""
from flask import Blueprint, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..db import ahora, get_db
from ..servicios.stock import hogar_actual_con_permiso
from ..utils import Validator, ValidationError

bp = Blueprint("gastos", __name__, url_prefix="/api/gastos")

TOLERANCIA_REPARTO = 0.01


def _miembros_hogar_ids(db, hogar_id):
    """IDs de usuario que pertenecen al hogar (propietario + permisos_hogar)."""
    filas = db.execute(
        "SELECT usuario_propietario_id AS id FROM hogares WHERE id = ? "
        "UNION SELECT usuario_id AS id FROM permisos_hogar WHERE hogar_id = ?",
        (hogar_id, hogar_id),
    ).fetchall()
    return {f["id"] for f in filas}


def _gasto_a_dict(db, gasto):
    participantes = db.execute(
        """SELECT gp.usuario_id, gp.importe, u.nombre_usuario
           FROM gastos_participantes gp, usuarios u
           WHERE gp.usuario_id = u.id AND gp.gasto_id = ?
           ORDER BY u.nombre_usuario""",
        (gasto["id"],),
    ).fetchall()
    return {
        "id": gasto["id"],
        "descripcion": gasto["descripcion"],
        "importe_total": gasto["importe_total"],
        "fecha": gasto["fecha"],
        "usuario_pagador_id": gasto["usuario_pagador_id"],
        "pagador_nombre": gasto["pagador_nombre"],
        "participantes": [
            {"usuario_id": p["usuario_id"], "importe": p["importe"], "nombre_usuario": p["nombre_usuario"]}
            for p in participantes
        ],
    }


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_gastos():
    """Lista los gastos del hogar activo, más recientes primero."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    gastos = db.execute(
        """SELECT g.*, u.nombre_usuario AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.hogar_id = ?
           ORDER BY g.fecha DESC, g.id DESC""",
        (hogar_id,),
    ).fetchall()

    return APIResponse.success([_gasto_a_dict(db, g) for g in gastos])


@bp.route("", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_gasto():
    """Crea un gasto con reparto flexible entre los participantes indicados."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    descripcion = Validator.string_requerido(datos.get("descripcion"), "descripción", 200)
    importe_total = Validator.decimal_positivo(datos.get("importe_total"), "importe total")
    fecha = Validator.string_opcional(datos.get("fecha"), ahora(), 30)
    usuario_pagador_id = datos.get("usuario_pagador_id")
    participantes = datos.get("participantes")

    if not isinstance(participantes, list) or not participantes:
        raise ValidationError("El gasto debe tener al menos un participante")

    miembros_ids = _miembros_hogar_ids(db, hogar_id)
    if usuario_pagador_id not in miembros_ids:
        raise ValidationError("El pagador debe ser miembro del hogar")

    reparto = []
    suma_reparto = 0.0
    for participante in participantes:
        usuario_id = participante.get("usuario_id")
        if usuario_id not in miembros_ids:
            raise ValidationError("Todos los participantes deben ser miembros del hogar")
        importe = Validator.decimal_positivo(participante.get("importe"), "importe del participante")
        reparto.append((usuario_id, importe))
        suma_reparto += importe

    if abs(suma_reparto - importe_total) > TOLERANCIA_REPARTO:
        raise ValidationError("La suma del reparto no coincide con el importe total")

    usuario_id_actual = session.get("usuario_id")
    cur = db.execute(
        """INSERT INTO gastos
           (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, creado_por_usuario_id, fecha_creacion)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, usuario_id_actual, ahora()),
    )
    gasto_id = cur.lastrowid

    for usuario_id, importe in reparto:
        db.execute(
            "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
            (gasto_id, usuario_id, importe),
        )
    db.commit()

    gasto = db.execute(
        """SELECT g.*, u.nombre_usuario AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.id = ?""",
        (gasto_id,),
    ).fetchone()
    return APIResponse.success(_gasto_a_dict(db, gasto), 201)


def _obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar"):
    """Devuelve (gasto, None) o (None, respuesta_error) tras comprobar permiso."""
    gasto = db.execute("SELECT * FROM gastos WHERE id = ?", (gasto_id,)).fetchone()
    if not gasto:
        return None, APIResponse.no_encontrado("recurso_gasto")

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido=nivel_requerido)
    if not hogar_id or gasto["hogar_id"] != hogar_id:
        return None, APIResponse.no_permitido()

    return gasto, None


@bp.route("/<int:gasto_id>", methods=["PUT", "PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_gasto(gasto_id):
    """Actualiza descripción/importe/reparto de un gasto (requiere nivel editar)."""
    db = get_db()
    gasto, error = _obtener_gasto_con_permiso(db, gasto_id)
    if error:
        return error

    datos = request.get_json(force=True) or {}
    actualizaciones = {}
    parametros = []

    if "descripcion" in datos:
        actualizaciones["descripcion"] = "?"
        parametros.append(Validator.string_requerido(datos.get("descripcion"), "descripción", 200))

    if "fecha" in datos:
        actualizaciones["fecha"] = "?"
        parametros.append(Validator.string_requerido(datos.get("fecha"), "fecha", 30))

    nuevo_importe_total = gasto["importe_total"]
    if "importe_total" in datos:
        nuevo_importe_total = Validator.decimal_positivo(datos.get("importe_total"), "importe total")
        actualizaciones["importe_total"] = "?"
        parametros.append(nuevo_importe_total)

    if "usuario_pagador_id" in datos:
        miembros_ids = _miembros_hogar_ids(db, gasto["hogar_id"])
        usuario_pagador_id = datos.get("usuario_pagador_id")
        if usuario_pagador_id not in miembros_ids:
            raise ValidationError("El pagador debe ser miembro del hogar")
        actualizaciones["usuario_pagador_id"] = "?"
        parametros.append(usuario_pagador_id)

    if actualizaciones:
        parametros.append(gasto_id)
        campos = ", ".join(f"{k} = {v}" for k, v in actualizaciones.items())
        db.execute(f"UPDATE gastos SET {campos} WHERE id = ?", parametros)

    if "participantes" in datos:
        participantes = datos.get("participantes")
        if not isinstance(participantes, list) or not participantes:
            raise ValidationError("El gasto debe tener al menos un participante")

        miembros_ids = _miembros_hogar_ids(db, gasto["hogar_id"])
        reparto = []
        suma_reparto = 0.0
        for participante in participantes:
            usuario_id = participante.get("usuario_id")
            if usuario_id not in miembros_ids:
                raise ValidationError("Todos los participantes deben ser miembros del hogar")
            importe = Validator.decimal_positivo(participante.get("importe"), "importe del participante")
            reparto.append((usuario_id, importe))
            suma_reparto += importe

        if abs(suma_reparto - nuevo_importe_total) > TOLERANCIA_REPARTO:
            raise ValidationError("La suma del reparto no coincide con el importe total")

        db.execute("DELETE FROM gastos_participantes WHERE gasto_id = ?", (gasto_id,))
        for usuario_id, importe in reparto:
            db.execute(
                "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
                (gasto_id, usuario_id, importe),
            )

    db.commit()

    gasto = db.execute(
        """SELECT g.*, u.nombre_usuario AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.id = ?""",
        (gasto_id,),
    ).fetchone()
    return APIResponse.success(_gasto_a_dict(db, gasto))


@bp.route("/<int:gasto_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_gasto(gasto_id):
    """Elimina un gasto (requiere nivel editar sobre el hogar)."""
    db = get_db()
    gasto, error = _obtener_gasto_con_permiso(db, gasto_id)
    if error:
        return error

    db.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
    db.commit()
    return APIResponse.success()


@bp.route("/saldo", methods=["GET"])
@requerir_sesion
@manejo_errores
def saldo_hogar():
    """Saldo neto por miembro del hogar activo: positivo = le deben, negativo = debe."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    filas = db.execute(
        """SELECT u.id, u.nombre_usuario,
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
           ORDER BY u.nombre_usuario""",
        (hogar_id, hogar_id, hogar_id, hogar_id, hogar_id, hogar_id),
    ).fetchall()

    return APIResponse.success([
        {"usuario_id": f["id"], "nombre_usuario": f["nombre_usuario"], "saldo": round(f["saldo"], 2)}
        for f in filas
    ])


@bp.route("/liquidaciones", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_liquidacion():
    """Registra que un miembro ha pagado a otro para saldar (parte de) el saldo."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    usuario_origen_id = datos.get("usuario_origen_id")
    usuario_destino_id = datos.get("usuario_destino_id")
    importe = Validator.decimal_positivo(datos.get("importe"), "importe")
    nota = Validator.string_opcional(datos.get("nota"), None, 200)

    if usuario_origen_id == usuario_destino_id:
        raise ValidationError("El origen y el destino de la liquidación deben ser distintos")

    miembros_ids = _miembros_hogar_ids(db, hogar_id)
    if usuario_origen_id not in miembros_ids or usuario_destino_id not in miembros_ids:
        raise ValidationError("Origen y destino deben ser miembros del hogar")

    db.execute(
        """INSERT INTO liquidaciones (hogar_id, usuario_origen_id, usuario_destino_id, importe, fecha, nota)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (hogar_id, usuario_origen_id, usuario_destino_id, importe, ahora(), nota),
    )
    db.commit()
    return APIResponse.success({"exito": True}, 201)
