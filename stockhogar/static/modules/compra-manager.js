/**
 * CompraManager - Gestión de artículos en listas de compra
 * Patrón: Manager singleton
 * Responsabilidad: CRUD artículos, pendientes vs completados
 */
class CompraManager {
  constructor(apiClient, domManager) {
    this.api = apiClient;
    this.dom = domManager;

    this.pendientes = [];
    this.completados = [];
    this.listaActualId = null;
    this.listeners = new Set();
  }

  // ===== CARGA DE DATOS =====
  async cargarPorLista(listaId) {
    if (!listaId) {
      console.warn('listaId no proporcionado');
      return;
    }

    try {
      this.listaActualId = listaId;
      const respuesta = await this.api.obtenerArticulos();

      // Suponiendo que la API devuelve { pendientes: [], completados: [] }
      this.pendientes = respuesta?.pendientes || [];
      this.completados = respuesta?.completados || [];

      this.notificar('articulos-cargados', { pendientes: this.pendientes, completados: this.completados });
      return { pendientes: this.pendientes, completados: this.completados };
    } catch (error) {
      console.error('Error cargando artículos:', error);
      throw error;
    }
  }

  // ===== CRUD =====
  async crear(datos) {
    try {
      const articulo = await this.api.crearArticulo(datos);
      this.pendientes.push(articulo);
      this.notificar('articulo-creado', articulo);
      return articulo;
    } catch (error) {
      console.error('Error creando artículo:', error);
      throw error;
    }
  }

  async actualizar(id, datos) {
    try {
      const articulo = await this.api.actualizarArticulo(id, datos);

      // Actualizar en pendientes o completados
      const idxPendiente = this.pendientes.findIndex(a => a.id === id);
      const idxCompletado = this.completados.findIndex(a => a.id === id);

      if (idxPendiente >= 0) {
        this.pendientes[idxPendiente] = articulo;
      } else if (idxCompletado >= 0) {
        this.completados[idxCompletado] = articulo;
      }

      this.notificar('articulo-actualizado', articulo);
      return articulo;
    } catch (error) {
      console.error('Error actualizando artículo:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      await this.api.borrarArticulo(id);
      this.pendientes = this.pendientes.filter(a => a.id !== id);
      this.completados = this.completados.filter(a => a.id !== id);
      this.notificar('articulo-borrado', id);
    } catch (error) {
      console.error('Error borrando artículo:', error);
      throw error;
    }
  }

  // ===== MARCAR COMPLETADO =====
  async marcarCompletado(id, completado = true) {
    return this.actualizar(id, { activo: !completado });
  }

  // ===== HELPERS =====
  obtenerPorId(id) {
    return this.pendientes.find(a => a.id === id) || this.completados.find(a => a.id === id);
  }

  obtenerTodos() {
    return [...this.pendientes, ...this.completados];
  }

  get totalPendientes() {
    return this.pendientes.length;
  }

  get totalCompletados() {
    return this.completados.length;
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
window.compraManager = new CompraManager(window.API, window.DOM);
