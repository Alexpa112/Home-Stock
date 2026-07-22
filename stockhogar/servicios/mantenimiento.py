"""Modo mantenimiento: bloquea el uso normal de la app y muestra un aviso a
los usuarios mientras se hacen cambios o backups.

Se controla con un fichero flag en disco (no en la base de datos) para que
sea instantaneo, no dependa de que la BD este disponible, y sobreviva a un
reinicio del proceso si se reinicia con el mantenimiento aun activo.

Esta app solo LEE el flag. Quien lo activa/desactiva es el Panel de Gestion
del Servidor (proyecto independiente, fuera de este repositorio), escribiendo
o borrando el mismo fichero directamente - no hay ninguna llamada de codigo
entre ambos proyectos.
"""
from ..config import DATA_DIR

RUTA_FLAG = DATA_DIR / "mantenimiento.flag"


def activo():
    return RUTA_FLAG.exists()


def mensaje():
    try:
        return RUTA_FLAG.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
