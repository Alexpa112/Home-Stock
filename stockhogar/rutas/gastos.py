"""Gastos compartidos del hogar (division tipo Tricount): registro de quien
pago que y como se reparte entre los miembros, y saldo neto de cada uno."""
import calendar
import csv
import heapq
import io
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, Response, request, session

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import LIMITE_RECIBOS_DIARIO_POR_USUARIO
from ..db import ahora, get_db
from ..servicios.push_service import enviar_push_a_usuario
from ..servicios.stock import hogar_actual_con_permiso
from ..translator import traducir
from ..utils import Validator, ValidationError
from ..utils.imagenes import validar_y_recodificar
from .categorias_gasto import normalizar_categoria_gasto

bp = Blueprint("gastos", __name__, url_prefix="/api/gastos")

TOLERANCIA_REPARTO = 0.01

RECIBO_EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "heif"}
RECIBO_TAMANO_MAXIMO_MB = 8
RECIBO_MIME_POR_EXTENSION = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "heic": "image/heic", "heif": "image/heif",
}

FRECUENCIAS_VALIDAS = {"semanal", "mensual", "anual"}


def _miembros_hogar_ids(db, hogar_id):
    """IDs de usuario que pertenecen al hogar (propietario + permisos_hogar)."""
    filas = db.execute(
        "SELECT usuario_propietario_id AS id FROM hogares WHERE id = ? "
        "UNION SELECT usuario_id AS id FROM permisos_hogar WHERE hogar_id = ?",
        (hogar_id, hogar_id),
    ).fetchall()
    return {f["id"] for f in filas}


def _avisar_si_supera_presupuesto(db, hogar_id):
    """Notifica por push a los miembros del hogar la primera vez que el
    gasto del mes en curso supera el presupuesto mensual fijado (P-05); solo
    una vez por mes (presupuesto_ultimo_aviso_mes) para no espamear con cada
    gasto nuevo mientras se siga por encima."""
    hogar = db.execute(
        "SELECT presupuesto_mensual, presupuesto_ultimo_aviso_mes, nombre FROM hogares WHERE id = ?",
        (hogar_id,),
    ).fetchone()
    if not hogar or not hogar["presupuesto_mensual"] or hogar["presupuesto_mensual"] <= 0:
        return

    mes_actual = date.today().isoformat()[:7]
    if hogar["presupuesto_ultimo_aviso_mes"] == mes_actual:
        return

    prefijo_mes = mes_actual
    fila = db.execute(
        "SELECT COALESCE(SUM(importe_total), 0) AS total FROM gastos WHERE hogar_id = ? AND fecha LIKE ?",
        (hogar_id, f"{prefijo_mes}%"),
    ).fetchone()
    if fila["total"] < hogar["presupuesto_mensual"]:
        return

    db.execute(
        "UPDATE hogares SET presupuesto_ultimo_aviso_mes = ? WHERE id = ?", (mes_actual, hogar_id)
    )
    db.commit()

    for usuario_id in _miembros_hogar_ids(db, hogar_id):
        enviar_push_a_usuario(
            db, usuario_id,
            traducir("push_presupuesto_superado_titulo"),
            traducir("push_presupuesto_superado_cuerpo").format(nombre=hogar["nombre"]),
            url="/dashboard/gastos",
        )


