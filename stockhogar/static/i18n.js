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

      // El endpoint devuelve { idioma: "es", traducciones: {...} }
      if (datos.traducciones) {
        this.traducciones = datos.traducciones;
        this.idiomaActual = idioma;
        localStorage.setItem('idioma', idioma);
        console.log(`✅ Traducciones cargadas para ${idioma}:`, Object.keys(this.traducciones).length, 'claves');
      } else {
        console.error('Respuesta sin traducciones:', datos);
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
    console.log(`📝 Traduciendo página a ${this.idiomaActual}. Traducciones cargadas:`, Object.keys(this.traducciones).length);

    // Mapeo de elementos a claves de traducción
    const elementosTrad = {
      '#buscador': 'buscar_producto',
      '#modalTitulo': 'nuevo_producto',
      '#listaActualRol': 'propietario',
    };

    // Traducir elementos específicos
    Object.entries(elementosTrad).forEach(([selector, clave]) => {
      const elemento = document.querySelector(selector);
      if (elemento && clave) {
        const trad = this.t(clave);
        if (elemento.tagName === 'INPUT') {
          elemento.placeholder = trad;
        } else {
          elemento.textContent = trad;
        }
      }
    });

    // Traducir tabs especiales (mantienen emoji)
    document.querySelectorAll('.tab').forEach(el => {
      const vista = el.dataset.vista;
      if (vista === 'stock') {
        const clave = 'stock';
        const trad = this.t(clave);
        console.log(`Tab stock: ${clave} -> ${trad}`);
        el.textContent = `📦 ${trad}`;
      } else if (vista === 'compra') {
        const clave = 'lista_compra';
        const trad = this.t(clave);
        console.log(`Tab compra: ${clave} -> ${trad}`);
        el.textContent = `🛒 ${trad}`;
      }
    });

    // Traducir botones por su contenido (sin emoji)
    const botonesMapeo = {
      'Nuevo producto': 'nuevo_producto',
      'Editar producto': 'editar_producto',
      'Guardar': 'guardar',
      'Cancelar': 'cancelar',
      'Añadir': 'añadir',
      'Eliminar': 'eliminar',
      'Borrar': 'borrar',
    };

    document.querySelectorAll('button, a').forEach(el => {
      // Limpiador de emojis: mantener solo texto
      const textoLimpio = el.textContent.trim().replace(/^[^\w\s]+ /, '');

      if (botonesMapeo[textoLimpio]) {
        const clave = botonesMapeo[textoLimpio];
        el.textContent = this.t(clave);
      }
    });

    // Traducir labels y placeholders
    document.querySelectorAll('label').forEach(el => {
      const texto = el.textContent.trim();
      const claveMap = {
        'Nombre': 'nombre',
        'Categoria': 'categoria',
        'Icono': 'icono',
        'Cantidad': 'cantidad',
        'Stock minimo': 'cantidad', // Usar clave existente
      };

      Object.entries(claveMap).forEach(([texto_es, clave]) => {
        if (el.textContent.includes(texto_es)) {
          const trad = this.t(clave);
          el.textContent = el.textContent.replace(texto_es, trad);
        }
      });
    });

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
    const selector = document.getElementById('selector-idioma');
    if (!selector) {
      console.warn('⚠️ Selector de idioma no encontrado en el HTML');
      return;
    }

    // Establecer valor actual
    selector.value = this.idiomaActual;

    // Agregar listener de cambio
    selector.addEventListener('change', (e) => {
      this.cambiarIdioma(e.target.value);
    });

    console.log('✅ Selector de idioma configurado');
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
