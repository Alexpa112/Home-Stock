"""
Dreame! - aplicacion ligera para llevar el inventario de productos de casa.
Backend con Flask + SQLite, pensado para correr en una Raspberry Pi 3.
"""
from datetime import timedelta

from flask import Flask, jsonify, redirect, request, session, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError

from . import db, seguridad
from .config import DIAS_SESION, USAR_COOKIE_SEGURA
from .rutas import auth, articulos_lista, categorias, espacios, historial, listas, paginas, productos, tickets, ocr_tickets, permisos, oauth, idiomas, formularios
from .rutas.auth import RUTAS_PUBLICAS

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = seguridad.FLASK_SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=DIAS_SESION)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = USAR_COOKIE_SEGURA
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
    app.register_blueprint(espacios.bp)
    app.register_blueprint(historial.bp)
    app.register_blueprint(listas.bp)
    app.register_blueprint(articulos_lista.bp)
    app.register_blueprint(permisos.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(ocr_tickets.bp)

    @app.before_request
    def exigir_sesion():
        if request.endpoint in RUTAS_PUBLICAS:
            return None
        if not session.get("usuario"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "No has iniciado sesión"}), 401
            return redirect(url_for("auth.pagina_login"))
        return None

    db.init_db()
    return app
