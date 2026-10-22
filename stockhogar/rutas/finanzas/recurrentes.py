"""Gastos recurrentes: plantillas que se materializan como gastos al llegar su fecha."""
from .blueprint import bp
from .comunes import miembros_hogar_ids, validar_reparto
import calendar
from datetime import datetime, timedelta
from flask import session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...db import ahora, get_db
from ...servicios.stock import hogar_actual_con_permiso
from ...utils import Validator, ValidationError
from .categorias_gasto import normalizar_categoria_gasto


FRECUENCIAS_VALIDAS = {"semanal", "mensual", "anual"}


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


def generar_gastos_recurrentes_pendientes(db, hogar_id, usuario_id_actual):
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

        # Primero se calculan las ocurrencias pendientes (por si nadie abrio la app durante varios
        # periodos), parando en cuanto la siguiente supere fecha_fin; sin escribir nada todavia.
        proxima_fecha = recurrente["proxima_fecha"]
        activo = True
        fechas = []
        while activo and proxima_fecha <= hoy and len(fechas) < 400:  # tope por llamada
            fechas.append(proxima_fecha)
            siguiente_fecha = _siguiente_fecha(proxima_fecha, recurrente["frecuencia"])
            if recurrente["fecha_fin"] and siguiente_fecha > recurrente["fecha_fin"]:
                activo = False
            proxima_fecha = siguiente_fecha

        # Se RECLAMA el recurrente moviendo su puntero solo si sigue donde lo leimos. Esto corre en
        # un GET (nivel "ver"): dos peticiones simultaneas leian la misma proxima_fecha y cada una
        # insertaba las mismas ocurrencias (gastos duplicados). Solo la que consigue el UPDATE
        # (rowcount == 1) genera los gastos; la otra ve el puntero ya movido y se salta este recurrente.
        reclamado = db.execute(
            "UPDATE gastos_recurrentes SET proxima_fecha = ?, activo = ? "
            "WHERE id = ? AND proxima_fecha = ? AND activo = 1",
            (proxima_fecha, 1 if activo else 0, recurrente["id"], recurrente["proxima_fecha"]),
        )
        if reclamado.rowcount != 1:
            continue

        for fecha_ocurrencia in fechas:
            cur = db.execute(
                """INSERT INTO gastos
                   (hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, categoria, creado_por_usuario_id, fecha_creacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                (
                    hogar_id, recurrente["descripcion"], recurrente["importe_total"], fecha_ocurrencia + "T00:00:00",
                    recurrente["usuario_pagador_id"], recurrente["categoria"], usuario_id_actual, ahora(),
                ),
            )
            gasto_id = cur.fetchone()["id"]
            for p in participantes:
                db.execute(
                    "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
                    (gasto_id, p["usuario_id"], p["importe"]),
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

    datos = cuerpo_json()
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
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        if fecha_fin:
            datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError as e:
        raise ValidationError("Las fechas deben tener el formato AAAA-MM-DD") from e
    # Sin cota, fecha_inicio=1000-01-01 semanal generaba 55.000 gastos de golpe.
    if inicio < datetime.now() - timedelta(days=366):
        raise ValidationError("La fecha de inicio no puede ser anterior a un año")
    if fecha_fin and fecha_inicio > fecha_fin:
        raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio")

    miembros_ids = miembros_hogar_ids(db, hogar_id)
    if usuario_pagador_id not in miembros_ids:
        raise ValidationError("El pagador debe ser miembro del hogar")
    reparto = validar_reparto(participantes, miembros_ids, importe_total)

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

    generar_gastos_recurrentes_pendientes(db, hogar_id, session.get("usuario_id"))

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

    datos = cuerpo_json()
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
