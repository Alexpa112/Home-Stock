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
    form.innerHTML = `<label>${(window.i18n && window.i18n.t('nombre')) || 'Nombre'}<input type="text" name="nombre" maxlength="50" placeholder="${(window.i18n && window.i18n.t('ej_mi_inventario')) || 'Ej. Mi inventario'}" required aria-label="${(window.i18n && window.i18n.t('nombre_lista')) || 'Nombre de la lista'}"></label><label>${(window.i18n && window.i18n.t('icono')) || 'Icono'}<div class="icono-selector-row"><span id="iconoSeleccionadoNuevaLista" class="icono-display"><svg class="icono-svg" width="20" height="20" aria-hidden="true"><use href="#icon-h-clipboard-document-list"></use></svg></span><button type="button" id="btnSeleccionarIconoNuevaLista" class="secundario" aria-label="${(window.i18n && window.i18n.t('seleccionar_icono')) || 'Seleccionar icono'}">${(window.i18n && window.i18n.t('cambiar_icono')) || 'Cambiar icono'}</button></div><input type="hidden" name="icono" value="h-clipboard-document-list"></label><label>${(window.i18n && window.i18n.t('color_lista')) || 'Color de la lista'}<div class="color-picker-row"><input type="color" id="crearListaColor" name="color" value="#B5551A"><span id="colorPreviewCrear" class="color-preview" style="background-color: #B5551A;"></span></div></label>`;
    // El submit se gestiona por delegación en el listener del modal
    // (drawer-listas.js), que sobrevive a la regeneración del formulario.
    // No añadir aquí un listener directo: se duplicaría en cada apertura del modal.
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
      formExistente.innerHTML = `<label>${(window.i18n && window.i18n.t('nombre')) || 'Nombre'}<input type="text" name="nombre" maxlength="50" placeholder="${(window.i18n && window.i18n.t('ej_mi_inventario')) || 'Ej. Mi inventario'}" required aria-label="${(window.i18n && window.i18n.t('nombre_lista')) || 'Nombre de la lista'}"></label><label>${(window.i18n && window.i18n.t('icono')) || 'Icono'}<div class="icono-selector-row"><span id="iconoSeleccionadoNuevaLista" class="icono-display"><svg class="icono-svg" width="20" height="20" aria-hidden="true"><use href="#icon-h-clipboard-document-list"></use></svg></span><button type="button" id="btnSeleccionarIconoNuevaLista" class="secundario" aria-label="${(window.i18n && window.i18n.t('seleccionar_icono')) || 'Seleccionar icono'}">${(window.i18n && window.i18n.t('cambiar_icono')) || 'Cambiar icono'}</button></div><input type="hidden" name="icono" value="h-clipboard-document-list"></label><label>${(window.i18n && window.i18n.t('color_lista')) || 'Color de la lista'}<div class="color-picker-row"><input type="color" id="crearListaColor" name="color" value="#B5551A"><span id="colorPreviewCrear" class="color-preview" style="background-color: #B5551A;"></span></div></label>`;
      // El submit se gestiona por delegación en el listener del modal
      // (drawer-listas.js): no reañadir un listener directo aquí.
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
      Toast.error((window.i18n && window.i18n.t('err_nombre_lista_requerido')) || 'El nombre de la lista es requerido');
      return false;
    }
    return true;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormBuilder;
}
