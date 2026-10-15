"""Blueprint de la cuenta y lista de rutas publicas (sin sesion)."""
from flask import Blueprint


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
    "paginas.log_client_error",
    "paginas.csrf_token",
    "paginas.mantenimiento_estado",
    # Solo devuelve la fecha de modificacion de un fichero del despliegue, sin
    # nada del usuario. Tiene que ser publica porque useCacheBuster corre
    # tambien en la pantalla de login: con 401 el cliente leia
    # data.version = undefined, lo interpretaba como "hay version nueva" y
    # borraba el service worker y todas las caches antes de recargar solo.
    "version.cache_version",
    "idiomas.obtener_todas_traducciones",
    "idiomas.obtener_idioma",
    "legal.configuracion_legal",
}
