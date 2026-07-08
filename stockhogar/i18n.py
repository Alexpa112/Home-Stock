"""
Sistema de internacionalización (i18n) para Dreame!

- Detección automática de idioma del sistema
- Selección manual por usuario
- Persistencia en base de datos
- Soporte para 7 idiomas
"""
import locale
from flask import session, request
from flask_babel import Babel, gettext, ngettext


# Idiomas soportados
IDIOMAS_SOPORTADOS = {
    "es": {"nombre": "Español", "nativo": "Español"},
    "gl": {"nombre": "Galego", "nativo": "Galego"},
    "en": {"nombre": "English", "nativo": "English"},
    "pt": {"nombre": "Português", "nativo": "Português"},
    "fr": {"nombre": "Français", "nativo": "Français"},
    "it": {"nombre": "Italiano", "nativo": "Italiano"},
    "de": {"nombre": "Deutsch", "nativo": "Deutsch"},
}

IDIOMAS_PREDEFINIDOS = list(IDIOMAS_SOPORTADOS.keys())


def detectar_idioma_sistema():
    """Detecta el idioma del sistema operativo.

    Returns:
        str: Código de idioma (ej: 'es', 'en', 'pt', 'gl')
    """
    try:
        # Intentar obtener idioma del sistema
        sistema_locale = locale.getdefaultlocale()[0]

        if sistema_locale:
            # Extraer código de idioma (ej: 'es_ES' -> 'es')
            idioma = sistema_locale.split('_')[0].lower()

            # Si está soportado, devolverlo
            if idioma in IDIOMAS_PREDEFINIDOS:
                return idioma
    except Exception:
        pass

    # Default: Español
    return "es"


def obtener_idioma_usuario(db, usuario_id):
    """Obtiene el idioma preferido del usuario.

    Args:
        db: Conexión a BD
        usuario_id: ID del usuario

    Returns:
        str: Código de idioma
    """
    if not usuario_id:
        return detectar_idioma_sistema()

    try:
        usuario = db.execute(
            "SELECT idioma_preferido FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()

        if usuario and usuario["idioma_preferido"]:
            idioma = usuario["idioma_preferido"]
            if idioma in IDIOMAS_PREDEFINIDOS:
                return idioma
    except Exception:
        pass

    # Default al idioma del sistema
    return detectar_idioma_sistema()


def configurar_babel(app):
    """Configura Flask-Babel en la aplicación.

    Args:
        app: Aplicación Flask
    """
    babel = Babel(app)
    app.config['BABEL_DEFAULT_LOCALE'] = 'es'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'stockhogar/translations'

    @babel.localeselector
    def get_locale():
        """Selector de idioma para Babel.

        Prioridad:
        1. Idioma en sesión del usuario
        2. Idioma BD del usuario (si autenticado)
        3. Idioma preferencia navegador
        4. Idioma sistema
        """
        # 1. Verificar sesión
        if 'idioma' in session:
            idioma = session['idioma']
            if idioma in IDIOMAS_PREDEFINIDOS:
                return idioma

        # 2. Verificar BD si está autenticado
        from flask_login import current_user
        if current_user.is_authenticated:
            try:
                from .db import get_db
                db = get_db()
                idioma = obtener_idioma_usuario(db, current_user.id)
                if idioma:
                    return idioma
            except Exception:
                pass

        # 3. Preferencia navegador
        mejor = request.accept_languages.best_match(IDIOMAS_PREDEFINIDOS)
        if mejor:
            return mejor

        # 4. Default
        return detectar_idioma_sistema()

    return babel


# Funciones helper para traducción
def _(mensaje):
    """Traducir mensaje (gettext)."""
    return gettext(mensaje)


def ngettext_fn(singular, plural, n):
    """Traducir mensaje plural."""
    return ngettext(singular, plural, n)
