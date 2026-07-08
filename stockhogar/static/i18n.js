/**
 * Sistema de traducciones para el frontend
 * Carga traducciones completas y traduce toda la página
 */

class TranslationManager {
  constructor() {
    this.traducciones = {};
    this.idiomaActual = this.obtenerIdiomaGuardado();
    this.inicializar();
  }

  /**
   * Obtiene idioma guardado o el actual de la sesión
   */
  obtenerIdiomaGuardado() {
    return localStorage.getItem('idioma') || 'es';
  }

  /**
   * Inicializa el sistema de traducciones
   */
  async inicializar() {
    await this.cargarTraducciones(this.idiomaActual);
    this.traducirPagina();
    this.configurarSelectorIdioma();
  }

  /**
   * Carga todas las traducciones para un idioma
   */
  async cargarTraducciones(idioma) {
    try {
      const respuesta = await fetch(`/api/idiomas/todos/${idioma}`);
      const datos = await respuesta.json();

      if (datos.success) {
        this.traducciones = datos.data.traducciones;
        this.idiomaActual = idioma;
        localStorage.setItem('idioma', idioma);
      }
    } catch (error) {
      console.error('Error cargando traducciones:', error);
      // Fallback a español
      if (idioma !== 'es') {
        await this.cargarTraducciones('es');
      }
    }
  }

  /**
   * Obtiene una traducción
   */
  t(clave) {
    return this.traducciones[clave] || clave;
  }

  /**
   * Traduce todos los elementos de la página
   */
  traducirPagina() {
    // Traducir por data-i18n="clave"
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const clave = el.dataset.i18n;
      const trad = this.t(clave);

      if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'password')) {
        el.placeholder = trad;
      } else if (el.tagName === 'BUTTON' || el.tagName === 'A') {
        el.textContent = trad;
      } else {
        el.textContent = trad;
      }
    });

    // Traducir atributos title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const clave = el.dataset.i18nTitle;
      el.title = this.t(clave);
    });

    // Traducir atributos placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const clave = el.dataset.i18nPlaceholder;
      el.placeholder = this.t(clave);
    });

    // Actualizar idioma en la página
    document.documentElement.lang = this.idiomaActual;
  }

  /**
   * Cambia el idioma de la página
   */
  async cambiarIdioma(nuevoIdioma) {
    if (nuevoIdioma === this.idiomaActual) return;

    // Guardar en BD
    try {
      await fetch('/api/idiomas/cambiar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idioma: nuevoIdioma })
      });
    } catch (error) {
      console.error('Error guardando idioma:', error);
    }

    // Cargar nuevas traducciones
    await this.cargarTraducciones(nuevoIdioma);

    // Traducir página
    this.traducirPagina();

    // Disparar evento para otros componentes
    window.dispatchEvent(new CustomEvent('idioma-cambiado', {
      detail: { idioma: nuevoIdioma }
    }));
  }

  /**
   * Configura el selector de idioma en la UI
   */
  configurarSelectorIdioma() {
    // Crear selector si no existe
    const selectorExistente = document.getElementById('selector-idioma');
    if (!selectorExistente) {
      this.crearSelectorIdioma();
    }

    // Agregar listener
    const selector = document.getElementById('selector-idioma');
    if (selector) {
      selector.value = this.idiomaActual;
      selector.addEventListener('change', (e) => {
        this.cambiarIdioma(e.target.value);
      });
    }
  }

  /**
   * Crea el selector de idioma en configuración
   */
  crearSelectorIdioma() {
    const config = document.querySelector('[data-seccion="configuracion"]');
    if (!config) return;

    const selector = document.createElement('div');
    selector.className = 'setting-item';
    selector.innerHTML = `
      <label for="selector-idioma">🌐 ${this.t('idioma')}:</label>
      <select id="selector-idioma" class="idioma-select">
        <option value="es">Español</option>
        <option value="gl">Galego</option>
        <option value="en">English</option>
        <option value="pt">Português</option>
        <option value="fr">Français</option>
        <option value="it">Italiano</option>
        <option value="de">Deutsch</option>
      </select>
    `;

    config.appendChild(selector);
    this.configurarSelectorIdioma();
  }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.i18n = new TranslationManager();
  });
} else {
  window.i18n = new TranslationManager();
}
