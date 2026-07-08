"""
Dreame! - aplicacion ligera para llevar el inventario de productos de casa.
Backend con Flask + SQLite, pensado para correr en una Raspberry Pi 3.
"""
from datetime import timedelta

from flask import Flask, jsonify, redirect, request, session, url_for

from . import db, seguridad
from .config import DIAS_SESION
from .rutas import auth, categorias, espacios, historial, lista_compra, listas, paginas, productos, tickets, ocr_tickets
from .rutas.auth import RUTAS_PUBLICAS


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = seguridad.FLASK_SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=DIAS_SESION)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.teardown_appcontext(db.close_db)

    app.register_blueprint(paginas.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(categorias.bp)
    app.register_blueprint(espacios.bp)
    app.register_blueprint(historial.bp)
    app.register_blueprint(listas.bp)
    app.register_blueprint(lista_compra.bp)
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
