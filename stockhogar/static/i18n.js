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
    return window.__IDIOMA_INICIAL__ || localStorage.getItem('idioma') || 'es';
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

    // Traducir tabs especiales (la traducción ya incluye el emoji)
    document.querySelectorAll('.tab').forEach(el => {
      const vista = el.dataset.vista;
      if (vista === 'stock') {
        el.textContent = this.t('stock');
      } else if (vista === 'compra') {
        el.textContent = this.t('lista_compra');
      }
    });

    // Traducir botones por su contenido
    const botonesMapeo = {
      'Nuevo producto': 'nuevo_producto',
      'Editar producto': 'editar_producto',
      'Guardar': 'guardar',
      'Cancelar': 'cancelar',
      'Añadir': 'añadir',
      'Eliminar': 'eliminar',
      'Borrar': 'borrar',
      'Cerrar': 'cancelar',
      'Listo': 'ok',
      'Guardar cambios': 'guardar_cambios',
      'Cerrar sesión': 'cerrar_sesion',
    };

    document.querySelectorAll('button, a').forEach(el => {
      const textoLimpio = el.textContent.trim().replace(/^[^\w\s]+ /, '');
      if (botonesMapeo[textoLimpio]) {
        const clave = botonesMapeo[textoLimpio];
        el.textContent = this.t(clave);
      }
    });

    // Traducir todos los inputs con placeholder
    document.querySelectorAll('input[placeholder]').forEach(el => {
      const placeholder = el.getAttribute('placeholder');
      // Mapear placeholders comunes a claves de traducción
      const placeholderMapeo = {
        'Buscar producto...': 'buscar_producto',
        'Ej. Papel higienico': 'ej_papel_higienico',
        'Ej. Bolsas de basura': 'ej_bolsas_basura',
        'Ej. Entera': 'ej_entera',
      };
      if (placeholderMapeo[placeholder]) {
        const trad = this.t(placeholderMapeo[placeholder]);
        el.setAttribute('placeholder', trad);
      }
    });

    // Traducir labels y sus textos.
    // IMPORTANTE: nunca usar `el.textContent = ...` aquí. Muchos <label> de la
    // app envuelven un <input>/<select> (p.ej. <label>Cantidad<input ...></label>),
    // y asignar textContent borra esos hijos (textContent los reemplaza por un
    // único nodo de texto), dejando el campo sin su <input> y rompiendo el
    // formulario entero (añadir producto, añadir a la lista de la compra, etc.).
    // Por eso se sustituye solo dentro de los nodos de texto directos del label.
    const claveMapLabels = {
      'Nombre': 'nombre',
      'Categoria': 'categoria',
      'Icono': 'icono',
      'Cantidad': 'cantidad',
      'Unidad': 'unidad',
      'Stock minimo': 'stock_minimo',
      'Sub-descripción': 'sub_descripcion',
      'Avisar para revisar caducidad si no cambia en (días)': 'avisar_caducidad',
    };

    document.querySelectorAll('label').forEach(el => {
      Array.from(el.childNodes).forEach(nodo => {
        if (nodo.nodeType !== Node.TEXT_NODE) return;
        Object.entries(claveMapLabels).forEach(([texto_es, clave]) => {
          if (nodo.textContent.includes(texto_es)) {
            const trad = this.t(clave);
            nodo.textContent = nodo.textContent.replace(texto_es, trad);
          }
        });
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

    // Traducir mensajes de texto vacío/no hay
    const textoVacioMapeo = {
      'No hay productos. Pulsa "+" para añadir el primero.': 'no_hay_productos',
      'Tu lista de la compra está vacía. Toca "+" para añadir algo.': 'lista_vacia',
      'Comprados recientemente': 'comprados_recientemente',
      '¡Pocas unidades!': 'pocas_unidades',
      '⏰ Revisar caducidad': 'revisar_caducidad',
    };

    document.querySelectorAll('p, span, h2, h3').forEach(el => {
      const texto = el.textContent.trim();
      if (textoVacioMapeo[texto]) {
        const clave = textoVacioMapeo[texto];
        const trad = this.t(clave);
        el.textContent = trad;
      }
    });

    // Actualizar idioma en la página
    document.documentElement.lang = this.idiomaActual;

    // Traducir categorías después de que el DOM se actualice
    setTimeout(() => this.traducirCategorias(), 500);
  }

  /**
   * Cambia el idioma de la página
   */
  async cambiarIdioma(nuevoIdioma) {
    if (nuevoIdioma === this.idiomaActual) return;

    // Guardar en BD
    try {
      const token = document.querySelector('meta[name="csrf-token"]')?.content || '';
      await fetch('/api/idiomas/cambiar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
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
    setTimeout(() => this.traducirCategorias(), 200);

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
          const response = await fetch(`/api/articulos/personalizados/${articuloId}/traducciones/${idioma}`);
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
   * Genera la clave de traducción para una categoría, quitando tildes/diacríticos
   * y caracteres especiales para que sea estable independientemente de cómo
   * esté escrito el nombre original.
   */
  claveCategoria(nombre) {
    const sinTildes = nombre
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, ''); // quita diacríticos (á->a, ñ no se ve afectada)
    return `categoria_${sinTildes
      .toLowerCase()
      .replace(/&/g, 'y')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')}`;
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
        const clave = this.claveCategoria(categoriaOriginal);
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
    const detalles = document.querySelectorAll('.detalle');
    console.log(`🔍 Encontrados ${detalles.length} elementos .detalle`);

    detalles.forEach(el => {
      const texto = el.textContent.trim();
      // El formato es "Categoria · Avisos" o solo "Categoria"
      const partes = texto.split(' · ');
      if (partes.length > 0) {
        // Usar el atributo data-categoria-original si existe, sino usar el textContent
        const categoriaOriginal = el.dataset.categoriaOriginal || partes[0].trim();

        // No traducir si es vacío o contiene puntos suspensivos
        if (!categoriaOriginal || categoriaOriginal === '...' || categoriaOriginal === '·') {
          return;
        }

        const clave = this.claveCategoria(categoriaOriginal);
        // Comprobar explícitamente si la clave existe en las traducciones
        const categoriaTrad = (this.traducciones[clave] !== undefined) ? this.traducciones[clave] : categoriaOriginal;
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
    // Selector principal en ajustes
    const selector = document.getElementById('selector-idioma');
    if (selector) {
      // Establecer valor actual
      selector.value = this.idiomaActual;

      // Agregar listener de cambio
      selector.addEventListener('change', (e) => {
        this.cambiarIdioma(e.target.value);
      });

      console.log('✅ Selector de idioma (ajustes) configurado');
    } else {
      console.warn('⚠️ Selector de idioma (#selector-idioma) no encontrado en el HTML');
    }

    // Selector secundario en modal de región
    const selectorRegion = document.getElementById('selectIdioma');
    if (selectorRegion) {
      // Establecer valor actual
      selectorRegion.value = this.idiomaActual;

      // Agregar listener de cambio
      selectorRegion.addEventListener('change', (e) => {
        this.cambiarIdioma(e.target.value);
      });

      console.log('✅ Selector de idioma (región) configurado');
    } else {
      console.warn('⚠️ Selector de idioma (#selectIdioma) no encontrado en el HTML');
    }

    // Escuchar cambios de idioma para sincronizar ambos selectores
    window.addEventListener('idioma-cambiado', (e) => {
      if (selector) selector.value = e.detail.idioma;
      if (selectorRegion) selectorRegion.value = e.detail.idioma;
    });
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
