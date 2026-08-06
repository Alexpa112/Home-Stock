"""Autenticación: login, registro, logout y gestión de usuarios."""
import hashlib
import io
import json
import secrets
import time
import zipfile

from flask import Blueprint, Response, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..api import APIResponse, manejo_errores, requerir_sesion
from ..config import APP_URL, LONGITUD_PASSWORD_MINIMA, REGISTRO_ABIERTO, VERSION_TERMINOS
from ..db import ahora, get_db
from ..red import ip_cliente, limite_por_ip
from ..servicios import auditoria, intentos_login
from ..servicios.email_service import EmailService
from ..servicios.password_pwned import es_password_filtrada
from ..utils import Validator, DataConverter

bp = Blueprint("auth", __name__)

# Endpoints accesibles sin haber iniciado sesion (usados por el guardian
# global en __init__.py).
RUTAS_PUBLICAS = {
    "auth.estado",
    "auth.login",
    "auth.registrar",
    "auth.verificar_codigo_dos_pasos",
    "auth.reenviar_codigo_dos_pasos",
    "auth.verificar_email",
    "auth.solicitar_reset_password",
    "auth.restablecer_password",
    "oauth.oauth_google",
    "oauth.oauth_google_callback",
    "oauth.oauth_apple",
    "oauth.oauth_apple_callback",
    "paginas.log_client_error",
    "paginas.csrf_token",
    "paginas.mantenimiento_estado",
    "idiomas.obtener_todas_traducciones",
    "idiomas.obtener_idioma",
    "legal.configuracion_legal",
}

DURACION_TOKEN_VERIFICACION_SEGUNDOS = 24 * 60 * 60
DURACION_TOKEN_RESET_SEGUNDOS = 60 * 60


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hay_usuarios(db):
    return db.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] > 0


def usuario_actual():
    return session.get("usuario")


@bp.route("/api/auth/estado")
@manejo_errores
def estado():
    db = get_db()
    email = None
    nombre = None
    tema_preferido = "auto"
    idioma_preferido = "es"
    teclado_virtual_activo = "on"
    vista_lista_compra = "lista"
    agrupar_categorias = "off"
    doble_factor_activo = False
    email_verificado = False
    ocr_local = False
    terminos_pendientes = False
    usuario_id = session.get("usuario_id")
    if usuario_id is not None:
        fila = db.execute(
            "SELECT email, nombre, tema_preferido, idioma_preferido, teclado_virtual_activo, vista_lista_compra, agrupar_categorias, doble_factor_activo, email_verificado, usuario_ocr_local, terminos_version_aceptada FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        if fila:
            email = fila["email"]
            nombre = fila["nombre"]
            tema_preferido = fila["tema_preferido"]
            idioma_preferido = fila["idioma_preferido"]
            teclado_virtual_activo = fila["teclado_virtual_activo"]
            vista_lista_compra = fila["vista_lista_compra"]
            agrupar_categorias = fila["agrupar_categorias"]
            doble_factor_activo = bool(fila["doble_factor_activo"])
            email_verificado = bool(fila["email_verificado"])
            ocr_local = bool(fila["usuario_ocr_local"])
            terminos_pendientes = fila["terminos_version_aceptada"] != VERSION_TERMINOS
    return APIResponse.success(
        {
            "necesita_setup": not hay_usuarios(db),
            "usuario": usuario_actual(),
            "usuario_id": usuario_id,
            "nombre": nombre,
            "email": email,
            "tema_preferido": tema_preferido,
            "idioma_preferido": idioma_preferido,
            "teclado_virtual_activo": teclado_virtual_activo,
            "vista_lista_compra": vista_lista_compra,
            "agrupar_categorias": agrupar_categorias,
            "doble_factor_activo": doble_factor_activo,
            "email_verificado": email_verificado,
            "ocr_local": ocr_local,
            "terminos_pendientes": terminos_pendientes,
        }
    )


@bp.route("/api/auth/registrar", methods=["POST"])
@manejo_errores
def registrar():
    if not REGISTRO_ABIERTO:
        return APIResponse.error("err_registro_cerrado", 403)

    db = get_db()
    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)
    password = datos.get("password") or ""

    if len(password) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_password_min_8")

    if not datos.get("acepta_terminos"):
        return APIResponse.validacion("err_debe_aceptar_terminos")

    if es_password_filtrada(password):
        return APIResponse.validacion("err_password_filtrada")

    existente = db.execute(
        "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
    ).fetchone()
    if existente:
        return APIResponse.error("err_usuario_duplicado", 400)

    db.execute(
        "INSERT INTO usuarios (nombre_usuario, password_hash, fecha_creacion, terminos_version_aceptada, terminos_fecha_aceptacion) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre_usuario, generate_password_hash(password), ahora(), VERSION_TERMINOS, ahora()),
    )

    # Iniciar sesión automáticamente después de registrar
    usuario = db.execute(
        "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
    ).fetchone()

    auditoria.registrar(db, "registro", usuario_id=usuario["id"], ip=ip_cliente())
    db.commit()

    session.permanent = True
    session["usuario"] = nombre_usuario
    session["usuario_id"] = usuario["id"]
    session["session_version"] = 0

    return APIResponse.success({"creado": True, "usuario": nombre_usuario}, 201)


