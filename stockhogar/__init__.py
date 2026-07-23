"""
Dreame! - aplicacion ligera para llevar el inventario de productos de casa.
Backend con Flask + SQLite, pensado para correr en una Raspberry Pi 3.
"""
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from flask_wtf.csrf import CSRFProtect, CSRFError

from . import db, seguridad
from .config import DIAS_SESION, USAR_COOKIE_SEGURA, LOG_FILE_PATH
from .rutas import auth, articulos_lista, categorias, consumo, historial, listas, paginas, productos, tickets, ocr_tickets, permisos, oauth, idiomas, formularios
from .rutas.auth import RUTAS_PUBLICAS
from .servicios import mantenimiento

csrf = CSRFProtect()


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
    app.session_interface = SessionInterfaceOmitible()
    app.teardown_appcontext(db.close_db)

    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def token_csrf_invalido(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Token CSRF invalido o ausente"}), 400
        return e.description, 400

    app.register_blueprint(paginas.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(oauth.bp)
    app.register_blueprint(idiomas.bp)
    app.register_blueprint(formularios.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(categorias.bp)
    app.register_blueprint(historial.bp)
    app.register_blueprint(listas.bp)
    app.register_blueprint(articulos_lista.bp)
    app.register_blueprint(permisos.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(ocr_tickets.bp)
    app.register_blueprint(consumo.bp)

    @app.before_request
    def comprobar_mantenimiento():
        # El flag de mantenimiento lo activa/desactiva el Panel de Gestion del
        # Servidor (proyecto independiente) escribiendo/borrando el mismo
        # fichero (data/mantenimiento.flag); esta app solo lo respeta.
        if (request.endpoint or "") == "static":
            return None
        if mantenimiento.activo():
            if request.path.startswith("/api/"):
                return jsonify({"error": "La aplicación está en mantenimiento", "mantenimiento": True}), 503
            return render_template("mantenimiento.html", mensaje=mantenimiento.mensaje()), 503
        return None

    @app.before_request
    def exigir_sesion():
        if request.endpoint in RUTAS_PUBLICAS:
            return None
        if not session.get("usuario"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "No has iniciado sesión"}), 401
            # Preservar la página solicitada (p.ej. un enlace de invitación a
            # una lista compartida) para retomarla justo después de iniciar
            # sesión, en vez de perderla y acabar en la home genérica.
            next_url = request.full_path.rstrip("?")
            return redirect(url_for("auth.pagina_login", next=next_url))
        return None

    db.init_db()
    return app
