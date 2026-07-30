"""
StockHogar - aplicación para gestión de inventario del hogar.
Backend con Flask + SQLite, frontend con Next.js.
"""
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, g, jsonify, redirect, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from flask_wtf.csrf import CSRFProtect, CSRFError

from . import db, seguridad
from .config import DIAS_SESION, USAR_COOKIE_SEGURA, LOG_FILE_PATH
from .servicios import mantenimiento
from .translator import traducir

csrf = CSRFProtect()

from .rutas import auth, articulos_compra, categorias, consumo, historial, hogares, paginas, productos, tickets, ocr_tickets, permisos, oauth, idiomas, formularios, version
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


def create_app():
    _configurar_logging_a_fichero()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = seguridad.FLASK_SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=DIAS_SESION)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = USAR_COOKIE_SEGURA
    # Limite de tamaño de subida (escaneo de tickets: imagen o PDF). Sin esto,
    # Flask acepta peticiones de cualquier tamaño y un POST enorme puede agotar
    # memoria/disco antes de que el codigo de la ruta llegue a validar nada.
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
    app.session_interface = SessionInterfaceOmitible()
    app.teardown_appcontext(db.close_db)

    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def token_csrf_invalido(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Token CSRF invalido o ausente"}), 400
        return e.description, 400

    @app.errorhandler(413)
    def archivo_demasiado_grande(e):
        return jsonify({"error": traducir("err_archivo_demasiado_grande")}), 413

    app.register_blueprint(paginas.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(oauth.bp)
    app.register_blueprint(idiomas.bp)
    app.register_blueprint(formularios.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(categorias.bp)
    app.register_blueprint(historial.bp)
    app.register_blueprint(hogares.bp)
    # Alias temporal /api/listas -> misma lógica que /api/hogares, para no
    # romper peticiones de PWAs instaladas con la app antigua en caché offline
    # hasta que se confirme que todos los clientes migraron (ver
    # docs/HOGAR_REESTRUCTURACION.md).
    app.register_blueprint(hogares.bp, name="hogares_alias_legado", url_prefix="/api/listas")
    app.register_blueprint(articulos_compra.bp)
    app.register_blueprint(permisos.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(ocr_tickets.bp)
    app.register_blueprint(consumo.bp)
    app.register_blueprint(version.bp)

    @app.before_request
    def comprobar_mantenimiento():
        # El flag de mantenimiento lo activa/desactiva el Panel de Gestion del
        # Servidor (proyecto independiente) escribiendo/borrando el mismo
        # fichero (data/mantenimiento.flag); esta app solo lo respeta.
        # El frontend Next.js se suscribe a /api/mantenimiento/stream para
        # mostrar la pantalla de mantenimiento.
        if (request.endpoint or "") in ("paginas.mantenimiento_stream",):
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
    return app
