"""
StockHogar - aplicación para gestión de inventario del hogar.
Backend con Flask + SQLite, frontend con Next.js.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, g, jsonify, redirect, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db, seguridad
from .config import DIAS_SESION, USAR_COOKIE_SEGURA, LOG_FILE_PATH
from .servicios import mantenimiento
from .translator import traducir

csrf = CSRFProtect()

from .rutas import auth, articulos_compra, categorias, categorias_gasto, consumo, gastos, historial, hogares, paginas, productos, recetas, tickets, ocr_tickets, permisos, oauth, idiomas, formularios, version, legal, push
from .rutas.auth import RUTAS_PUBLICAS


def _configurar_logging_a_fichero():
    """Vuelca los logs de la aplicacion (logging.getLogger(__name__) de cada
    modulo) a un fichero rotativo en logs/. El Panel de Gestion del Servidor
    (proyecto independiente, github.com/.../StockHogar-Panel) lo lee para
    mostrarlo en vivo sin depender de 'docker logs' ni de ningun acoplamiento
    de codigo con esta app.
    """
    raiz = logging.getLogger()
    ya_configurado = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "_stockhogar_panel", False)
        for h in raiz.handlers
    )
    if ya_configurado:
        return
    handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    handler._stockhogar_panel = True
    raiz.addHandler(handler)
    if raiz.level == logging.WARNING or raiz.level == logging.NOTSET:
        raiz.setLevel(logging.INFO)


class SessionInterfaceOmitible(SecureCookieSessionInterface):
    """Igual que la interfaz de sesión por defecto de Flask, pero permite que
    una ruta concreta pida no reenviar la cookie de sesión en su respuesta.

    Por defecto Flask reenvía (refresca) la cookie de sesión en CADA
    respuesta cuando la sesión es permanente (SESSION_REFRESH_EACH_REQUEST,
    que dejamos con su valor por defecto). Eso es correcto para casi todas
    las rutas, pero es peligroso para peticiones en segundo plano que el
    frontend dispara sin esperar su respuesta (p. ej. /api/productos/traducir,
    ver app.js): si esa petición tarda y el usuario cambia de lista mientras
    tanto, su respuesta tardía reenviaría la cookie con el "lista_actual_id"
    desactualizado de cuando empezó, pisando la selección de lista más
    reciente. Las rutas que marquen `g._omitir_refresco_sesion = True` no
    reenvían la cookie salvo que de verdad hayan modificado la sesión.
    """

    def save_session(self, app, session, response):
        if getattr(g, "_omitir_refresco_sesion", False) and not session.modified:
            return None
        return super().save_session(app, session, response)

    def get_signing_serializer(self, app):
        # Soporte de rotacion de clave (S-18, ver seguridad.rotar_clave()):
        # itsdangerous.Signer acepta una LISTA de claves - firma siempre con
        # la primera, pero verifica una firma existente contra CUALQUIERA de
        # ellas. Sin esto, rotar la clave invalidaria de golpe TODAS las
        # sesiones ya abiertas, no solo las que se quisiera revocar aposta.
        serializer = super().get_signing_serializer(app)
        if serializer is None or not seguridad.CLAVES_VERIFICACION_PREVIAS:
            return serializer
        serializer.secret_keys = [app.secret_key, *seguridad.CLAVES_VERIFICACION_PREVIAS]
        return serializer


def create_app():
    _configurar_logging_a_fichero()

    app = Flask(__name__)
    # Un solo salto de proxy de confianza: el contenedor Next (rewrite de
    # /api/*). Sin esto, request.remote_addr siempre es la IP del contenedor
    # Next, nunca la del cliente real (ver stockhogar/red.py::ip_cliente()).
    # x_for=1 exactamente: mas de un salto permitiria a un cliente falsear su
    # propia IP añadiendo entradas propias a X-Forwarded-For.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    app.config["SECRET_KEY"] = seguridad.FLASK_SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=DIAS_SESION)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = USAR_COOKIE_SEGURA
    # Limite de tamaño de subida (escaneo de tickets: imagen o PDF). Sin esto,
    # Flask acepta peticiones de cualquier tamaño y un POST enorme puede agotar
    # memoria/disco antes de que el codigo de la ruta llegue a validar nada.
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
    app.config["WTF_CSRF_CHECK_DEFAULT"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    app.config["WTF_CSRF_SSL_STRICT"] = False
    app.session_interface = SessionInterfaceOmitible()
    app.teardown_appcontext(db.close_db)

    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def token_csrf_invalido(e):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "Error CSRF: %s | Ruta: %s | Método: %s | Sesión: %s | Usuario: %s",
            str(e),
            request.path,
            request.method,
            request.cookies.get("session", "sin_cookie")[:20],
            session.get("usuario_id", "no_autenticado")
        )
        if request.path.startswith("/api/"):
            return jsonify({"error": "Token CSRF invalido o ausente"}), 400
        return e.description, 400

    @app.errorhandler(413)
    def archivo_demasiado_grande(e):
        return jsonify({"error": traducir("err_archivo_demasiado_grande")}), 413

    @app.after_request
    def cabeceras_seguridad(response):
        # Defensa en profundidad barata para el caso en que este backend
        # quede accesible directamente sin pasar por el proxy Next (que es
        # quien fija la CSP completa). No se duplica la CSP aquí.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    app.register_blueprint(paginas.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(oauth.bp)
    app.register_blueprint(idiomas.bp)
    app.register_blueprint(formularios.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(categorias.bp)
    app.register_blueprint(categorias_gasto.bp)
    app.register_blueprint(historial.bp)
    app.register_blueprint(hogares.bp)
    # Alias temporal /api/listas -> misma lógica que /api/hogares, para no
    # romper peticiones de PWAs instaladas con la app antigua en caché offline
    # hasta que se confirme que todos los clientes migraron (ver
    # docs/HOGAR_REESTRUCTURACION.md).
    app.register_blueprint(hogares.bp, name="hogares_alias_legado", url_prefix="/api/listas")
    app.register_blueprint(articulos_compra.bp)
    app.register_blueprint(permisos.bp)
    app.register_blueprint(gastos.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(ocr_tickets.bp)
    app.register_blueprint(consumo.bp)
    app.register_blueprint(version.bp)
    app.register_blueprint(legal.bp)
    app.register_blueprint(push.bp)
    app.register_blueprint(recetas.bp)

    @app.before_request
    def comprobar_mantenimiento():
        # El flag de mantenimiento lo activa/desactiva el Panel de Gestion del
        # Servidor (proyecto independiente) escribiendo/borrando el mismo
        # fichero (data/mantenimiento.flag); esta app solo lo respeta.
        # El frontend Next.js hace polling a /api/mantenimiento/estado para
        # mostrar la pantalla de mantenimiento (ver lib/useMantenimientoStream.ts).
        if (request.endpoint or "") in ("paginas.mantenimiento_estado",):
            return None
        # El HEALTHCHECK de Docker (curl a "/" desde dentro del propio
        # contenedor, ver Dockerfile) y el `wait_healthy` de install.sh usan
        # esta misma ruta. El Panel activa mantenimiento ANTES de invocar
        # install.sh y solo lo desactiva al terminar, así que sin esta
        # excepcion el healthcheck jamas pasaria durante un despliegue
        # lanzado desde el panel: siempre veria 503 y forzaria un rollback
        # aunque la app estuviera perfectamente sana. El trafico real nunca
        # llega como 127.0.0.1/::1 (pasa por la red de Docker o el proxy),
        # asi que esto no abre la app en mantenimiento a usuarios reales.
        if mantenimiento.activo() and request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify({"error": "La aplicación está en mantenimiento", "mantenimiento": True}), 503
        return None

    @app.before_request
    def exigir_sesion():
        # Antes de mirar nada mas: si la cookie trae una session_version que la
        # BD ya no reconoce, la sesion esta revocada y se descarta aqui, para
        # TODAS las rutas. La comprobacion vivia solo dentro de @requerir_sesion,
        # asi que las rutas que leen la sesion sin ese decorador -entre ellas
        # /api/auth/estado, que devuelve email, nombre y preferencias- seguian
        # sirviendo los datos del usuario con una cookie robada aunque la
        # victima hubiera pulsado "cerrar otras sesiones" o cambiado la
        # contraseña, durante los 365 dias de vida de la cookie.
        #
        # Se limpia y se sigue el flujo normal: en una ruta publica la peticion
        # continua ya sin sesion (estado dira "no hay usuario", y el login puede
        # rehacerse con normalidad), y en una protegida cae en el 401/redirect
        # de aqui abajo.
        from .api.base import sesion_revocada
        if sesion_revocada():
            session.clear()

        if request.endpoint in RUTAS_PUBLICAS:
            return None
        if not session.get("usuario"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "No has iniciado sesión"}), 401
            # El frontend Next.js maneja la pantalla de login.
            # Redirigimos al usuario no autenticado hacia /
            return redirect("/")
        return None

    db.init_db()
    _registrar_estado_escaner()
    return app


def _registrar_estado_escaner():
    """Deja en el log, al arrancar, que motor va a usar el escaner de tickets.

    Antes esto solo se sabia al escanear un ticket (y el aviso se perdia entre
    el resto del log), asi que una instalacion sin el paquete `anthropic` o sin
    ANTHROPIC_API_KEY se comportaba como si funcionase: caia a Tesseract en
    silencio y reconocia mucho peor. Con esta linea, tras reinstalar se ve de un
    vistazo si el motor principal esta armado.
    """
    logger = logging.getLogger(__name__)
    hay_clave = bool(os.getenv("ANTHROPIC_API_KEY"))
    try:
        import anthropic
        version = anthropic.__version__
    except ImportError:
        version = None

    if version and hay_clave:
        logger.info(
            "Escaner de tickets: motor principal Claude Vision listo (anthropic %s)", version
        )
    elif not version:
        logger.warning(
            "Escaner de tickets: el paquete 'anthropic' NO esta instalado, se usara "
            "solo Tesseract (reconoce bastante peor). Instala con: pip install -r requirements.txt"
        )
    else:
        logger.warning(
            "Escaner de tickets: ANTHROPIC_API_KEY no configurada, se usara solo "
            "Tesseract (reconoce bastante peor). Añadela al .env del host: "
            "docker-compose ya lo inyecta con env_file."
        )
