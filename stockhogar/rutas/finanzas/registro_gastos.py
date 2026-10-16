"""Alta, edicion, listado, resumen del mes y exportacion de gastos."""
from .blueprint import bp
from .comunes import COLUMNAS_GASTO, avisar_si_supera_presupuesto, gasto_a_dict, miembros_hogar_ids, obtener_gasto_con_permiso, participantes_del_hogar, validar_reparto
from .recurrentes import generar_gastos_recurrentes_pendientes
import io
from datetime import date
from flask import Response, session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json
from ...db import ahora, get_db
from ...servicios.stock import hogar_actual_con_permiso
from ...translator import traducir
from ...utils.csv_seguro import EscritorCsvSeguro
from ...utils import Validator, ValidationError
from .categorias_gasto import normalizar_categoria_gasto


@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_gastos():
    """Lista los gastos del hogar activo, más recientes primero."""
    db = get_db()
    hogar_id = hogar_actual_con_permiso(db, session)
    if not hogar_id:
        return APIResponse.success([])

    generar_gastos_recurrentes_pendientes(db, hogar_id, session.get("usuario_id"))

    gastos = db.execute(
        f"""SELECT {COLUMNAS_GASTO}, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.hogar_id = ?
           ORDER BY g.fecha DESC, g.id DESC""",  # nosec B608 - COLUMNAS_GASTO es una constante literal del modulo
        (hogar_id,),
    ).fetchall()

    participantes = participantes_del_hogar(db, hogar_id)
    return APIResponse.success(
        [gasto_a_dict(db, g, participantes.get(g["id"], [])) for g in gastos]
    )


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

    datos = cuerpo_json()
    descripcion = Validator.string_requerido(datos.get("descripcion"), "descripción", 200)
    importe_total = Validator.decimal_positivo(datos.get("importe_total"), "importe total")
    fecha = Validator.string_opcional(datos.get("fecha"), ahora(), 30)
    categoria = normalizar_categoria_gasto(db, datos.get("categoria"))
    usuario_pagador_id = datos.get("usuario_pagador_id")
    participantes = datos.get("participantes")

    miembros_ids = miembros_hogar_ids(db, hogar_id)
    if usuario_pagador_id not in miembros_ids:
        raise ValidationError("El pagador debe ser miembro del hogar")
    reparto = validar_reparto(participantes, miembros_ids, importe_total)

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

    avisar_si_supera_presupuesto(db, hogar_id)

    gasto = db.execute(
        f"""SELECT {COLUMNAS_GASTO}, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.id = ?""",  # nosec B608 - COLUMNAS_GASTO es una constante literal del modulo
        (gasto_id,),
    ).fetchone()
    return APIResponse.success(gasto_a_dict(db, gasto), 201)


@bp.route("/<int:gasto_id>", methods=["PUT", "PATCH"])
@requerir_sesion
@manejo_errores
def actualizar_gasto(gasto_id):
    """Actualiza descripción/importe/reparto de un gasto (requiere nivel editar)."""
    db = get_db()
    gasto, error = obtener_gasto_con_permiso(db, gasto_id)
    if error:
        return error

    datos = cuerpo_json()
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
        miembros_ids = miembros_hogar_ids(db, gasto["hogar_id"])
        usuario_pagador_id = datos.get("usuario_pagador_id")
        if usuario_pagador_id not in miembros_ids:
            raise ValidationError("El pagador debe ser miembro del hogar")
        actualizaciones["usuario_pagador_id"] = "?"
        parametros.append(usuario_pagador_id)

    if actualizaciones:
        parametros.append(gasto_id)
        campos = ", ".join(f"{k} = {v}" for k, v in actualizaciones.items())
        db.execute(f"UPDATE gastos SET {campos} WHERE id = ?", parametros)  # nosec B608 - claves de actualizaciones son literales fijos, nunca claves de datos

    if "participantes" in datos:
        reparto = validar_reparto(
            datos.get("participantes"), miembros_hogar_ids(db, gasto["hogar_id"]), nuevo_importe_total
        )

        db.execute("DELETE FROM gastos_participantes WHERE gasto_id = ?", (gasto_id,))
        for usuario_id, importe in reparto:
            db.execute(
                "INSERT INTO gastos_participantes (gasto_id, usuario_id, importe) VALUES (?, ?, ?)",
                (gasto_id, usuario_id, importe),
            )

    db.commit()

    gasto = db.execute(
        f"""SELECT {COLUMNAS_GASTO}, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.id = ?""",  # nosec B608 - COLUMNAS_GASTO es una constante literal del modulo
        (gasto_id,),
    ).fetchone()
    return APIResponse.success(gasto_a_dict(db, gasto))


@bp.route("/<int:gasto_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def eliminar_gasto(gasto_id):
    """Elimina un gasto (requiere nivel editar sobre el hogar)."""
    db = get_db()
    gasto, error = obtener_gasto_con_permiso(db, gasto_id)
    if error:
        return error

    db.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
    db.commit()
    return APIResponse.success()


def formatear_decimal_csv(valor):
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
        f"""SELECT {COLUMNAS_GASTO}, COALESCE(u.nombre, u.nombre_usuario) AS pagador_nombre
           FROM gastos g, usuarios u
           WHERE g.usuario_pagador_id = u.id AND g.hogar_id = ?
           ORDER BY g.fecha, g.id""",  # nosec B608 - COLUMNAS_GASTO es una constante literal del modulo
        (hogar_id,),
    ).fetchall()
    participantes_por_gasto = participantes_del_hogar(db, hogar_id)

    buffer = io.StringIO()
    writer = EscritorCsvSeguro(buffer)
    writer.writerow([
        traducir("fecha"), traducir("descripcion"), traducir("categoria"),
        traducir("importe_total"), traducir("pagador"), traducir("participante"),
        traducir("importe_participante"), traducir("tipo"),
    ])

    for gasto in gastos:
        for participante in participantes_por_gasto.get(gasto["id"], []):
            writer.writerow([
                gasto["fecha"],
                gasto["descripcion"],
                gasto["categoria"] or "",
                formatear_decimal_csv(gasto["importe_total"]),
                gasto["pagador_nombre"],
                participante["nombre_usuario"],
                formatear_decimal_csv(participante["importe"]),
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
            formatear_decimal_csv(liquidacion["importe"]),
            liquidacion["origen_nombre"],
            liquidacion["destino_nombre"],
            formatear_decimal_csv(liquidacion["importe"]),
            traducir("liquidacion"),
        ])

    contenido = buffer.getvalue().encode("utf-8-sig")
    nombre_fichero = f"gastos_{ahora()[:10]}.csv"
    return Response(
        contenido,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )
