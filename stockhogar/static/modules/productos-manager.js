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

  // ===== FORMULARIOS MODALES =====
  abrirModalCrear() {
    this.notificar('modal-crear-producto', null);
    this._llenarSelectCategoria();
    this._resetearFormulario();
    this.dom.get('modalTitulo').textContent = 'Nuevo producto';
    this.dom.get('productoId').value = '';
    this.dom.get('modal').hidden = false;
  }

  abrirModalEditar(id) {
    const producto = this.obtenerPorId(id);
    if (!producto) return;

    this._llenarSelectCategoria(producto.categoria);
    this._llenarFormularioConProducto(producto);
    this.dom.get('modalTitulo').textContent = `Editar: ${producto.nombre}`;
    this.dom.get('productoId').value = id;
    this.dom.get('modal').hidden = false;
  }

  cerrarModal() {
    this.dom.get('modal').hidden = true;
    this._resetearFormulario();
  }

  async guardarProducto(e) {
    e?.preventDefault();

    const id = parseInt(this.dom.get('productoId').value);
    const datos = this._extraerDatosFormulario();

    try {
      if (id) {
        await this.actualizar(id, datos);
        this.notificar('producto-actualizado-guardado', datos);
      } else {
        await this.crear(datos);
        this.notificar('producto-creado-guardado', datos);
      }
      this.cerrarModal();
    } catch (error) {
      console.error('Error guardando producto:', error);
      this.notificar('producto-error-guardado', error.message);
    }
  }

  // ===== HELPERS DE FORMULARIO =====
  _extraerDatosFormulario() {
    return {
      nombre: this.dom.get('campoNombre').value.trim(),
      categoria: this.dom.get('campoCategoria').value,
      icono: this.dom.get('campoIcono').value || null,
      cantidad: parseInt(this.dom.get('campoCantidad').value) || 0,
      unidad: this.dom.get('campoUnidad').value.trim() || 'ud',
      stock_minimo: parseInt(this.dom.get('campoStockMinimo')?.value) || 1,
      dias_aviso: parseInt(this.dom.get('campoDiasAviso')?.value) || 30,
    };
  }

  _llenarFormularioConProducto(producto) {
    this.dom.get('campoNombre').value = producto.nombre;
    this.dom.get('campoCategoria').value = producto.categoria;
    this.dom.get('campoIcono').value = producto.icono || '';
    this.dom.get('campoCantidad').value = producto.cantidad || 0;
    this.dom.get('campoUnidad').value = producto.unidad || 'ud';

    const stockMinimo = this.dom.get('campoStockMinimo');
    if (stockMinimo) stockMinimo.value = producto.stock_minimo || 1;

    const diasAviso = this.dom.get('campoDiasAviso');
    if (diasAviso) diasAviso.value = producto.dias_aviso || 30;

    this._mostrarIconoSeleccionado(producto.icono);
  }

  _resetearFormulario() {
    const form = this.dom.get('formProducto');
    if (form) form.reset();
    this.dom.get('campoIcono').value = '';
    this._mostrarIconoSeleccionado(null);
  }

  _llenarSelectCategoria(seleccionada = null) {
    const select = this.dom.get('campoCategoria');
    if (!select) return;

    select.innerHTML = `
      <option value="">-- Selecciona categoría --</option>
      ${window.categoriasManager.categorias
        .map(c => `
          <option value="${c.nombre}" ${c.nombre === seleccionada ? 'selected' : ''}>
            ${c.icono} ${c.nombre}
          </option>
        `)
        .join('')}
    `;
  }

  _mostrarIconoSeleccionado(icono) {
    const btn = this.dom.get('btnQuitarIconoProducto');
    if (btn) btn.hidden = !icono;
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
