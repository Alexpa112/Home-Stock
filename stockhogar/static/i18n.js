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

    // Traducir categorías después de que el DOM se actualice
    setTimeout(() => this.traducirCategorias(), 100);
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

    // Traducir categorías (con delay para asegurar que los elementos existan)
    setTimeout(() => this.traducirCategorias(), 50);

    // Cargar traducciones de artículos si existen
    this.cargarTraduccionesArticulos(nuevoIdioma);

    // Disparar evento para otros componentes
    window.dispatchEvent(new CustomEvent('idioma-cambiado', {
      detail: { idioma: nuevoIdioma }
    }));
  }

  /**
   * Carga traducciones de artículos personalizados
   */
  async cargarTraduccionesArticulos(idioma) {
    try {
      // Obtener todos los artículos visibles
      const articulos = document.querySelectorAll('[data-articulo-id]');

      for (const elemento of articulos) {
        const articuloId = elemento.dataset.articuloId;
        if (!articuloId) continue;

        try {
          const response = await fetch(`/api/articulos-personalizados/${articuloId}/traducciones/${idioma}`);
          const traducciones = await response.json();

          if (traducciones && traducciones.data) {
            // Actualizar nombre si existe traducción
            if (traducciones.data.nombre) {
              const nombreEl = elemento.querySelector('[data-nombre]');
              if (nombreEl) {
                nombreEl.textContent = traducciones.data.nombre;
              }
            }

            // Actualizar descripción si existe traducción
            if (traducciones.data.descripcion) {
              const descEl = elemento.querySelector('[data-descripcion]');
              if (descEl) {
                descEl.textContent = traducciones.data.descripcion;
              }
            }
          }
        } catch (error) {
          console.debug(`No hay traducciones para artículo ${articuloId}:`, error);
        }
      }
    } catch (error) {
      console.warn('Error cargando traducciones de artículos:', error);
    }
  }

  /**
   * Traduce categorías visibles en la página
   */
  traducirCategorias() {
    console.log('🌍 Traduciendo categorías para idioma:', this.idiomaActual);

    const botones = document.querySelectorAll('button.chip');
    console.log(`🔍 Encontrados ${botones.length} botones chip`);

    // Traducir categorías en filtros (botones chip con data-cat)
    botones.forEach(el => {
      const categoriaOriginal = el.dataset.cat;
      if (categoriaOriginal && categoriaOriginal !== 'todas') {
        // Generar clave usando el dataset.cat (que no tiene emoji)
        const clave = `categoria_${categoriaOriginal.toLowerCase().replace(/ /g, '_').replace(/&/g, 'y')}`;
        const categoriaTrad = this.t(clave) ?? categoriaOriginal;

        // Extraer emoji del texto actual si existe
        const textoActual = el.textContent.trim();
        const partes = textoActual.split(' ');
        let emoji = '';

        if (partes.length > 0 && /^[\p{Emoji_Presentation}]$/u.test(partes[0])) {
          emoji = partes[0];
        }

        el.textContent = emoji ? `${emoji} ${categoriaTrad}` : categoriaTrad;
        console.log(`  Filtro chip: ${categoriaOriginal} -> ${categoriaTrad} (emoji: ${emoji})`);
      }
    });

    // Traducir categorías en tarjetas de productos (en .detalle)
    document.querySelectorAll('.detalle').forEach(el => {
      const texto = el.textContent.trim();
      // El formato es "Categoria · Avisos" o solo "Categoria"
      const partes = texto.split(' · ');
      if (partes.length > 0) {
        const categoriaOriginal = partes[0].trim();

        // No traducir si es vacío o contiene puntos suspensivos
        if (!categoriaOriginal || categoriaOriginal === '...' || categoriaOriginal === '·') {
          return;
        }

        const clave = `categoria_${categoriaOriginal.toLowerCase().replace(/ /g, '_').replace(/&/g, 'y')}`;
        const categoriaTrad = this.t(clave) ?? categoriaOriginal;  // Usar nullish coalescing
        const avisos = partes.slice(1).join(' · ');
        el.textContent = avisos ? `${categoriaTrad} · ${avisos}` : categoriaTrad;
        console.log(`  Tarjeta detalle: ${categoriaOriginal} -> ${categoriaTrad}`);
      }
    });
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
