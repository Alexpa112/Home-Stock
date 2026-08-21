"""Rutas para autenticación OAuth con Google."""
import secrets

from flask import Blueprint, request, session, redirect
from urllib.parse import urlencode
import requests
import logging

from ..api import APIResponse, manejo_errores
from ..db import ahora, get_db
from ..translator import traducir
from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APP_URL

bp = Blueprint("oauth", __name__, url_prefix="/auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Parametro con el que se le pide a la pantalla de login que abra directamente
# el formulario del codigo 2FA (ver los callbacks de mas abajo). El frontend lo
# lee en app/page.tsx; si se renombra aqui hay que renombrarlo alli, y
# test_oauth_2fa_redirect.py falla a proposito si solo se cambia en un lado.
PARAM_CODIGO_2FA = "codigo_2fa"


@bp.route("/google", methods=["GET"])
@manejo_errores
def oauth_google():
    """Iniciar flujo OAuth con Google."""
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{APP_URL}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@bp.route("/google/callback", methods=["GET"])
@manejo_errores
def oauth_google_callback():
    """Callback de Google OAuth."""
    codigo = request.args.get("code")
    error = request.args.get("error")
    estado_recibido = request.args.get("state")
    estado_esperado = session.pop("oauth_state", None)

    if error:
        return APIResponse.error(traducir("err_oauth_google_generico").replace("{error}", error), 400)

    if not estado_esperado or estado_recibido != estado_esperado:
        return APIResponse.error("err_oauth_solicitud_invalida", 400)

    if not codigo:
        return APIResponse.error("err_oauth_sin_codigo", 400)

    # Intercambiar código por token
    datos_token = {
        "code": codigo,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{APP_URL}/auth/google/callback",
        "grant_type": "authorization_code"
    }

    try:
        respuesta_token = requests.post(GOOGLE_TOKEN_URL, data=datos_token, timeout=10)
        respuesta_token.raise_for_status()
        tokens = respuesta_token.json()
        access_token = tokens.get("access_token")

        # Obtener información del usuario
        headers = {"Authorization": f"Bearer {access_token}"}
        respuesta_usuario = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        respuesta_usuario.raise_for_status()
        info_usuario = respuesta_usuario.json()

        # Buscar o crear usuario
        db = get_db()
        email = info_usuario.get("email")
        email_verificado = info_usuario.get("verified_email")
        nombre = info_usuario.get("name")
        id_proveedor = info_usuario.get("id")
        foto_perfil = info_usuario.get("picture")

        # Buscar cuenta OAuth existente
        cuenta_oauth = db.execute(
            "SELECT usuario_id FROM oauth_accounts WHERE proveedor = ? AND id_proveedor = ?",
            ("google", id_proveedor)
        ).fetchone()

        if cuenta_oauth:
            usuario_id = cuenta_oauth["usuario_id"]
        else:
            # Solo vincular a una cuenta existente por email si Google lo ha
            # verificado: si no, cualquiera podria hacerse pasar por el dueño
            # de ese email y entrar en su cuenta.
            usuario = db.execute(
                "SELECT id FROM usuarios WHERE email = ?",
                (email,)
            ).fetchone() if email_verificado else None

            if usuario:
                usuario_id = usuario["id"]
            else:
                # Crear nuevo usuario
                nombre_usuario = email.split("@")[0]
                # Asegurar nombre único
                contador = 1
                nombre_base = nombre_usuario
                while db.execute(
                    "SELECT id FROM usuarios WHERE nombre_usuario = ?",
                    (nombre_usuario,)
                ).fetchone():
                    nombre_usuario = f"{nombre_base}{contador}"
                    contador += 1

                cur = db.execute(
                    "INSERT INTO usuarios (nombre_usuario, email, fecha_creacion, email_verificado) VALUES (?, ?, ?, ?) RETURNING id",
                    (nombre_usuario, email, ahora(), int(bool(email_verificado)))
                )
                usuario_id = cur.fetchone()["id"]

            # Crear cuenta OAuth
            db.execute(
                """INSERT INTO oauth_accounts
                   (usuario_id, proveedor, id_proveedor, email, nombre, foto_perfil, fecha_creacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (usuario_id, "google", id_proveedor, email, nombre, foto_perfil, ahora())
            )

        db.commit()

        # M-5: verificar si el usuario tiene 2FA activo. Si es así, no crear la
        # sesión todavía, sino generar un código y pedirlo antes de continuar.
        fila_usuario = db.execute(
            "SELECT nombre_usuario, session_version, doble_factor_activo, email FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()

        if fila_usuario["doble_factor_activo"] and fila_usuario["email"]:
            # Importar la función de auth.py para generar y enviar el código
            from .auth import _generar_y_enviar_codigo
            _generar_y_enviar_codigo(db, usuario_id, fila_usuario["email"])
            session["pendiente_2fa_usuario_id"] = usuario_id
            # A la pantalla de login con el formulario del código ya abierto.
            # Antes esto apuntaba a "/verificar-codigo-2fa", una página que no
            # existe en el frontend: el usuario con 2FA que entraba por OAuth
            # se comía un 404 y no podía terminar de iniciar sesión (y si su
            # cuenta se creó con OAuth no tiene contraseña con la que entrar
            # por el otro camino). El formulario del código vive dentro de la
            # propia pantalla de login (app/page.tsx), que lo abre al ver este
            # parámetro; desde ahí llama a /api/auth/verificar-codigo, que lee
            # el pendiente_2fa_usuario_id que acabamos de guardar.
            return redirect(f"{APP_URL}/?{PARAM_CODIGO_2FA}=1")

        # Si no tiene 2FA, crear sesión directamente
        session["usuario"] = fila_usuario["nombre_usuario"]
        session["usuario_id"] = usuario_id
        session["session_version"] = fila_usuario["session_version"]
        session.permanent = True

        return redirect(f"{APP_URL}/dashboard")

    except requests.RequestException:
        logging.getLogger(__name__).exception("Error en autenticación Google")
        return APIResponse.error("err_oauth_google_fallo", 500)