@bp.route("/api/auth/login", methods=["POST"])
@manejo_errores
def login():
    ip = ip_cliente()
    datos = request.get_json(force=True) or {}
    nombre_usuario = Validator.string_requerido(datos.get("usuario"), "usuario", 50)

    if intentos_login.bloqueada(ip, nombre_usuario):
        return APIResponse.error("err_demasiados_intentos_login", 429)

    password = datos.get("password") or ""

    db = get_db()
    fila = db.execute(
        "SELECT * FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?)", (nombre_usuario,)
    ).fetchone()
    if fila is None or not check_password_hash(fila["password_hash"], password):
        intentos_login.registrar_fallo(ip, nombre_usuario)
        auditoria.registrar(db, "login", usuario_id=fila["id"] if fila else None, ip=ip, resultado="fallo", usuario_intentado=nombre_usuario)
        db.commit()
        return APIResponse.no_autorizado()

    intentos_login.limpiar_exito(ip, nombre_usuario)
    auditoria.registrar(db, "login", usuario_id=fila["id"], ip=ip, resultado="ok")
    db.commit()

    if fila["doble_factor_activo"] and fila["email"]:
        _generar_y_enviar_codigo(db, fila["id"], fila["email"])
        session["pendiente_2fa_usuario_id"] = fila["id"]
        return APIResponse.success({"requiere_codigo": True})

    session.permanent = True
    session["usuario"] = fila["nombre_usuario"]
    session["usuario_id"] = fila["id"]
    session["session_version"] = fila["session_version"]
    return APIResponse.success({"usuario": fila["nombre_usuario"]})


def _generar_y_enviar_codigo(db, usuario_id, email):
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.execute(
        "INSERT INTO codigos_dos_factor (usuario_id, codigo_hash, expira, intentos) VALUES (?, ?, ?, 0) "
        "ON CONFLICT(usuario_id) DO UPDATE SET codigo_hash = excluded.codigo_hash, expira = excluded.expira, intentos = 0",
        (usuario_id, _hash_codigo(codigo), int(time.time()) + DURACION_CODIGO_SEGUNDOS),
    )
    db.commit()
    EmailService.enviar_codigo_verificacion(email, codigo)


def _hash_codigo(codigo):
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


DURACION_CODIGO_SEGUNDOS = 10 * 60
MAX_INTENTOS_CODIGO = 5


