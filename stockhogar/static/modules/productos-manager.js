/**
 * ProductosManager - Gestión centralizada de productos
 * Patrón: Manager singleton (instancia única)
 * Responsabilidad: CRUD productos, filtrado, renderización
 */
class ProductosManager {
  constructor(apiClient, domManager) {
    this.api = apiClient;
    this.dom = domManager;

    this.productos = [];
    this.filtroCategoria = 'todas';
    this.textoBusqueda = '';
    this.listeners = new Set();
  }

  // ===== CARGA DE DATOS =====
  async cargar() {
    try {
      this.productos = await this.api.obtenerProductos();
      this.notificar('productos-cargados', this.productos);
      return this.productos;
    } catch (error) {
      console.error('Error cargando productos:', error);
      throw error;
    }
  }

  // ===== CRUD =====
  async crear(datos) {
    try {
      const producto = await this.api.crearProducto(datos);
      this.productos.push(producto);
      this.notificar('producto-creado', producto);
      return producto;
    } catch (error) {
      console.error('Error creando producto:', error);
      throw error;
    }
  }

  async actualizar(id, datos) {
    try {
      const producto = await this.api.actualizarProducto(id, datos);
      const idx = this.productos.findIndex(p => p.id === id);
      if (idx >= 0) {
        this.productos[idx] = producto;
      }
      this.notificar('producto-actualizado', producto);
      return producto;
    } catch (error) {
      console.error('Error actualizando producto:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      await this.api.borrarProducto(id);
      this.productos = this.productos.filter(p => p.id !== id);
      this.notificar('producto-borrado', id);
    } catch (error) {
      console.error('Error borrando producto:', error);
      throw error;
    }
  }

  // ===== FILTRADO =====
  filtrar(categoria = null, texto = null) {
    if (categoria !== null) this.filtroCategoria = categoria;
    if (texto !== null) this.textoBusqueda = (texto || '').toLowerCase().trim();

    this.notificar('filtro-cambiado', {
      categoria: this.filtroCategoria,
      texto: this.textoBusqueda
    });
    this.render();
    return this.obtenerFiltrados();
  }

  obtenerFiltrados() {
    return this.productos.filter(p => {
      // Filtro por categoría
      if (this.filtroCategoria !== 'todas' && p.categoria !== this.filtroCategoria) {
        return false;
      }
      // Filtro por búsqueda de texto
      if (this.textoBusqueda && !p.nombre.toLowerCase().includes(this.textoBusqueda)) {
        return false;
      }
      return true;
    });
  }

  // ===== RENDERIZADO =====
  render() {
    const filtrados = this.obtenerFiltrados();
    const lista = this.dom.lista;
    const vacio = this.dom.vacio;

    if (!lista) return;

    // Renderizar lista de productos
    lista.innerHTML = filtrados.map(p => this._crearTarjeta(p)).join('');

    // Mostrar/ocultar mensaje vacío
    if (vacio) {
      vacio.hidden = filtrados.length > 0;
    }

    // Re-agregar event listeners
    lista.querySelectorAll('[data-producto-id]').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.dataset.productoId);
        this.notificar('producto-seleccionado', this.obtenerPorId(id));
      });
    });
  }

  _crearTarjeta(producto) {
    const icono = producto.icono || '📦';
    const nombre = this._escapeHtml(producto.nombre);
    const cantidad = producto.cantidad || 0;
    const unidad = producto.unidad || 'ud';
    const categoria = producto.categoria || 'Otros';

    return `
      <div class="producto-tarjeta" data-producto-id="${producto.id}">
        <div class="producto-header">
          <span class="icono">${icono}</span>
          <div class="producto-info">
            <h3>${nombre}</h3>
            <p class="categoria">${categoria}</p>
          </div>
        </div>
        <div class="producto-cantidad">
          <span class="cantidad">${cantidad}</span>
          <span class="unidad">${unidad}</span>
        </div>
      </div>
    `;
  }

  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  // ===== HELPERS =====
  obtenerPorId(id) {
    return this.productos.find(p => p.id === id);
  }

  obtenerPorNombre(nombre) {
    return this.productos.find(p => p.nombre === nombre);
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
window.productosManager = new ProductosManager(window.API, window.DOM);
