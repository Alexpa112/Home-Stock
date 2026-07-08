/**
 * PRODUCTOS MANAGER - Gestión de stock
 * Patrón: Manager OOP + Event Emitter
 * Responsabilidad: CRUD productos, filtrado, renderizado con DISEÑO ORIGINAL
 */

class ProductosManager {
  constructor(api, dom) {
    this.api = api;
    this.dom = dom;

    // Estado
    this.productos = [];
    this.filtroCategoria = 'todas';
    this.textoBusqueda = '';

    // Event emitter
    this.listeners = new Set();

    // Elementos DOM
    this.lista = this.dom.get('lista');
    this.vacio = this.dom.get('vacio');
    this.filtros = this.dom.get('filtros');
    this.buscador = this.dom.get('buscador');

    this._setupEventListeners();
    this.cargar();
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
    // Búsqueda de texto
    if (this.buscador) {
      this.buscador.addEventListener('input', (e) => {
        this.textoBusqueda = e.target.value.toLowerCase();
        this.render();
      });
    }

    // Delegación de eventos para cambios rápidos
    document.addEventListener('click', async (e) => {
      if (e.target.classList.contains('btn-sumar')) {
        const id = parseInt(e.target.dataset.id);
        this.cambiarCantidad(id, 1);
      }
      if (e.target.classList.contains('btn-restar')) {
        const id = parseInt(e.target.dataset.id);
        this.cambiarCantidad(id, -1);
      }
      if (e.target.classList.contains('btn-editar')) {
        const id = parseInt(e.target.dataset.id);
        this.abrirModalEditar(id);
      }
      if (e.target.classList.contains('btn-borrar')) {
        const id = parseInt(e.target.dataset.id);
        const producto = this.obtenerPorId(id);
        if (confirm(`¿Borrar "${producto.nombre}"?`)) {
          try {
            await this.borrar(id);
          } catch (error) {
            console.error('Error al borrar producto:', error);
            alert('Error al borrar el producto');
          }
        }
      }
    });
  }

  // ===== CRUD =====
  async cargar() {
    try {
      this.productos = await this.api.obtenerProductos();
      this.render();
      this._cargarFiltros();
      this.notificar('productos-cargados', this.productos);
    } catch (error) {
      console.error('Error cargando productos:', error);
      this.productos = [];
      this.render();
    }
  }

  async crear(datos) {
    try {
      const nuevoProducto = await this.api.crearProducto(datos);
      this.productos.push(nuevoProducto);
      this.render();
      this.notificar('producto-creado', nuevoProducto);
      return nuevoProducto;
    } catch (error) {
      console.error('Error creando producto:', error);
      throw error;
    }
  }

