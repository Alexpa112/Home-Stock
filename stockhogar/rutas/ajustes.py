"""Rutas de ajustes y sincronizacion con Bring!."""
from flask import Blueprint, jsonify, request

from ..db import get_db
from ..integraciones import bring_sync

bp = Blueprint("ajustes", __name__, url_prefix="/api")


def get_ajustes(db):
    filas = db.execute("SELECT clave, valor FROM ajustes").fetchall()
    valores = {f["clave"]: f["valor"] for f in filas}
    return {
        "activado": valores.get("bring_activado") == "1",
        "email": valores.get("bring_email") or "",
        "tiene_password": bool(valores.get("bring_password")),
        "lista_uuid": valores.get("bring_lista_uuid") or "",
        "lista_nombre": valores.get("bring_lista_nombre") or "",
    }


def set_ajuste(db, clave, valor):
    db.execute(
        "INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )


@bp.route("/ajustes", methods=["GET"])
def obtener_ajustes():
    return jsonify(get_ajustes(get_db()))


@bp.route("/ajustes", methods=["POST"])
def guardar_ajustes():
    datos = request.get_json(force=True) or {}
    db = get_db()
    set_ajuste(db, "bring_activado", "1" if datos.get("activado") else "0")
    set_ajuste(db, "bring_email", (datos.get("email") or "").strip())
    if datos.get("password"):
        set_ajuste(db, "bring_password", datos["password"])
    set_ajuste(db, "bring_lista_uuid", datos.get("lista_uuid") or "")
    set_ajuste(db, "bring_lista_nombre", datos.get("lista_nombre") or "")
    db.commit()
    return jsonify(get_ajustes(db))


@bp.route("/bring/listas", methods=["POST"])
def bring_listar_listas():
    datos = request.get_json(force=True) or {}
    email = (datos.get("email") or "").strip()
    password = datos.get("password") or ""
    if not password:
        db = get_db()
        ajustes = db.execute("SELECT valor FROM ajustes WHERE clave = 'bring_password'").fetchone()
        password = ajustes["valor"] if ajustes else ""
    if not email or not password:
        return jsonify({"error": "Introduce el email y la contraseña de Bring!"}), 400

    try:
        listas = bring_sync.obtener_listas(email, password)
    except Exception:
        return jsonify({"error": "No se pudo conectar con Bring!. Revisa el email y la contraseña."}), 400
    return jsonify(listas)


@bp.route("/bring/sincronizar", methods=["POST"])
def bring_sincronizar():
    db = get_db()
    ajustes = get_ajustes(db)
    if not ajustes["activado"] or not ajustes["lista_uuid"] or not ajustes["tiene_password"]:
        return jsonify({"error": "La sincronizacion con Bring! no esta configurada"}), 400

    password_fila = db.execute("SELECT valor FROM ajustes WHERE clave = 'bring_password'").fetchone()
    password = password_fila["valor"] if password_fila else ""

    pendientes = db.execute("SELECT * FROM lista_compra WHERE sincronizado_bring = 0").fetchall()
    if not pendientes:
        return jsonify({"sincronizados": 0})

    nombres = [f["nombre"] for f in pendientes]
    try:
        bring_sync.sincronizar_items(ajustes["email"], password, ajustes["lista_uuid"], nombres)
    except Exception:
        return jsonify({"error": "No se pudo sincronizar con Bring! en este momento."}), 502

    ids = [f["id"] for f in pendientes]
    db.executemany("UPDATE lista_compra SET sincronizado_bring = 1 WHERE id = ?", [(i,) for i in ids])
    db.commit()
    return jsonify({"sincronizados": len(ids)})
