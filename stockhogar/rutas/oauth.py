"""Rutas para autenticación OAuth con Google y Apple."""
import secrets

from flask import Blueprint, request, session, redirect, url_for
from urllib.parse import urlencode
import requests
import jwt
from jwt import PyJWKClient
import logging

from ..api import APIResponse, manejo_errores
from ..db import ahora, get_db
from ..translator import traducir
from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APPLE_CLIENT_ID, APPLE_CLIENT_SECRET, APPLE_TEAM_ID

bp = Blueprint("oauth", __name__, url_prefix="/auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

# Cliente JWKS de Apple: cachea las claves publicas y las refresca solas
# cuando aparece un "kid" que no conoce.
_apple_jwks_client = PyJWKClient(APPLE_JWKS_URL)


def _verificar_id_token_apple(id_token):
    """Verifica firma y claims (iss/aud/exp) del id_token de Apple.

    Sin esto, cualquiera podria fabricar un id_token con el email que quisiera
    y tomar el control de la cuenta asociada a ese email.
    """
    signing_key = _apple_jwks_client.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=APPLE_CLIENT_ID,
        issuer="https://appleid.apple.com",
    )


@bp.route("/google", methods=["GET"])
@manejo_errores
def oauth_google():
    """Iniciar flujo OAuth con Google."""
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": url_for("oauth.oauth_google_callback", _external=True),
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
        "redirect_uri": url_for("oauth.oauth_google_callback", _external=True),
        "grant_type": "authorization_code"
    }

    try:
        respuesta_token = requests.post(GOOGLE_TOKEN_URL, data=datos_token)
        respuesta_token.raise_for_status()
        tokens = respuesta_token.json()
        access_token = tokens.get("access_token")

        # Obtener información del usuario
        headers = {"Authorization": f"Bearer {access_token}"}
        respuesta_usuario = requests.get(GOOGLE_USERINFO_URL, headers=headers)
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
                import hashlib
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
                    "INSERT INTO usuarios (nombre_usuario, email, fecha_creacion) VALUES (?, ?, ?)",
                    (nombre_usuario, email, ahora())
                )
                usuario_id = cur.lastrowid

            # Crear cuenta OAuth
            db.execute(
                """INSERT INTO oauth_accounts
                   (usuario_id, proveedor, id_proveedor, email, nombre, foto_perfil, fecha_creacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (usuario_id, "google", id_proveedor, email, nombre, foto_perfil, ahora())
            )

        db.commit()

        # Crear sesión
        fila_usuario = db.execute(
            "SELECT nombre_usuario FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        session["usuario"] = fila_usuario["nombre_usuario"]
        session["usuario_id"] = usuario_id
        session.permanent = True

        return redirect("/")

    except requests.RequestException:
        logging.getLogger(__name__).exception("Error en autenticación Google")
        return APIResponse.error("err_oauth_google_fallo", 500)


@bp.route("/apple", methods=["GET"])
@manejo_errores
def oauth_apple():
    """Iniciar flujo OAuth con Apple."""
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    params = {
        "client_id": APPLE_CLIENT_ID,
        "redirect_uri": url_for("oauth.oauth_apple_callback", _external=True),
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "openid email name",
        "state": state,
    }
    return redirect(f"{APPLE_AUTH_URL}?{urlencode(params)}")


@bp.route("/apple/callback", methods=["POST"])
@manejo_errores
def oauth_apple_callback():
    """Callback de Apple OAuth."""
    codigo = request.form.get("code")
    id_token = request.form.get("id_token")
    error = request.form.get("error")
    estado_recibido = request.form.get("state")
    estado_esperado = session.pop("oauth_state", None)

    if error:
        return APIResponse.error(traducir("err_oauth_apple_generico").replace("{error}", error), 400)

    if not estado_esperado or estado_recibido != estado_esperado:
        return APIResponse.error("err_oauth_solicitud_invalida", 400)

    if not codigo:
        return APIResponse.error("err_oauth_sin_codigo", 400)

    # Intercambiar código por token
    datos_token = {
        "code": codigo,
        "client_id": APPLE_CLIENT_ID,
        "client_secret": APPLE_CLIENT_SECRET or APPLE_CLIENT_ID,
        "redirect_uri": url_for("oauth.oauth_apple_callback", _external=True),
        "grant_type": "authorization_code"
    }

    try:
        respuesta_token = requests.post(APPLE_TOKEN_URL, data=datos_token)
        respuesta_token.raise_for_status()
        tokens = respuesta_token.json()

        # Verificar firma y claims (iss/aud/exp) del id_token contra las
        # claves publicas de Apple antes de confiar en su contenido.
        try:
            info_usuario = _verificar_id_token_apple(id_token)
        except jwt.PyJWTError:
            logging.getLogger(__name__).exception("id_token de Apple inválido")
            return APIResponse.error("err_oauth_apple_identidad", 400)

        email = info_usuario.get("email")
        email_verificado = str(info_usuario.get("email_verified", "")).lower() == "true"
        id_proveedor = info_usuario.get("sub")

        # Buscar o crear usuario
        db = get_db()

        # Buscar cuenta OAuth existente
        cuenta_oauth = db.execute(
            "SELECT usuario_id FROM oauth_accounts WHERE proveedor = ? AND id_proveedor = ?",
            ("apple", id_proveedor)
        ).fetchone()

        if cuenta_oauth:
            usuario_id = cuenta_oauth["usuario_id"]
        else:
            # Solo vincular a una cuenta existente por email si Apple lo ha
            # verificado (ver comentario equivalente en el flujo de Google).
            usuario = db.execute(
                "SELECT id FROM usuarios WHERE email = ?",
                (email,)
            ).fetchone() if (email and email_verificado) else None

            if usuario:
                usuario_id = usuario["id"]
            else:
                # Crear nuevo usuario
                nombre_usuario = email.split("@")[0] if email else f"apple_{id_proveedor[:8]}"
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
                    "INSERT INTO usuarios (nombre_usuario, email, fecha_creacion) VALUES (?, ?, ?)",
                    (nombre_usuario, email, ahora())
                )
                usuario_id = cur.lastrowid

            # Crear cuenta OAuth
            db.execute(
                """INSERT INTO oauth_accounts
                   (usuario_id, proveedor, id_proveedor, email, fecha_creacion)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario_id, "apple", id_proveedor, email, ahora())
            )

        db.commit()

        # Crear sesión
        fila_usuario = db.execute(
            "SELECT nombre_usuario FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        session["usuario"] = fila_usuario["nombre_usuario"]
        session["usuario_id"] = usuario_id
        session.permanent = True

        return redirect("/")

    except Exception:
        logging.getLogger(__name__).exception("Error en autenticación Apple")
        return APIResponse.error("err_oauth_apple_fallo", 500)
