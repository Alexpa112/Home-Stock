/**
 * FORM BUILDER - Generador de formularios dinámicos
 * Crea formularios en JavaScript en lugar de confiar en HTML estático
 * Evita problemas de caching y rendering de Flask/Jinja2
 */

class FormBuilder {
  /**
   * Crea formulario para crear nueva lista
   * @returns {HTMLFormElement} Formulario listo para usar
   */
  static crearFormularioLista() {
    const form = document.createElement('form');
    form.id = 'formCrearLista';
    form.innerHTML = '<label>Nombre<input type="text" name="nombre" maxlength="50" placeholder="Ej. Mi inventario" required aria-label="Nombre de la lista"></label><label>Icono<div class="icono-selector-row"><span id="iconoSeleccionadoNuevaLista" class="icono-display">📋</span><button type="button" id="btnSeleccionarIconoNuevaLista" class="secundario" aria-label="Seleccionar icono">Cambiar icono</button></div><input type="hidden" name="icono" value="📋"></label><label>Color de la lista<div class="color-picker-row"><input type="color" id="crearListaColor" name="color" value="#B5551A"><span id="colorPreviewCrear" class="color-preview" style="background-color: #B5551A;"></span></div></label>';
    // Agregar listener directo al form submit
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (window.crearListaModal) {
        window.crearListaModal.onSubmit(e);
      }
    });
    return form;
  }

  /**
   * Inyecta formulario en un modal existente
   * @param {HTMLElement} modalContent - Contenedor del contenido del modal
   */
  static inyectarFormularioEnModal(modalContent) {
    // Buscar formulario existente
    const formExistente = modalContent.querySelector('form');

    if (formExistente) {
      // Si existe, limpiar y llenar con contenido nuevo
      formExistente.innerHTML = '<label>Nombre<input type="text" name="nombre" maxlength="50" placeholder="Ej. Mi inventario" required aria-label="Nombre de la lista"></label><label>Icono<div class="icono-selector-row"><span id="iconoSeleccionadoNuevaLista" class="icono-display">📋</span><button type="button" id="btnSeleccionarIconoNuevaLista" class="secundario" aria-label="Seleccionar icono">Cambiar icono</button></div><input type="hidden" name="icono" value="📋"></label><label>Color de la lista<div class="color-picker-row"><input type="color" id="crearListaColor" name="color" value="#B5551A"><span id="colorPreviewCrear" class="color-preview" style="background-color: #B5551A;"></span></div></label>';
      // Re-agregar listener después de limpiar innerHTML
      formExistente.addEventListener('submit', (e) => {
        e.preventDefault();
        if (window.crearListaModal) {
          window.crearListaModal.onSubmit(e);
        }
      });
      return formExistente;
    }

    // Si no existe, crear y agregar uno nuevo
    const form = FormBuilder.crearFormularioLista();
    modalContent.appendChild(form);

    return form;
  }

  /**
   * Valida que un formulario de lista tenga los campos requeridos
   * @param {HTMLFormElement} form - Formulario a validar
   * @returns {boolean} True si es válido
   */
  static validarFormularioLista(form) {
    const nombre = form.querySelector('input[name="nombre"]')?.value?.trim();
    if (!nombre) {
      alert('El nombre de la lista es requerido');
      return false;
    }
    return true;
  }
}
