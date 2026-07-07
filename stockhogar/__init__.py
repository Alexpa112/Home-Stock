"""
Stock Hogar - aplicacion ligera para llevar el inventario de productos de casa.
Backend con Flask + SQLite, pensado para correr en una Raspberry Pi 3.
"""
from flask import Flask

from . import db
from .rutas import ajustes, lista_compra, paginas, productos, tickets


def create_app():
    app = Flask(__name__)
    app.teardown_appcontext(db.close_db)

    app.register_blueprint(paginas.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(lista_compra.bp)
    app.register_blueprint(ajustes.bp)
    app.register_blueprint(tickets.bp)

    db.init_db()
    return app
