"""Rutas para autenticación OAuth con Google y Apple."""
from flask import Blueprint, request, session, redirect, url_for
from urllib.parse import urlencode
import requests
import json

from ..api import APIResponse, manejo_errores
from ..db import ahora, get_db
from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APPLE_CLIENT_ID, APPLE_CLIENT_SECRET, APPLE_TEAM_ID

bp = Blueprint("oauth", __name__, url_prefix="/auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"


@bp.route("/google", methods=["GET"])
def oauth_google():
    """Iniciar flujo OAuth con Google."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": url_for("oauth.oauth_google_callback", _external=True),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline"
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@bp.route("/google/callback", methods=["GET"])
@manejo_errores
def oauth_google_callback():
    """Callback de Google OAuth."""
    codigo = request.args.get("code")
    error = request.args.get("error")

    if error:
        return APIResponse.error(f"Error de Google: {error}", 400)

    if not codigo:
        return APIResponse.error("No se recibió código de autorización", 400)

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
            # Buscar usuario por email
            usuario = db.execute(
                "SELECT id FROM usuarios WHERE email = ?",
                (email,)
            ).fetchone()

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
        session["usuario_id"] = usuario_id
        session.permanent = True

        return redirect("/")

    except requests.RequestException as e:
        return APIResponse.error(f"Error en autenticación Google: {str(e)}", 500)


@bp.route("/apple", methods=["GET"])
def oauth_apple():
    """Iniciar flujo OAuth con Apple."""
    params = {
        "client_id": APPLE_CLIENT_ID,
        "redirect_uri": url_for("oauth.oauth_apple_callback", _external=True),
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "openid email name"
    }
    return redirect(f"{APPLE_AUTH_URL}?{urlencode(params)}")


@bp.route("/apple/callback", methods=["POST"])
@manejo_errores
def oauth_apple_callback():
    """Callback de Apple OAuth."""
    codigo = request.form.get("code")
    id_token = request.form.get("id_token")
    error = request.form.get("error")

    if error:
        return APIResponse.error(f"Error de Apple: {error}", 400)

    if not codigo:
        return APIResponse.error("No se recibió código de autorización", 400)

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

        # Decodificar id_token para obtener info del usuario
        # En producción, verificar la firma JWT
        import base64
        partes = id_token.split(".")
        payload = partes[1]
        # Añadir padding si es necesario
        payload += "=" * (4 - len(payload) % 4)
        info_usuario = json.loads(base64.urlsafe_b64decode(payload))

        email = info_usuario.get("email")
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
            # Buscar usuario por email
            usuario = db.execute(
                "SELECT id FROM usuarios WHERE email = ?",
                (email,)
            ).fetchone() if email else None

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
        session["usuario_id"] = usuario_id
        session.permanent = True

        return redirect("/")

    except (requests.RequestException, Exception) as e:
        return APIResponse.error(f"Error en autenticación Apple: {str(e)}", 500)
