"""Perfil y preferencias del usuario (nombre, email, tema, teclado, OCR, listas, terminos)."""
from .blueprint import bp
from .comunes import email_valido, enviar_token_verificacion_email, password_valida
import time

from flask import session
from ...api import APIResponse, manejo_errores, requerir_sesion, cuerpo_json, texto_json
from ...config import VERSION_TERMINOS
from ...db import ahora, get_db

# Un inicio de sesion mas viejo que esto no basta para cambiar el email de una cuenta sin contrasena.
VENTANA_REAUTENTICACION_S = 10 * 60


def _validar_cambios_perfil(db, usuario_id, usuario, nombre_usuario_nuevo, nombre, email_nuevo):
    """Respuesta de error si algun cambio pedido no es valido (sin escribir nada), o None."""
    if nombre_usuario_nuevo:
        if len(nombre_usuario_nuevo) > 80:
            return APIResponse.validacion("err_nombre_max_80")
        if db.execute(
            "SELECT id FROM usuarios WHERE LOWER(nombre_usuario) = LOWER(?) AND id != ?",
            (nombre_usuario_nuevo, usuario_id),
        ).fetchone():
            return APIResponse.error("err_usuario_duplicado", 400)
    if nombre and len(nombre) > 80:
        return APIResponse.validacion("err_nombre_max_80")
    if email_nuevo:
        if not email_valido(email_nuevo):
            return APIResponse.validacion("err_email_invalido")
        if db.execute(
            "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(?) AND id != ?", (email_nuevo, usuario_id),
        ).fetchone():
            # Respuesta generica: confirmar que un email ya esta registrado seria un oraculo de enumeracion (S-10).
            return APIResponse.error("err_email_no_disponible", 400)
    return None


@bp.route("/api/auth/perfil", methods=["PUT"])
@requerir_sesion
@manejo_errores
def actualizar_perfil():
    """Actualizar usuario (login), nombre a mostrar y/o email del usuario actual.

    NO cambia la contraseña (A-3): antes aceptaba un campo `password` y lo
    aplicaba sin pedir la actual, mientras /api/auth/cambiar-password si la
    exige. Con una sesion robada bastaba un PUT aqui para tomar la cuenta de
    forma permanente y expulsar al dueño. El frontend nunca uso esa rama.
    El cambio de contraseña vive solo en /api/auth/cambiar-password.

    El cambio de usuario (login) y de email exigen la contraseña actual
    (`password_actual`) por el mismo motivo: son los dos datos con los que se
    recupera una cuenta, asi que no pueden cambiarse solo con la cookie.
    """
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    nombre_usuario_nuevo = texto_json(datos, "usuario")
    nombre = texto_json(datos, "nombre")
    email_nuevo = texto_json(datos, "email").lower()
    password_actual = texto_json(datos, "password_actual", recortar=False)

    if "password" in datos:
        return APIResponse.error("err_usa_cambiar_password", 400)

    db = get_db()
    usuario = db.execute(
        "SELECT nombre_usuario, password_hash, email FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    # Reautenticacion para los campos sensibles. Las cuentas creadas por OAuth
    # no tienen password_hash: para ellas la prueba de identidad es el propio
    # proveedor, asi que no se puede exigir aqui (ver password_valida).
    if (nombre_usuario_nuevo or email_nuevo) and usuario and usuario["password_hash"]:
        if not password_valida(usuario["password_hash"], password_actual):
            return APIResponse.error("err_password_actual_incorrecta", 400)

    if not usuario:
        return APIResponse.no_autorizado()

    # Las cuentas sin contrasena (OAuth) no pueden reautenticarse con ella, y quien robase la
    # cookie podria fijar SU email, verificarlo y pedir un reset de contrasena: toma de cuenta.
    # Para fijar o cambiar el email se exige un inicio de sesion reciente (auth_ts, que pone cada
    # login); una cookie robada no lo tiene. Las cookies anteriores a este campo caen aqui y
    # basta con volver a iniciar sesion.
    if email_nuevo and usuario and not usuario["password_hash"]:
        if int(time.time()) - int(session.get("auth_ts") or 0) > VENTANA_REAUTENTICACION_S:
            return APIResponse.error("err_reautenticar_para_cambiar_email", 403)

    # Primero se validan TODOS los cambios y despues se aplican: antes se iba escribiendo campo a
    # campo, y un fallo en el ultimo (email invalido) dejaba la sesion con el usuario ya cambiado
    # mientras la BD hacia rollback.
    error = _validar_cambios_perfil(db, usuario_id, usuario, nombre_usuario_nuevo, nombre, email_nuevo)
    if error:
        return error

    if nombre_usuario_nuevo:
        db.execute("UPDATE usuarios SET nombre_usuario = ? WHERE id = ?", (nombre_usuario_nuevo, usuario_id))
    if nombre:
        db.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", (nombre, usuario_id))

    # Fijar o cambiar el email (A-3b). Sin esto, quien se registraba con usuario+contraseña no podia
    # tener email NUNCA, y por tanto no podia recuperar la contraseña ni activar la verificacion en
    # dos pasos. El email entra SIN verificar y se envia el enlace: hasta que no se confirme no sirve
    # para recuperar la contraseña (el reset exige email_verificado, ver solicitar_reset_password).
    email_cambiado = bool(email_nuevo) and (usuario["email"] or "").lower() != email_nuevo
    if email_cambiado:
        db.execute("UPDATE usuarios SET email = ?, email_verificado = 0 WHERE id = ?", (email_nuevo, usuario_id))

    db.commit()
    if nombre_usuario_nuevo:
        session["usuario"] = nombre_usuario_nuevo

    if email_cambiado:
        enviar_token_verificacion_email(db, usuario_id, usuario["nombre_usuario"], email_nuevo)

    fila = db.execute("SELECT nombre, email, email_verificado FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return APIResponse.success({
        "usuario": session.get("usuario"),
        "nombre": fila["nombre"] if fila else None,
        "email": fila["email"] if fila else None,
        "email_verificado": bool(fila["email_verificado"]) if fila else False,
    })


@bp.route("/api/auth/tema", methods=["POST"])
@requerir_sesion
@manejo_errores
def cambiar_tema():
    """Guarda la preferencia de tema (light/dark/auto) del usuario."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    tema = (texto_json(datos, "tema") or "auto").lower()

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
    datos = cuerpo_json()
    valor = (texto_json(datos, "teclado_virtual_activo") or "on").lower()

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
    Anthropic, ver stockhogar/rutas/escaner/tickets.py::analizar_ticket."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()
    ocr_local = bool(datos.get("ocr_local"))

    db = get_db()
    db.execute("UPDATE usuarios SET usuario_ocr_local = ? WHERE id = ?", (int(ocr_local), usuario_id))
    db.commit()
    return APIResponse.success({"ocr_local": ocr_local})


@bp.route("/api/auth/preferencias-listas", methods=["POST"])
@requerir_sesion
@manejo_errores
def actualizar_preferencias_listas():
    """Actualiza las preferencias de vista de la lista de la compra (lista/recuadros) y agrupación por categorías."""
    usuario_id = session.get("usuario_id")
    datos = cuerpo_json()

    vista = (texto_json(datos, "vista_lista_compra") or "lista").lower()
    agrupar = (texto_json(datos, "agrupar_categorias") or "off").lower()

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


@bp.route("/api/auth/aceptar-terminos", methods=["POST"])
@requerir_sesion
@manejo_errores
def aceptar_terminos():
    """Registra la aceptación de la versión vigente de Términos y Privacidad.

    Cubre tanto al usuario que se registra por Google (no pasa por el
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
