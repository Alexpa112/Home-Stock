/**
 * CategoriasManager - Gestión de categorías de productos
 * Patrón: Manager singleton
 * Responsabilidad: CRUD categorías
 */
class CategoriasManager {
  constructor(apiClient, domManager) {
    this.api = apiClient;
    this.dom = domManager;

    this.categorias = [];
    this.listeners = new Set();
  }

  // ===== CARGA DE DATOS =====
  async cargar() {
    try {
      this.categorias = await this.api.obtenerCategorias();
      this.notificar('categorias-cargadas', this.categorias);
      this.render();
      return this.categorias;
    } catch (error) {
      console.error('Error cargando categorías:', error);
      throw error;
    }
  }

  // ===== CRUD =====
  async crear(datos) {
    try {
      const categoria = await this.api.crearCategoria(datos);
      this.categorias.push(categoria);
      this.notificar('categoria-creada', categoria);
      return categoria;
    } catch (error) {
      console.error('Error creando categoría:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      await this.api.borrarCategoria(id);
      this.categorias = this.categorias.filter(c => c.id !== id);
      this.notificar('categoria-borrada', id);
    } catch (error) {
      console.error('Error borrando categoría:', error);
      throw error;
    }
  }

  // ===== HELPERS =====
  obtenerPorId(id) {
    return this.categorias.find(c => c.id === id);
  }

  obtenerPorNombre(nombre) {
    return this.categorias.find(c => c.nombre === nombre);
  }

  obtenerIconoPorNombre(nombre) {
    const cat = this.obtenerPorNombre(nombre);
    return cat ? cat.icono : 'h-folder';
  }

  // ===== FORMULARIOS MODALES =====
  abrirModalCrear() {
    this._resetearFormularioCategoria();
    this.dom.get('modal').hidden = false;
  }

  cerrarModal() {
    this.dom.get('modal').hidden = true;
    this._resetearFormularioCategoria();
  }

  async guardarCategoria(e) {
    e?.preventDefault();

    const nombre = this.dom.get('categoriaCampoNombre')?.value.trim();
    const icono = this.dom.get('categoriaCampoIcono')?.value || 'h-folder';

    if (!nombre) {
      console.warn('Nombre de categoría requerido');
      return;
    }

    try {
      await this.crear({ nombre, icono });
      this.cerrarModal();
    } catch (error) {
      console.error('Error guardando categoría:', error);
    }
  }

  // ===== HELPERS DE FORMULARIO =====
  _resetearFormularioCategoria() {
    const form = this.dom.get('formCategoria');
    if (form) form.reset();
  }

  // ===== RENDERIZADO =====
  render() {
    // Renderizar lista de categorías (en modal)
    const categoriasLista = this.dom.get('categoriasLista');
    if (categoriasLista) {
      categoriasLista.innerHTML = this.categorias
        .map(c => this._crearFilaCategoriaLista(c))
        .join('');

      // Re-agregar event listeners
      categoriasLista.querySelectorAll('[data-categoria-id]').forEach(el => {
        el.addEventListener('click', () => {
          const id = parseInt(el.dataset.categoriaId);
          this.notificar('categoria-seleccionada', this.obtenerPorId(id));
        });
      });
    }

    // Renderizar filtros (chips en vista stock)
    const filtros = this.dom.filtros;
    if (filtros) {
      const htmlFiltros = `
        <button class="chip ${this._esActiva('todas') ? 'activo' : ''}" data-categoria="todas">
          Todas
        </button>
        ${this.categorias.map(c => `
          <button class="chip ${this._esActiva(c.nombre) ? 'activo' : ''}" data-categoria="${c.nombre}">
            ${window.renderIcono(c.icono)} ${this._escapeHtml(c.nombre)}
          </button>
        `).join('')}
      `;
      filtros.innerHTML = htmlFiltros;

      // Re-agregar event listeners
      filtros.querySelectorAll('[data-categoria]').forEach(btn => {
        btn.addEventListener('click', () => {
          this._actualizarFiltroUI(btn.dataset.categoria);
        });
      });
    }
  }

  _crearFilaCategoriaLista(categoria) {
    return `
      <div class="categoria-item" data-categoria-id="${categoria.id}">
        <span class="icono">${window.renderIcono(categoria.icono)}</span>
        <span class="nombre">${this._escapeHtml(categoria.nombre)}</span>
      </div>
    `;
  }

  _esActiva(nombre) {
    // Placeholder: necesitaría estado de filtro activo del ProductosManager
    return false;
  }

  _actualizarFiltroUI(categoria) {
    const filtros = this.dom.filtros;
    if (filtros) {
      filtros.querySelectorAll('.chip').forEach(btn => {
        btn.classList.toggle('activo', btn.dataset.categoria === categoria);
      });
    }
    this.notificar('filtro-categoria-cambio', categoria);
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
window.categoriasManager = new CategoriasManager(window.API, window.DOM);
