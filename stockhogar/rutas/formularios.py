"""Rutas para servir formularios HTML dinámicamente"""
from flask import Blueprint, jsonify
from ..api import manejo_errores

bp = Blueprint("formularios", __name__, url_prefix="/api/formularios")


@bp.route("/crear-lista", methods=["GET"])
@manejo_errores
def formulario_crear_lista():
    """Devuelve el HTML del formulario de crear lista"""
    html_form = '''
    <label>Nombre
      <input type="text" name="nombre" maxlength="50" placeholder="Ej. Mi inventario" required aria-label="Nombre de la lista">
    </label>
    <label>Icono
      <div class="icono-selector-row">
        <span id="iconoSeleccionadoNuevaLista" class="icono-display">📋</span>
        <button type="button" id="btnSeleccionarIconoNuevaLista" class="secundario" aria-label="Seleccionar icono">Cambiar icono</button>
      </div>
      <input type="hidden" name="icono" value="📋">
    </label>
    <label>Color de la lista
      <div class="color-picker-row">
        <input type="color" id="crearListaColor" name="color" value="#B5551A">
        <span id="colorPreviewCrear" class="color-preview" style="background-color: #B5551A;"></span>
      </div>
    </label>
    '''
    return jsonify({
        "html": html_form,
        "success": True
    })
