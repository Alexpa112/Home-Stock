/**
 * HISTORIAL MANAGER - Historial de productos
 * Patrón: Manager OOP + Event Emitter
 * Responsabilidad: Cargar y mostrar historial de cambios
 */

class HistorialManager {
  constructor(api, dom) {
    this.api = api;
    this.dom = dom;

    this.historial = [];
    this.filtroProducto = '';

    // Event emitter
    this.listeners = new Set();

    // DOM
    this.contenedor = this.dom.get('historialContenedor');
    this.btnCargarHistorial = this.dom.get('btnCargarHistorial');
    this.inputBuscarHistorial = this.dom.get('inputBuscarHistorial');

    this._setupEventListeners();
  }

  // ===== EVENT EMITTER =====
  suscribir(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notificar(evento, datos = null) {
    this.listeners.forEach(listener => {
      try {
        listener(evento, datos);
      } catch (error) {
        console.error(`Error en listener para ${evento}:`, error);
      }
    });
  }

  // ===== SETUP =====
  _setupEventListeners() {
    if (this.btnCargarHistorial) {
      this.btnCargarHistorial.addEventListener('click', () => this.cargar());
    }

    if (this.inputBuscarHistorial) {
      this.inputBuscarHistorial.addEventListener('input', (e) => {
        this.filtroProducto = e.target.value.toLowerCase();
        this.render();
      });
    }
  }

  // ===== CRUD =====
  async cargar() {
    try {
      const data = await this.api.obtenerHistorial();
      this.historial = Array.isArray(data) ? data : [];
      this.render();
      this.notificar('historial-cargado', this.historial);
    } catch (error) {
      console.error('Error cargando historial:', error);
      this.historial = [];
    }
  }

  // ===== FILTRADO =====
  obtenerFiltrados() {
    if (!this.filtroProducto) return this.historial;

    return this.historial.filter(item =>
      item.nombre_producto?.toLowerCase().includes(this.filtroProducto) ||
      item.nombre?.toLowerCase().includes(this.filtroProducto)
    );
  }

  // ===== RENDERIZADO =====
  render() {
    if (!this.contenedor) return;

    const filtrados = this.obtenerFiltrados();
    this.contenedor.innerHTML = '';

    if (filtrados.length === 0) {
      this.contenedor.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-soft);">Sin historial</div>';
      return;
    }

    const tabla = document.createElement('table');
    tabla.style.width = '100%';
    tabla.style.borderCollapse = 'collapse';

    // Header
    const headerRow = tabla.insertRow();
    headerRow.style.borderBottom = '2px solid var(--border)';
    ['Producto', 'Acción', 'Cantidad', 'Fecha'].forEach(header => {
      const th = document.createElement('th');
      th.textContent = header;
      th.style.padding = '10px';
      th.style.textAlign = 'left';
      th.style.fontWeight = 'bold';
      headerRow.appendChild(th);
    });

    // Filas
    filtrados.forEach(item => {
      const row = tabla.insertRow();
      row.style.borderBottom = '1px solid var(--border)';

      const cells = [
        item.nombre_producto || item.nombre || '-',
        this._obtenerAccion(item.tipo_cambio),
        item.cantidad_anterior ? `${item.cantidad_anterior} → ${item.cantidad_nueva}` : `${item.cantidad_nueva}`,
        new Date(item.fecha_cambio).toLocaleDateString('es-ES')
      ];

      cells.forEach(text => {
        const td = document.createElement('td');
        td.textContent = text;
        td.style.padding = '10px';
        row.appendChild(td);
      });
    });

    this.contenedor.appendChild(tabla);
  }

  _obtenerAccion(tipo) {
    const acciones = {
      'creacion': '➕ Creado',
      'aumento': '⬆️ Aumentado',
      'disminucion': '⬇️ Disminuido',
      'actualizacion': '✏️ Actualizado',
      'eliminacion': '❌ Eliminado'
    };
    return acciones[tipo] || tipo;
  }
}

// Instanciar cuando esté listo
document.addEventListener('DOMContentLoaded', () => {
  if (window.API && window.DOM) {
    window.historialManager = new HistorialManager(window.API, window.DOM);
  }
});
