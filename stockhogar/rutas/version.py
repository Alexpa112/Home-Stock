"""Endpoint para cache busting: devuelve la versión del servidor."""
import os
from flask import Blueprint, jsonify

bp = Blueprint("version", __name__, url_prefix="/api")


@bp.route("/cache-version", methods=["GET"])
def cache_version():
    """Devuelve la versión del servidor para cache busting.

    El cliente guarda esta versión en localStorage. Si la versión cambia,
    significa que el servidor fue desplegado (git pull + rebuild),
    y el cliente debe limpiar el caché y recargar.

    Usamos el timestamp de docker-compose.yml porque:
    - Se actualiza con cada 'git pull'
    - Es compartido entre frontend (Next.js) y backend (Flask)
    - Refleja el estado real de la app después del update
    """
    try:
        # Buscar docker-compose.yml en el directorio de la app
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo_dir = os.path.dirname(app_dir)  # Subir dos niveles
        docker_compose_path = os.path.join(repo_dir, "docker-compose.yml")

        if os.path.exists(docker_compose_path):
            mtime = os.path.getmtime(docker_compose_path)
            return jsonify({
                "version": int(mtime),
                "status": "ok",
                "source": "docker-compose.yml"
            })
    except Exception:
        pass

    # Fallback: usar timestamp de __init__.py
    try:
        app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mtime = os.path.getmtime(os.path.join(app_path, "__init__.py"))
        return jsonify({
            "version": int(mtime),
            "status": "ok",
            "source": "__init__.py"
        })
    except Exception:
        # Último recurso: usar la hora actual (fuerza update cada vez)
        import time
        return jsonify({
            "version": int(time.time()),
            "status": "ok",
            "source": "current-time"
        })
