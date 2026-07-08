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
    return cat ? cat.icono : '🗂️';
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