def _gasto_a_dict(db, gasto):
    participantes = db.execute(
        """SELECT gp.usuario_id, gp.importe, COALESCE(u.nombre, u.nombre_usuario) AS nombre_usuario
           FROM gastos_participantes gp, usuarios u
           WHERE gp.usuario_id = u.id AND gp.gasto_id = ?
           ORDER BY COALESCE(u.nombre, u.nombre_usuario)""",
        (gasto["id"],),
    ).fetchall()
    return {
        "id": gasto["id"],
        "descripcion": gasto["descripcion"],
        "importe_total": gasto["importe_total"],
        "fecha": gasto["fecha"],
        "categoria": gasto["categoria"],
        "usuario_pagador_id": gasto["usuario_pagador_id"],
        "pagador_nombre": gasto["pagador_nombre"],
        "tiene_recibo": bool(gasto["imagen_recibo"]),
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

    _generar_gastos_recurrentes_pendientes(db, hogar_id, session.get("usuario_id"))

    gastos = db.execute(
        """SELECT g.*, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.hogar_id = ?
           ORDER BY g.fecha DESC, g.id DESC""",
        (hogar_id,),
    ).fetchall()

    return APIResponse.success([_gasto_a_dict(db, g) for g in gastos])


@bp.route("/resumen-mes", methods=["GET"])
@requerir_sesion
@manejo_errores
def resumen_mes():
    """Gasto acumulado del mes en curso frente al presupuesto mensual del
    hogar (P-05), para la barra de progreso/alerta en el frontend."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success({"gasto_mes": 0, "presupuesto_mensual": None, "porcentaje": None})

    prefijo_mes = date.today().isoformat()[:7]
    fila = db.execute(
        "SELECT COALESCE(SUM(importe_total), 0) AS total FROM gastos "
        "WHERE hogar_id = ? AND fecha LIKE ?",
        (hogar_id, f"{prefijo_mes}%"),
    ).fetchone()
    gasto_mes = fila["total"]

    hogar = db.execute("SELECT presupuesto_mensual FROM hogares WHERE id = ?", (hogar_id,)).fetchone()
    presupuesto_mensual = hogar["presupuesto_mensual"] if hogar else None

    porcentaje = None
    if presupuesto_mensual and presupuesto_mensual > 0:
        porcentaje = round((gasto_mes / presupuesto_mensual) * 100, 1)

    return APIResponse.success({
        "gasto_mes": gasto_mes,
        "presupuesto_mensual": presupuesto_mensual,
        "porcentaje": porcentaje,
    })


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
    categoria = normalizar_categoria_gasto(db, datos.get("categoria"))
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
           (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, categoria, creado_por_usuario_id, fecha_creacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, categoria, usuario_id_actual, ahora()),
    )
    gasto_id = cur.fetchone()["id"]

    for usuario_id, importe in reparto:
        db.execute(
            "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
            (gasto_id, usuario_id, importe),
        )
    db.commit()

    _avisar_si_supera_presupuesto(db, hogar_id)

    gasto = db.execute(
        """SELECT g.*, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
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

    if "categoria" in datos:
        actualizaciones["categoria"] = "?"
        parametros.append(normalizar_categoria_gasto(db, datos.get("categoria")))

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
        db.execute(f"UPDATE gastos SET {campos} WHERE id = ?", parametros)  # nosec B608

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
        """SELECT g.*, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
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


def _calcular_saldos(db, hogar_id):
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

    return APIResponse.success(_calcular_saldos(db, hogar_id))


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

    saldos = _calcular_saldos(db, hogar_id)
    return APIResponse.success(_simplificar_deudas(saldos))


def _formatear_decimal_csv(valor):
    """Coma decimal (no punto) porque el delimitador de columna es ';':
    así Excel en español reconoce el número en vez de leerlo como texto."""
    return f"{valor:.2f}".replace(".", ",")


@bp.route("/exportar", methods=["GET"])
@requerir_sesion
@manejo_errores
def exportar_gastos_csv():
    """Exporta los gastos del hogar activo a CSV, formato largo: una fila
    por (gasto, participante). Solo lectura: mismo nivel de permiso que
    listar_gastos/saldo_hogar (acceso 'ver' es suficiente)."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.no_permitido()

    gastos = db.execute(
        """SELECT g.*, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.hogar_id = ?
           ORDER BY g.fecha, g.id""",
        (hogar_id,),
    ).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([
        traducir("fecha"), traducir("descripcion"), traducir("categoria"),
        traducir("importe_total"), traducir("pagador"), traducir("participante"),
        traducir("importe_participante"), traducir("tipo"),
    ])

    for gasto in gastos:
        participantes = db.execute(
            """SELECT gp.importe, COALESCE(u.nombre, u.nombre_usuario) AS nombre_usuario
               FROM gastos_participantes gp, usuarios u
               WHERE gp.usuario_id = u.id AND gp.gasto_id = ?
               ORDER BY COALESCE(u.nombre, u.nombre_usuario)""",
            (gasto["id"],),
        ).fetchall()
        for participante in participantes:
            writer.writerow([
                gasto["fecha"],
                gasto["descripcion"],
                gasto["categoria"] or "",
                _formatear_decimal_csv(gasto["importe_total"]),
                gasto["pagador_nombre"],
                participante["nombre_usuario"],
                _formatear_decimal_csv(participante["importe"]),
                traducir("gasto"),
            ])

    liquidaciones = db.execute(
        """SELECT l.*, COALESCE(uo.nombre, uo.nombre_usuario) AS origen_nombre,
               COALESCE(ud.nombre, ud.nombre_usuario) AS destino_nombre
           FROM liquidaciones l, usuarios uo, usuarios ud
           WHERE l.usuario_origen_id = uo.id AND l.usuario_destino_id = ud.id AND l.hogar_id = ?
           ORDER BY l.fecha, l.id""",
        (hogar_id,),
    ).fetchall()
    for liquidacion in liquidaciones:
        writer.writerow([
            liquidacion["fecha"],
            liquidacion["nota"] or traducir("liquidacion"),
            "",
            _formatear_decimal_csv(liquidacion["importe"]),
            liquidacion["origen_nombre"],
            liquidacion["destino_nombre"],
            _formatear_decimal_csv(liquidacion["importe"]),
            traducir("liquidacion"),
        ])

    contenido = buffer.getvalue().encode("utf-8-sig")
    nombre_fichero = f"gastos_{ahora()[:10]}.csv"
    return Response(
        contenido,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


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


def _extension_recibo_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in RECIBO_EXTENSIONES_PERMITIDAS


@bp.route("/<int:gasto_id>/recibo", methods=["POST"])
@requerir_sesion
@manejo_errores
def subir_recibo(gasto_id):
    """Adjunta (o reemplaza) la foto de recibo de un gasto."""
    db = get_db()
    gasto, error = _obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar")
    if error:
        return error

    usuario_id = session.get("usuario_id")
    hoy = date.today().isoformat()
    uso_hoy = db.execute(
        "SELECT contador FROM uso_recibos_diario WHERE usuario_id = ? AND fecha = ?", (usuario_id, hoy)
    ).fetchone()
    if uso_hoy and uso_hoy["contador"] >= LIMITE_RECIBOS_DIARIO_POR_USUARIO:
        return APIResponse.error("err_limite_recibos_diario", 429)

    archivo = request.files.get("foto")
    if archivo is None or archivo.filename == "":
        return APIResponse.validacion("err_sin_imagen")
    if not _extension_recibo_permitida(archivo.filename):
        return APIResponse.validacion("err_formato_no_permitido")

    archivo.seek(0, 2)
    tamano_bytes = archivo.tell()
    archivo.seek(0)
    if tamano_bytes > RECIBO_TAMANO_MAXIMO_MB * 1024 * 1024:
        return APIResponse.validacion(
            traducir("err_archivo_muy_grande").replace("{mb}", str(RECIBO_TAMANO_MAXIMO_MB))
        )

    extension = Path(archivo.filename).suffix.lower().lstrip(".")
    mime_type = RECIBO_MIME_POR_EXTENSION.get(extension, "application/octet-stream")

    # Recodificar (S-16): confirma que el contenido es de verdad una imagen
    # del formato que dice la extension (no solo un fichero renombrado) y
    # descarta metadatos/bytes extra antes de guardarla en la BD a largo
    # plazo. HEIC/HEIF no pasa por Pillow (ver utils/imagenes.py) y se
    # guarda tal cual, igual que antes de este cambio.
    imagen_validada, error_validacion = validar_y_recodificar(archivo.read(), extension)
    if error_validacion:
        return APIResponse.validacion(error_validacion)

    db.execute(
        "UPDATE gastos SET imagen_recibo = ?, imagen_recibo_mime = ? WHERE id = ?",
        (imagen_validada, mime_type, gasto_id),
    )
    db.execute(
        "INSERT INTO uso_recibos_diario (usuario_id, fecha, contador) VALUES (?, ?, 1) "
        "ON CONFLICT(usuario_id, fecha) DO UPDATE SET contador = contador + 1",
        (usuario_id, hoy),
    )
    db.commit()
    return APIResponse.success({"tiene_recibo": True})


@bp.route("/<int:gasto_id>/recibo", methods=["GET"])
@requerir_sesion
@manejo_errores
def obtener_recibo(gasto_id):
    """Sirve la foto de recibo adjunta a un gasto."""
    db = get_db()
    gasto, error = _obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="ver")
    if error:
        return error
    if not gasto["imagen_recibo"]:
        return APIResponse.no_encontrado("recurso_recibo")

    return Response(gasto["imagen_recibo"], mimetype=gasto["imagen_recibo_mime"] or "application/octet-stream")


@bp.route("/<int:gasto_id>/recibo", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_recibo(gasto_id):
    """Elimina la foto de recibo adjunta a un gasto."""
    db = get_db()
    gasto, error = _obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar")
    if error:
        return error

    db.execute("UPDATE gastos SET imagen_recibo = NULL, imagen_recibo_mime = NULL WHERE id = ?", (gasto_id,))
    db.commit()
    return APIResponse.success()


def _siguiente_fecha(fecha_iso, frecuencia):
    """Avanza una fecha (YYYY-MM-DD) un periodo segun la frecuencia, ajustando
    al ultimo dia del mes destino si hace falta (p.ej. 31 ene -> 28/29 feb)."""
    fecha = datetime.fromisoformat(fecha_iso)

    if frecuencia == "semanal":
        fecha = fecha + timedelta(days=7)
    elif frecuencia == "anual":
        dia = min(fecha.day, calendar.monthrange(fecha.year + 1, fecha.month)[1])
        fecha = fecha.replace(year=fecha.year + 1, day=dia)
    else:  # mensual
        mes = fecha.month + 1
        anio = fecha.year + (1 if mes > 12 else 0)
        mes = 1 if mes > 12 else mes
        dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
        fecha = fecha.replace(year=anio, month=mes, day=dia)

    return fecha.strftime("%Y-%m-%d")


def _generar_gastos_recurrentes_pendientes(db, hogar_id, usuario_id_actual):
    """Materializa como gastos normales las ocurrencias de gastos recurrentes
    activos cuya proxima_fecha ya ha llegado, avanzando el puntero tantos
    periodos como haga falta (p.ej. si nadie abrio la app durante 2 meses)."""
    hoy = ahora()[:10]
    recurrentes = db.execute(
        "SELECT * FROM gastos_recurrentes WHERE hogar_id = ? AND activo = 1 AND proxima_fecha <= ?",
        (hogar_id, hoy),
    ).fetchall()
    if not recurrentes:
        return

    for recurrente in recurrentes:
        participantes = db.execute(
            "SELECT usuario_id, importe FROM gastos_recurrentes_participantes WHERE gasto_recurrente_id = ?",
            (recurrente["id"],),
        ).fetchall()

        proxima_fecha = recurrente["proxima_fecha"]
        activo = True
        # Genera todas las ocurrencias pendientes hasta hoy (por si nadie abrio
        # la app durante varios periodos), parando en cuanto la siguiente
        # ocurrencia calculada supere fecha_fin.
        while activo and proxima_fecha <= hoy:
            cur = db.execute(
                """INSERT INTO gastos
                   (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, categoria, creado_por_usuario_id, fecha_creacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                (
                    hogar_id, recurrente["descripcion"], recurrente["importe_total"], proxima_fecha + "T00:00:00",
                    recurrente["usuario_pagador_id"], recurrente["categoria"], usuario_id_actual, ahora(),
                ),
            )
            gasto_id = cur.fetchone()["id"]
            for p in participantes:
                db.execute(
                    "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
                    (gasto_id, p["usuario_id"], p["importe"]),
                )

            siguiente_fecha = _siguiente_fecha(proxima_fecha, recurrente["frecuencia"])
            if recurrente["fecha_fin"] and siguiente_fecha > recurrente["fecha_fin"]:
                activo = False
            proxima_fecha = siguiente_fecha

        db.execute(
            "UPDATE gastos_recurrentes SET proxima_fecha = ?, activo = ? WHERE id = ?",
            (proxima_fecha, 1 if activo else 0, recurrente["id"]),
        )

    db.commit()


def _gasto_recurrente_a_dict(db, recurrente):
    participantes = db.execute(
        """SELECT grp.usuario_id, grp.importe, COALESCE(u.nombre, u.nombre_usuario) AS nombre_usuario
           FROM gastos_recurrentes_participantes grp, usuarios u
           WHERE grp.usuario_id = u.id AND grp.gasto_recurrente_id = ?
           ORDER BY COALESCE(u.nombre, u.nombre_usuario)""",
        (recurrente["id"],),
    ).fetchall()
    return {
        "id": recurrente["id"],
        "descripcion": recurrente["descripcion"],
        "importe_total": recurrente["importe_total"],
        "categoria": recurrente["categoria"],
        "usuario_pagador_id": recurrente["usuario_pagador_id"],
        "frecuencia": recurrente["frecuencia"],
        "proxima_fecha": recurrente["proxima_fecha"],
        "fecha_fin": recurrente["fecha_fin"],
        "activo": bool(recurrente["activo"]),
        "participantes": [
            {"usuario_id": p["usuario_id"], "importe": p["importe"], "nombre_usuario": p["nombre_usuario"]}
            for p in participantes
        ],
    }


@bp.route("/recurrentes", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_gastos_recurrentes():
    """Lista las plantillas de gastos recurrentes del hogar activo."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    recurrentes = db.execute(
        "SELECT * FROM gastos_recurrentes WHERE hogar_id = ? ORDER BY proxima_fecha", (hogar_id,)
    ).fetchall()
    return APIResponse.success([_gasto_recurrente_a_dict(db, r) for r in recurrentes])


@bp.route("/recurrentes", methods=["POST"])
@requerir_sesion
@manejo_errores
def crear_gasto_recurrente():
    """Crea una plantilla de gasto recurrente (se generara como gasto normal
    a partir de fecha_inicio, cada periodo indicado en frecuencia)."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    descripcion = Validator.string_requerido(datos.get("descripcion"), "descripción", 200)
    importe_total = Validator.decimal_positivo(datos.get("importe_total"), "importe total")
    categoria = normalizar_categoria_gasto(db, datos.get("categoria"))
    usuario_pagador_id = datos.get("usuario_pagador_id")
    participantes = datos.get("participantes")
    frecuencia = datos.get("frecuencia")
    fecha_inicio = Validator.string_requerido(datos.get("fecha_inicio"), "fecha de inicio", 10)
    fecha_fin = Validator.string_opcional(datos.get("fecha_fin"), None, 10)

    if frecuencia not in FRECUENCIAS_VALIDAS:
        raise ValidationError("La frecuencia debe ser semanal, mensual o anual")
    if not isinstance(participantes, list) or not participantes:
        raise ValidationError("El gasto debe tener al menos un participante")

    try:
        datetime.strptime(fecha_inicio, "%Y-%m-%d")
        if fecha_fin:
            datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError as e:
        raise ValidationError("Las fechas deben tener el formato AAAA-MM-DD") from e
    if fecha_fin and fecha_inicio > fecha_fin:
        raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio")

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

    cur = db.execute(
        """INSERT INTO gastos_recurrentes
           (hogar_id, descripcion, importe_total, categoria, usuario_pagador_id, frecuencia,
            fecha_fin, proxima_fecha, activo, fecha_creacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?) RETURNING id""",
        (hogar_id, descripcion, importe_total, categoria, usuario_pagador_id, frecuencia,
         fecha_fin, fecha_inicio, ahora()),
    )
    recurrente_id = cur.fetchone()["id"]
    for usuario_id, importe in reparto:
        db.execute(
            "INSERT INTO gastos_recurrentes_participantes (gasto_recurrente_id, usuario_id, importe) VALUES (?, ?, ?)",
            (recurrente_id, usuario_id, importe),
        )
    db.commit()

    _generar_gastos_recurrentes_pendientes(db, hogar_id, session.get("usuario_id"))

    recurrente = db.execute("SELECT * FROM gastos_recurrentes WHERE id = ?", (recurrente_id,)).fetchone()
    return APIResponse.success(_gasto_recurrente_a_dict(db, recurrente), 201)


@bp.route("/recurrentes/<int:recurrente_id>", methods=["PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_gasto_recurrente(recurrente_id):
    """Pausa o reanuda una plantilla de gasto recurrente."""
    db = get_db()
    recurrente = db.execute("SELECT * FROM gastos_recurrentes WHERE id = ?", (recurrente_id,)).fetchone()
    if not recurrente:
        return APIResponse.no_encontrado("recurso_gasto_recurrente")

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id or recurrente["hogar_id"] != hogar_id:
        return APIResponse.no_permitido()

    datos = request.get_json(force=True) or {}
    if "activo" in datos:
        db.execute("UPDATE gastos_recurrentes SET activo = ? WHERE id = ?", (1 if datos["activo"] else 0, recurrente_id))
        db.commit()

    recurrente = db.execute("SELECT * FROM gastos_recurrentes WHERE id = ?", (recurrente_id,)).fetchone()
    return APIResponse.success(_gasto_recurrente_a_dict(db, recurrente))


@bp.route("/recurrentes/<int:recurrente_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_gasto_recurrente(recurrente_id):
    """Elimina una plantilla de gasto recurrente (no afecta a los gastos ya generados)."""
    db = get_db()
    recurrente = db.execute("SELECT * FROM gastos_recurrentes WHERE id = ?", (recurrente_id,)).fetchone()
    if not recurrente:
        return APIResponse.no_encontrado("recurso_gasto_recurrente")

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido="editar")
    if not hogar_id or recurrente["hogar_id"] != hogar_id:
        return APIResponse.no_permitido()

    db.execute("DELETE FROM gastos_recurrentes WHERE id = ?", (recurrente_id,))
    db.commit()
    return APIResponse.success()
