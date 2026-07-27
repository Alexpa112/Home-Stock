"""Endpoint para cache busting: devuelve la versión del servidor."""
import os
from flask import Blueprint, jsonify

bp = Blueprint("version", __name__, url_prefix="/api")


@bp.route("/cache-version", methods=["GET"])
def cache_version():
    """Devuelve la versión del servidor para cache busting.

    El cliente guarda esta versión en localStorage. Si la versión cambia
    al recargar, significa que el servidor fue desplegado con cambios,
    y el cliente debe limpiar el caché y recargar.
    """
    # Usar el timestamp del archivo de la app como versión
    # (se actualiza con cada push/redeploy)
    app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_mtime = os.path.getmtime(os.path.join(app_path, "__init__.py"))

    return jsonify({
        "version": int(app_mtime),
        "status": "ok"
    })
