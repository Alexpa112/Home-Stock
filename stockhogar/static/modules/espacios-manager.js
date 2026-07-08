/**
 * EspaciosManager - Gestión de espacios (stocks independientes)
 * Patrón: Manager singleton
 * Responsabilidad: CRUD espacios, cambio de espacio activo
 */
class EspaciosManager {
  constructor(apiClient, domManager) {
    this.api = apiClient;
    this.dom = domManager;

    this.espacios = [];
    this.espacioActualId = null;
    this.listeners = new Set();
  }

  // ===== CARGA DE DATOS =====
  async cargar() {
    try {
      this.espacios = await this.api.obtenerEspacios();
      if (this.espacios.length > 0 && !this.espacioActualId) {
        this.espacioActualId = this.espacios[0].id;
      }
      this.notificar('espacios-cargados', this.espacios);
      this.render();
      return this.espacios;
    } catch (error) {
      console.error('Error cargando espacios:', error);
      throw error;
    }
  }

  // ===== CRUD =====
  async crear(datos) {
    try {
      const espacio = await this.api.crearEspacio(datos);
      this.espacios.push(espacio);
      this.notificar('espacio-creado', espacio);
      return espacio;
    } catch (error) {
      console.error('Error creando espacio:', error);
      throw error;
    }
  }

  async actualizar(id, datos) {
    try {
      const espacio = await this.api.actualizarEspacio(id, datos);
      const idx = this.espacios.findIndex(e => e.id === id);
      if (idx >= 0) {
        this.espacios[idx] = espacio;
      }
      this.notificar('espacio-actualizado', espacio);
      return espacio;
    } catch (error) {
      console.error('Error actualizando espacio:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      await this.api.borrarEspacio(id);
      this.espacios = this.espacios.filter(e => e.id !== id);
      if (this.espacioActualId === id && this.espacios.length > 0) {
        this.seleccionar(this.espacios[0].id);
      }
      this.notificar('espacio-borrado', id);
    } catch (error) {
      console.error('Error borrando espacio:', error);
      throw error;
    }
  }

  // ===== SELECCIÓN DEL ESPACIO ACTUAL =====
  async seleccionar(id) {
    try {
      const espacio = this.obtenerPorId(id);
      if (!espacio) {
        throw new Error(`Espacio ${id} no encontrado`);
      }
      this.espacioActualId = id;
      this.notificar('espacio-seleccionado', espacio);
      return espacio;
    } catch (error) {
      console.error('Error seleccionando espacio:', error);
      throw error;
    }
  }

  // ===== HELPERS =====
  obtenerPorId(id) {
    return this.espacios.find(e => e.id === id);
  }

  obtenerActual() {
    return this.obtenerPorId(this.espacioActualId);
  }

  // ===== RENDERIZADO =====
  render() {
    // Renderizar espacio actual en topbar
    const espacioActualIcono = this.dom.get('espacioActualIcono');
    const espacioActualNombre = this.dom.get('espacioActualNombre');
    const actual = this.obtenerActual();

    if (actual && espacioActualIcono && espacioActualNombre) {
      espacioActualIcono.textContent = actual.icono || '📦';
      espacioActualNombre.textContent = actual.nombre;
    }

    // Renderizar tarjetas de espacios (en modal)
    const espaciosTarjetas = this.dom.espaciosTarjetas;
    if (espaciosTarjetas) {
      espaciosTarjetas.innerHTML = this.espacios
        .map(e => this._crearTarjeta(e))
        .join('');

      // Re-agregar event listeners
      espaciosTarjetas.querySelectorAll('[data-espacio-id]').forEach(el => {
        el.addEventListener('click', () => {
          const id = parseInt(el.dataset.espacioId);
          this.seleccionar(id);
        });
      });
    }
  }

  _crearTarjeta(espacio) {
    const esActual = espacio.id === this.espacioActualId;
    const activo = esActual ? 'activo' : '';
    const nombre = this._escapeHtml(espacio.nombre);

    return `
      <div class="espacio-tarjeta ${activo}" data-espacio-id="${espacio.id}" style="border-color: ${espacio.color || '#999'}">
        <div class="espacio-icono">${espacio.icono || '📦'}</div>
        <h3 class="espacio-nombre">${nombre}</h3>
        <p class="espacio-count">${espacio.productos_count || 0} productos</p>
        ${esActual ? '<span class="espacio-badge">✓ Activo</span>' : ''}
      </div>
    `;
  }

  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  // ===== EVENT EMITTER =====
  suscribir(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notificar(evento, datos) {
    this.listeners.forEach(listener => {
      try {
        listener(evento, datos);
      } catch (error) {
        console.error(`Error en listener para ${evento}:`, error);
      }
    });
  }
}

// Crear instancia global
window.espaciosManager = new EspaciosManager(window.API, window.DOM);
