"""Piezas compartidas por las rutas de gastos: miembros, reparto, aviso de presupuesto y serializacion."""
from datetime import date
from flask import session
from ...api import APIResponse
from ...servicios.notificaciones.push_service import enviar_push_a_usuario
from ...servicios.stock import hogar_actual_con_permiso
from ...translator import traducir
from ...utils import Validator, ValidationError


TOLERANCIA_REPARTO = 0.01


def miembros_hogar_ids(db, hogar_id):
    """IDs de usuario que pertenecen al hogar (propietario + permisos_hogar)."""
    filas = db.execute(
        "SELECT usuario_propietario_id AS id FROM hogares WHERE id = ? "
        "UNION SELECT usuario_id AS id FROM permisos_hogar WHERE hogar_id = ?",
        (hogar_id, hogar_id),
    ).fetchall()
    return {f["id"] for f in filas}


def validar_reparto(participantes, miembros_ids, importe_total):
    """Valida el reparto de un gasto (normal o recurrente) y lo devuelve como [(usuario_id, importe)].

    Cada participante debe ser un objeto con un usuario miembro del hogar y un importe > 0, y la
    suma debe coincidir con el total (tolerancia de un centimo)."""
    if not isinstance(participantes, list) or not participantes:
        raise ValidationError("El gasto debe tener al menos un participante")
    reparto = []
    suma_reparto = 0.0
    for participante in participantes:
        if not isinstance(participante, dict):
            raise ValidationError("cada participante debe ser un objeto JSON")
        usuario_id = participante.get("usuario_id")
        if usuario_id not in miembros_ids:
            raise ValidationError("Todos los participantes deben ser miembros del hogar")
        importe = Validator.decimal_positivo(participante.get("importe"), "importe del participante")
        reparto.append((usuario_id, importe))
        suma_reparto += importe
    if round(abs(suma_reparto - importe_total), 2) > TOLERANCIA_REPARTO:
        raise ValidationError("La suma del reparto no coincide con el importe total")
    return reparto


def avisar_si_supera_presupuesto(db, hogar_id):
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

    for usuario_id in miembros_hogar_ids(db, hogar_id):
        enviar_push_a_usuario(
            db, usuario_id,
            traducir("push_presupuesto_superado_titulo"),
            traducir("push_presupuesto_superado_cuerpo").format(nombre=hogar["nombre"]),
            url="/dashboard/gastos",
        )


# Columnas del gasto que necesita la respuesta JSON, en lugar de "g.*". El
# comodin arrastraba imagen_recibo, un BLOB con la foto del recibo, para
# terminar usandolo solo como bool(...): listar 300 gastos con recibo leia
# todas las fotos del disco y las descartaba. Aqui se sustituye por la
# comprobacion hecha en SQL, que no mueve los bytes.
COLUMNAS_GASTO = """g.id, g.descripcion, g.importe_total, g.fecha, g.categoria,
           g.usuario_pagador_id, (g.imagen_recibo IS NOT NULL) AS tiene_recibo"""


def participantes_del_hogar(db, hogar_id):
    """Participantes de TODOS los gastos del hogar en una consulta, agrupados
    por gasto_id.

    Antes se consultaba gasto por gasto dentro de gasto_a_dict: listar el
    hogar costaba una consulta por gasto (medido: 308 sentencias SQL con 300
    gastos). Se filtra por hogar_id en vez de por una lista IN (...) de ids
    para no depender de SQLITE_LIMIT_VARIABLE_NUMBER, que varia segun como se
    haya compilado SQLite en cada maquina.
    """
    filas = db.execute(
        """SELECT gp.gasto_id, gp.usuario_id, gp.importe,
               COALESCE(u.nombre, u.nombre_usuario) AS nombre_usuario
           FROM gastos_participantes gp, usuarios u, gastos g
           WHERE gp.usuario_id = u.id AND gp.gasto_id = g.id AND g.hogar_id = ?
           ORDER BY COALESCE(u.nombre, u.nombre_usuario)""",
        (hogar_id,),
    ).fetchall()
    agrupados = {}
    for fila in filas:
        agrupados.setdefault(fila["gasto_id"], []).append(fila)
    return agrupados


def gasto_a_dict(db, gasto, participantes=None):
    if participantes is None:
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
        "tiene_recibo": bool(gasto["tiene_recibo"]),
        "participantes": [
            {"usuario_id": p["usuario_id"], "importe": p["importe"], "nombre_usuario": p["nombre_usuario"]}
            for p in participantes
        ],
    }


def obtener_gasto_con_permiso(db, gasto_id, nivel_requerido="editar", con_imagen=False):
    """Devuelve (gasto, None) o (None, respuesta_error) tras comprobar permiso.

    `con_imagen` solo lo pide la ruta que sirve el recibo. El resto (editar,
    borrar, subir otra foto) no necesita los bytes de la imagen, y con SELECT *
    se leia el recibo entero del disco para acabar descartandolo.
    """
    columnas = "*" if con_imagen else (
        "id, hogar_id, descripcion, importe_total, fecha, usuario_pagador_id, "
        "creado_por_usuario_id, fecha_creacion, categoria, imagen_recibo_mime, "
        "(imagen_recibo IS NOT NULL) AS tiene_recibo"
    )
    gasto = db.execute(
        f"SELECT {columnas} FROM gastos WHERE id = ?",  # nosec B608 - `columnas` es uno de dos literales fijos de arriba
        (gasto_id,),
    ).fetchone()
    if not gasto:
        return None, APIResponse.no_encontrado("recurso_gasto")

    hogar_id = hogar_actual_con_permiso(db, session, nivel_requerido=nivel_requerido)
    if not hogar_id or gasto["hogar_id"] != hogar_id:
        return None, APIResponse.no_permitido()

    return gasto, None