@bp.route("/api/auth/verificar-codigo", methods=["POST"])
@manejo_errores
def verificar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    datos = request.get_json(force=True) or {}
    codigo = (datos.get("codigo") or "").strip()

    db = get_db()
    fila = db.execute(
        "SELECT codigo_hash, expira, intentos FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()

    if fila is None or fila["intentos"] >= MAX_INTENTOS_CODIGO or fila["expira"] < int(time.time()):
        session.pop("pendiente_2fa_usuario_id", None)
        return APIResponse.error("err_codigo_expirado", 400)

    if _hash_codigo(codigo) != fila["codigo_hash"]:
        db.execute("UPDATE codigos_dos_factor SET intentos = intentos + 1 WHERE usuario_id = ?", (usuario_id,))
        db.commit()
        return APIResponse.error("err_codigo_incorrecto", 400)

    db.execute("DELETE FROM codigos_dos_factor WHERE usuario_id = ?", (usuario_id,))
    db.commit()
    usuario = db.execute("SELECT nombre_usuario, session_version FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    session.pop("pendiente_2fa_usuario_id", None)
    session.permanent = True
    session["usuario"] = usuario["nombre_usuario"]
    session["usuario_id"] = usuario_id
    session["session_version"] = usuario["session_version"]
    return APIResponse.success({"usuario": usuario["nombre_usuario"]})


@bp.route("/api/auth/reenviar-codigo", methods=["POST"])
@manejo_errores
def reenviar_codigo_dos_pasos():
    usuario_id = session.get("pendiente_2fa_usuario_id")
    if usuario_id is None:
        return APIResponse.no_autorizado()

    db = get_db()
    fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if fila is None or not fila["email"]:
        return APIResponse.no_autorizado()

    _generar_y_enviar_codigo(db, usuario_id, fila["email"])
    return APIResponse.success({"reenviado": True})


@bp.route("/api/auth/doble-factor", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_doble_factor():
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    activar = bool(datos.get("activo"))

    db = get_db()
    if activar:
        fila = db.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not fila or not fila["email"]:
            return APIResponse.error("err_doble_factor_requiere_email", 400)

    db.execute("UPDATE usuarios SET doble_factor_activo = ? WHERE id = ?", (int(activar), usuario_id))
    if not activar:
        # Desactivar 2FA reduce la seguridad de la cuenta: invalida otras
        # sesiones que pudieran haber quedado abiertas con el 2FA aun
        # activo, para que el cambio se note de verdad (S-08). Refresca la
        # propia sesion a la nueva version para no cerrarse a si mismo.
        db.execute("UPDATE usuarios SET session_version = session_version + 1 WHERE id = ?", (usuario_id,))
        nueva_version = db.execute("SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()["session_version"]
        session["session_version"] = nueva_version
    auditoria.registrar(db, "cambio_2fa", usuario_id=usuario_id, ip=ip_cliente(), activo=activar)
    db.commit()
    return APIResponse.success({"doble_factor_activo": activar})


@bp.route("/api/auth/aceptar-terminos", methods=["POST"])
@requerir_sesion
@manejo_errores
def aceptar_terminos():
    """Registra la aceptación de la versión vigente de Términos y Privacidad.

    Cubre tanto al usuario que se registra por Google/Apple (no pasa por el
    formulario de registro, así que no acepta ahí) como al que ya tenía
    cuenta antes de introducir esta versión de los términos.
    """
    usuario_id = session.get("usuario_id")
    db = get_db()
    db.execute(
        "UPDATE usuarios SET terminos_version_aceptada = ?, terminos_fecha_aceptacion = ? WHERE id = ?",
        (VERSION_TERMINOS, ahora(), usuario_id),
    )
    db.commit()
    return APIResponse.success({"version_terminos": VERSION_TERMINOS})


@bp.route("/api/auth/logout", methods=["POST"])
@requerir_sesion
@manejo_errores
def logout():
    session.clear()
    return APIResponse.success()


@bp.route("/api/auth/perfil", methods=["PUT"])
@requerir_sesion
@manejo_errores
def actualizar_perfil():
    """Actualizar usuario (login), nombre a mostrar y/o contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    nombre_usuario_nuevo = datos.get("usuario", "").strip()
    nombre = datos.get("nombre", "").strip()
    password = datos.get("password", "").strip()

    db = get_db()
    usuario = db.execute(
        "SELECT nombre_usuario FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Actualizar usuario (login) si se proporciona
    if nombre_usuario_nuevo:
        if len(nombre_usuario_nuevo) > 80:
            return APIResponse.validacion("err_nombre_max_80")
        duplicado = db.execute(
            "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?) AND id != ?",
            (nombre_usuario_nuevo, usuario_id)
        ).fetchone()
        if duplicado:
            return APIResponse.error("err_usuario_duplicado", 400)
        db.execute(
            "UPDATE usuarios SET nombre_usuario = ? WHERE id = ?",
            (nombre_usuario_nuevo, usuario_id)
        )
        session["usuario"] = nombre_usuario_nuevo

    # Actualizar nombre a mostrar si se proporciona (independiente del usuario de login)
    if nombre:
        if len(nombre) > 80:
            return APIResponse.validacion("err_nombre_max_80")
        db.execute(
            "UPDATE usuarios SET nombre = ? WHERE id = ?",
            (nombre, usuario_id)
        )

    # Actualizar contraseña si se proporciona
    if password:
        if len(password) < LONGITUD_PASSWORD_MINIMA:
            return APIResponse.validacion("err_password_min_8")
        nuevo_hash = generate_password_hash(password)
        db.execute(
            "UPDATE usuarios SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
            (nuevo_hash, usuario_id)
        )
        session["session_version"] = db.execute(
            "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()["session_version"]
        auditoria.registrar(db, "cambio_password", usuario_id=usuario_id, ip=ip_cliente())

    db.commit()
    fila = db.execute("SELECT nombre FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return APIResponse.success({"usuario": session.get("usuario"), "nombre": fila["nombre"] if fila else None})


@bp.route("/api/auth/tema", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_tema():
    """Guarda la preferencia de tema (light/dark/auto) del usuario."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    tema = (datos.get("tema") or "auto").strip().lower()

    if tema not in ("light", "dark", "auto"):
        return APIResponse.validacion("Tema no válido. Debe ser 'light', 'dark' o 'auto'")

    db = get_db()
    db.execute("UPDATE usuarios SET tema_preferido = ? WHERE id = ?", (tema, usuario_id))
    db.commit()

    return APIResponse.success({"tema": tema})


@bp.route("/api/auth/teclado-virtual", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_teclado_virtual():
    """Guarda si el usuario quiere el teclado virtual propio (on/off)."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    valor = (datos.get("teclado_virtual_activo") or "on").strip().lower()

    if valor not in ("on", "off"):
        return APIResponse.validacion("Valor no válido. Debe ser 'on' u 'off'")

    db = get_db()
    db.execute("UPDATE usuarios SET teclado_virtual_activo = ? WHERE id = ?", (valor, usuario_id))
    db.commit()

    return APIResponse.success({"teclado_virtual_activo": valor})


@bp.route("/api/auth/preferencia-ocr", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_preferencia_ocr():
    """Opt-out del OCR en la nube (S-26): con ocr_local=True, el escaneo de
    tickets usa solo el pipeline local (Tesseract) sin enviar la foto a
    Groq, ver stockhogar/rutas/tickets.py::analizar_ticket."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    ocr_local = bool(datos.get("ocr_local"))

    db = get_db()
    db.execute("UPDATE usuarios SET usuario_ocr_local = ? WHERE id = ?", (int(ocr_local), usuario_id))
    db.commit()
    return APIResponse.success({"ocr_local": ocr_local})


@bp.route("/api/auth/cambiar-password", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_password():
    """Cambiar contraseña del usuario actual."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}
    password_actual = datos.get("password_actual") or ""
    password_nueva = datos.get("password_nueva") or ""
    password_confirmacion = datos.get("password_confirmacion") or ""

    # Validar contraseña nueva
    if len(password_nueva) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_nueva_password_min_8")

    if password_nueva != password_confirmacion:
        return APIResponse.validacion("error_contrasenas_no_coinciden")

    db = get_db()
    usuario = db.execute(
        "SELECT password_hash FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    if not usuario:
        return APIResponse.no_autorizado()

    # Verificar contraseña actual
    if not check_password_hash(usuario["password_hash"], password_actual):
        return APIResponse.error("err_password_actual_incorrecta", 400)

    # Actualizar contraseña. session_version + 1 invalida cualquier otra
    # sesion abierta con esta cuenta (S-08) - la propia se refresca abajo.
    nuevo_hash = generate_password_hash(password_nueva)
    db.execute(
        "UPDATE usuarios SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
        (nuevo_hash, usuario_id)
    )
    session["session_version"] = db.execute(
        "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()["session_version"]
    auditoria.registrar(db, "cambio_password", usuario_id=usuario_id, ip=ip_cliente())
    db.commit()

    return APIResponse.success({"mensaje": "Contraseña cambiada correctamente"})


@bp.route("/api/auth/cerrar-otras-sesiones", methods=["POST"])
@requerir_sesion
@manejo_errores
def cerrar_otras_sesiones():
    """Invalida cualquier otra sesion abierta con esta cuenta (S-08), sin
    cerrar la que hace la peticion: incrementa session_version en BD y
    refresca la propia sesion al nuevo valor."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    db.execute("UPDATE usuarios SET session_version = session_version + 1 WHERE id = ?", (usuario_id,))
    session["session_version"] = db.execute(
        "SELECT session_version FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()["session_version"]
    auditoria.registrar(db, "cerrar_otras_sesiones", usuario_id=usuario_id, ip=ip_cliente())
    db.commit()
    return APIResponse.success({"mensaje": "sesiones_cerradas_confirmacion"})


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
            f"SELECT sh.hogar_id, p.nombre, sh.cantidad, sh.stock_minimo, sh.fecha_actualizacion "  # nosec B608
            f"FROM stock_hogar sh JOIN productos p ON p.id = sh.producto_id WHERE sh.hogar_id IN ({placeholders})",
            ids_hogares,
        )
        articulos_compra = _filas_a_lista(
            db,
            f"SELECT hogar_id, nombre, cantidad, unidad, activo, fecha_creacion FROM articulos_compra "  # nosec B608
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
            zf.writestr(f"recibos/gasto_{recibo['id']}.{extension}", recibo["imagen_recibo"])

    buffer.seek(0)
    return Response(
        buffer.read(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=mis-datos-dreame.zip"},
    )


@bp.route("/api/auth/enviar-verificacion-email", methods=["POST"])
@requerir_sesion
@manejo_errores
def enviar_verificacion_email():
    """Genera un token de un solo uso y envia el enlace de verificacion de
    email (S-07). Invalida cualquier token previo no usado del mismo tipo
    para este usuario, para que solo el ultimo enlace enviado sea valido."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    fila = db.execute("SELECT nombre_usuario, email, email_verificado FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if not fila or not fila["email"]:
        return APIResponse.error("err_email_no_configurado", 400)
    if fila["email_verificado"]:
        return APIResponse.error("err_email_ya_verificado", 400)

    db.execute(
        "UPDATE tokens_verificacion SET usado = 1 WHERE usuario_id = ? AND tipo = 'verificar_email' AND usado = 0",
        (usuario_id,),
    )
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira) VALUES (?, 'verificar_email', ?, ?)",
        (usuario_id, _hash_token(token), int(time.time()) + DURACION_TOKEN_VERIFICACION_SEGUNDOS),
    )
    db.commit()

    EmailService.enviar_verificacion_email(fila["email"], fila["nombre_usuario"], token)
    return APIResponse.success({"mensaje": "verificacion_email_enviada"})


@bp.route("/api/auth/verificar-email/<token>", methods=["GET"])
@manejo_errores
def verificar_email(token):
    db = get_db()
    fila = db.execute(
        "SELECT id, usuario_id, expira, usado FROM tokens_verificacion WHERE token_hash = ? AND tipo = 'verificar_email'",
        (_hash_token(token),),
    ).fetchone()

    if fila is None:
        return APIResponse.error("err_token_invalido", 400)
    if fila["usado"]:
        return APIResponse.error("err_token_usado", 400)
    if fila["expira"] < int(time.time()):
        return APIResponse.error("err_token_expirado", 400)

    db.execute("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (fila["usuario_id"],))
    db.execute("UPDATE tokens_verificacion SET usado = 1 WHERE id = ?", (fila["id"],))
    db.commit()
    return APIResponse.success({"mensaje": "email_verificado_ok"})


@bp.route("/api/auth/solicitar-reset-password", methods=["POST"])
@manejo_errores
def solicitar_reset_password():
    """Solicitud publica de restablecimiento de contraseña. Responde SIEMPRE
    con el mismo mensaje generico, exista o no la cuenta (S-10, mismo
    principio anti-enumeracion), y solo envia email si existe y tiene un
    email verificado."""
    ip = ip_cliente()
    if limite_por_ip(f"reset_password:{ip}", 5, 60 * 60):
        return APIResponse.error("err_demasiadas_peticiones", 429)

    datos = request.get_json(force=True) or {}
    identificador = (datos.get("usuario_o_email") or "").strip()
    respuesta_generica = APIResponse.success({"mensaje": "mensaje_reset_generico"})
    if not identificador:
        return respuesta_generica

    db = get_db()
    fila = db.execute(
        "SELECT id, nombre_usuario, email, email_verificado FROM usuarios "
        "WHERE LOWER(nombre_usuario) = LOWER(?) OR LOWER(email) = LOWER(?)",
        (identificador, identificador),
    ).fetchone()

    if fila and fila["email"] and fila["email_verificado"]:
        db.execute(
            "UPDATE tokens_verificacion SET usado = 1 WHERE usuario_id = ? AND tipo = 'reset_password' AND usado = 0",
            (fila["id"],),
        )
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO tokens_verificacion (usuario_id, tipo, token_hash, expira) VALUES (?, 'reset_password', ?, ?)",
            (fila["id"], _hash_token(token), int(time.time()) + DURACION_TOKEN_RESET_SEGUNDOS),
        )
        db.commit()
        EmailService.enviar_recuperacion_password(fila["email"], fila["nombre_usuario"], token)

    return respuesta_generica


@bp.route("/api/auth/restablecer-password", methods=["POST"])
@manejo_errores
def restablecer_password():
    datos = request.get_json(force=True) or {}
    token = (datos.get("token") or "").strip()
    password_nueva = datos.get("password_nueva") or ""

    if len(password_nueva) < LONGITUD_PASSWORD_MINIMA:
        return APIResponse.validacion("err_password_min_8")
    if es_password_filtrada(password_nueva):
        return APIResponse.validacion("err_password_filtrada")

    db = get_db()
    fila = db.execute(
        "SELECT id, usuario_id, expira, usado FROM tokens_verificacion WHERE token_hash = ? AND tipo = 'reset_password'",
        (_hash_token(token),),
    ).fetchone()

    if fila is None:
        return APIResponse.error("err_token_invalido", 400)
    if fila["usado"]:
        return APIResponse.error("err_token_usado", 400)
    if fila["expira"] < int(time.time()):
        return APIResponse.error("err_token_expirado", 400)

    # session_version + 1 invalida todas las sesiones activas de esta cuenta
    # (S-08): si el token se filtro/uso por error, quien tuviera una sesion
    # abierta con la contraseña vieja tambien queda fuera.
    db.execute(
        "UPDATE usuarios SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
        (generate_password_hash(password_nueva), fila["usuario_id"]),
    )
    db.execute("UPDATE tokens_verificacion SET usado = 1 WHERE id = ?", (fila["id"],))
    auditoria.registrar(db, "reset_password", usuario_id=fila["usuario_id"], ip=ip_cliente())
    db.commit()
    return APIResponse.success({"mensaje": "password_restablecida_ok"})


@bp.route("/api/auth/preferencias-listas", methods=["POST"])
@requerir_sesion
@manejo_errores
def actualizar_preferencias_listas():
    """Actualiza las preferencias de vista de la lista de la compra (lista/recuadros) y agrupación por categorías."""
    usuario_id = session.get("usuario_id")
    datos = request.get_json(force=True) or {}

    vista = (datos.get("vista_lista_compra") or "lista").strip().lower()
    agrupar = (datos.get("agrupar_categorias") or "off").strip().lower()

    if vista not in ("lista", "recuadros"):
        return APIResponse.validacion("Vista no válida. Debe ser 'lista' o 'recuadros'")
    if agrupar not in ("on", "off"):
        return APIResponse.validacion("Agrupación no válida. Debe ser 'on' u 'off'")

    db = get_db()
    db.execute(
        "UPDATE usuarios SET vista_lista_compra = ?, agrupar_categorias = ? WHERE id = ?",
        (vista, agrupar, usuario_id)
    )
    db.commit()

    return APIResponse.success({
        "vista_lista_compra": vista,
        "agrupar_categorias": agrupar
    })


@bp.route("/api/usuarios", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_usuarios():
    """Lista solo los usuarios con los que la sesión actual comparte al menos
    una lista (propia o compartida), nunca todos los usuarios de la instalación."""
    usuario_id = session.get("usuario_id")
    db = get_db()
    filas = db.execute(
        """
        SELECT DISTINCT u.id, u.nombre_usuario, u.fecha_creacion
        FROM usuarios u
        WHERE u.id = ?
           OR u.id IN (
                SELECT l.usuario_propietario_id FROM hogares l
                WHERE l.id IN (
                    SELECT id FROM hogares WHERE usuario_propietario_id = ?
                    UNION
                    SELECT hogar_id FROM permisos_hogar WHERE usuario_id = ?
                )
           )
           OR u.id IN (
                SELECT p.usuario_id FROM permisos_hogar p
                WHERE p.hogar_id IN (
                    SELECT id FROM hogares WHERE usuario_propietario_id = ?
                    UNION
                    SELECT hogar_id FROM permisos_hogar WHERE usuario_id = ?
                )
           )
        ORDER BY u.fecha_creacion
        """,
        (usuario_id, usuario_id, usuario_id, usuario_id, usuario_id),
    ).fetchall()
    return APIResponse.success([dict(f) for f in filas])


@bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
@requerir_sesion
@manejo_errores
def borrar_usuario(usuario_id):
    if session.get("usuario_id") != usuario_id:
        return APIResponse.no_permitido()

    db = get_db()
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