  async actualizar(id, datos) {
    try {
      const actualizado = await this.api.actualizarProducto(id, datos);
      const idx = this.productos.findIndex(p => p.id === id);
      if (idx >= 0) {
        this.productos[idx] = actualizado;
      }
      this.render();
      this.notificar('producto-actualizado', actualizado);
      return actualizado;
    } catch (error) {
      console.error('Error actualizando producto:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      await this.api.borrarProducto(id);
      this.productos = this.productos.filter(p => p.id !== id);
      this.render();
      this.notificar('producto-borrado', id);
    } catch (error) {
      console.error('Error borrando producto:', error);
      throw error;
    }
  }

  // ===== FILTRADO =====
  obtenerFiltrados() {
    return this.productos.filter(p => {
      const pasaCategoria = this.filtroCategoria === 'todas' || p.categoria === this.filtroCategoria;
      const pasaTexto = !this.textoBusqueda || p.nombre.toLowerCase().includes(this.textoBusqueda);
      return pasaCategoria && pasaTexto;
    });
  }

  // ===== BUSQUEDA =====
  obtenerPorId(id) {
    return this.productos.find(p => p.id === id);
  }

  obtenerPorNombre(nombre) {
    return this.productos.find(p => p.nombre.toLowerCase() === nombre.toLowerCase());
  }

  // ===== CAMBIO RÁPIDO DE CANTIDAD =====
  async cambiarCantidad(id, delta) {
    const producto = this.obtenerPorId(id);
    if (!producto) return;

    const cantidadAnterior = producto.cantidad;
    const nuevaCantidad = Math.max(0, producto.cantidad + delta);
    const stockMinimo = producto.stock_minimo || 1;

    try {
      await this.actualizar(id, { cantidad: nuevaCantidad });
      this.notificar('cantidad-cambió', { id, cantidad: nuevaCantidad, delta });

      // STOCK MÍNIMO: Detectar si acabamos de llegar al límite
      if (cantidadAnterior > stockMinimo && nuevaCantidad <= stockMinimo) {
        // Stock ha llegado al mínimo o por debajo
        // Automáticamente añadir a la lista de compra
        await this._anadirAListaCompra(producto);
      }
    } catch (error) {
      alert('Error al cambiar cantidad: ' + error.message);
    }
  }

  async _anadirAListaCompra(producto) {
    try {
      // Buscar instancia global de compraManager (definida en app.js)
      if (window.compraManager) {
        await window.compraManager.crear({
          nombre: producto.nombre,
          categoria: producto.categoria,
          icono: producto.icono,
          cantidad: producto.stock_minimo,
          unidad: producto.unidad || 'ud',
          sub_descripcion: `[Automático: stock bajo]`
        });

        // Mostrar notificación al usuario
        const mensaje = `📦 "${producto.nombre}" ha llegado al stock mínimo. Añadido a la lista de compra.`;
        if (window.notificar) {
          window.notificar(mensaje);
        } else {
          alert(mensaje);
        }
      }
    } catch (error) {
      console.error('Error al añadir a lista de compra:', error);
    }
  }

  // ===== RENDERIZADO =====
  render() {
    if (!this.lista) return;

    const filtrados = this.obtenerFiltrados();
    this.lista.innerHTML = '';

    if (filtrados.length === 0) {
      if (this.vacio) this.vacio.hidden = false;
      return;
    }

    if (this.vacio) this.vacio.hidden = true;

    filtrados.forEach(p => {
      this.lista.appendChild(this._crearTarjeta(p));
    });
  }

  _crearTarjeta(producto) {
    const div = document.createElement('div');

    // Determinar si está bajo stock
    const bajoStock = producto.cantidad < (producto.stock_minimo || 5);
    let clases = 'tarjeta';
    if (bajoStock) clases += ' bajo';
    if (producto.revisar_caducidad) clases += ' aviso-caducidad';

    div.className = clases;
    div.dataset.productoId = producto.id;

    // Avisos
    const avisos = [];
    if (bajoStock) avisos.push('¡Pocas unidades!');
    if (producto.revisar_caducidad) avisos.push('⏰ Revisar caducidad');

    // Icono efectivo
    const icono = producto.icono || this._obtenerIconoCategoria(producto.categoria);
    const nombre = this._escapeHtml(producto.nombre);
    const categoria = this._escapeHtml(producto.categoria);
    const cantidad = producto.cantidad || 0;
    const unidad = producto.unidad || 'ud';
    const detalles = avisos.length ? ` · ${avisos.join(' · ')}` : '';

    div.innerHTML = `
      <div class="icono">${icono}</div>
      <div class="info">
        <div class="nombre">${nombre}</div>
        <div class="detalle">${categoria}${detalles}</div>
      </div>
      <div class="contador">
        <button class="btn-restar" data-id="${producto.id}" title="Quitar uno">−</button>
        <span class="cantidad">${cantidad} ${unidad}</span>
        <button class="btn-sumar" data-id="${producto.id}" title="Añadir uno">+</button>
      </div>
      <div class="acciones">
        <button class="btn-editar" data-id="${producto.id}" title="Editar">✏️</button>
        <button class="btn-borrar" data-id="${producto.id}" title="Eliminar">🗑️</button>
      </div>
    `;

    return div;
  }

  _obtenerIconoCategoria(categoria) {
    const iconos = {
      'Alimentacion': '🍎',
      'Limpieza': '🧴',
      'Higiene': '🧼',
      'Bebidas': '🥤',
      'Otros': '🗂️',
      'Frutas y Verduras': '🥕',
      'Panadería y Bollería': '🥖',
      'Lácteos y Huevos': '🥚',
      'Carnes y Embutidos': '🥩',
      'Pescados y Mariscos': '🐟',
      'Congelados': '🧊',
      'Despensa': '🥫',
      'Cereales y Pasta': '🍝',
      'Snacks y Dulces': '🍫',
      'Bebé': '🍼',
      'Mascotas': '🐶'
    };
    return iconos[categoria] || '📦';
  }

  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  // ===== CARGAR FILTROS =====
  _cargarFiltros() {
    // Obtener categorías únicas
    const categorias = [...new Set(this.productos.map(p => p.categoria))];

    if (this.filtros) {
      this.filtros.innerHTML = '<button class="chip activo" data-cat="todas">Todas</button>';

      categorias.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.textContent = cat;
        btn.dataset.cat = cat;
        btn.addEventListener('click', () => {
          this.filtros.querySelectorAll('.chip').forEach(b => b.classList.remove('activo'));
          btn.classList.add('activo');
          this.filtroCategoria = cat;
          this.render();
          this.notificar('filtro-cambiado', cat);
        });
        this.filtros.appendChild(btn);
      });

      // Click en "Todas"
      this.filtros.querySelector('[data-cat="todas"]').addEventListener('click', () => {
        this.filtros.querySelectorAll('.chip').forEach(b => b.classList.remove('activo'));
        this.filtros.querySelector('[data-cat="todas"]').classList.add('activo');
        this.filtroCategoria = 'todas';
        this.render();
        this.notificar('filtro-cambiado', 'todas');
      });
    }
  }

  // ===== FORMULARIOS MODALES =====
  abrirModalCrear() {
    const modal = this.dom.get('modal');
    if (modal) {
      modal.hidden = false;
      this.dom.get('modalTitulo').textContent = 'Nuevo producto';
      this.dom.get('productoId').value = '';
      if (this.dom.get('formProducto')) this.dom.get('formProducto').reset();
    }
  }

  abrirModalEditar(id) {
    const producto = this.obtenerPorId(id);
    if (!producto) return;

    const modal = this.dom.get('modal');
    if (modal) {
      modal.hidden = false;
      this.dom.get('modalTitulo').textContent = `Editar: ${producto.nombre}`;
      this.dom.get('productoId').value = id;
      this.dom.get('campoNombre').value = producto.nombre;
      this.dom.get('campoCantidad').value = producto.cantidad;
      this.dom.get('campoUnidad').value = producto.unidad || 'ud';
      this.dom.get('campoCategoria').value = producto.categoria;
    }
  }

  cerrarModal() {
    const modal = this.dom.get('modal');
    if (modal) modal.hidden = true;
  }

  async guardarProducto(e) {
    e.preventDefault();

    const id = this.dom.get('productoId').value;
    const nombre = this.dom.get('campoNombre').value.trim();
    const cantidad = parseInt(this.dom.get('campoCantidad').value) || 0;
    const unidad = this.dom.get('campoUnidad').value;
    const categoria = this.dom.get('campoCategoria').value;

    if (!nombre) {
      alert('El nombre es requerido');
      return;
    }

    try {
      const datos = { nombre, cantidad, unidad, categoria };

      if (id) {
        await this.actualizar(parseInt(id), datos);
        alert('Producto actualizado');
      } else {
        await this.crear(datos);
        alert('Producto creado');
      }

      this.cerrarModal();
    } catch (error) {
      alert('Error: ' + error.message);
    }
  }
}

// Instanciar cuando esté listo
document.addEventListener('DOMContentLoaded', () => {
  if (window.API && window.DOM) {
    window.productosManager = new ProductosManager(window.API, window.DOM);
  }
});
