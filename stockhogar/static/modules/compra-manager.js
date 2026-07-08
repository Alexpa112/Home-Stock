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
      this.render();
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

  // ===== FORMULARIOS MODALES =====
  abrirModalCrear() {
    this._resetearFormularioCompra();
    this.dom.get('compraModalTitulo').textContent = 'Añadir a la lista';
    this.dom.get('compraEditId').value = '';
    this.dom.get('modalCompra').hidden = false;
  }

  abrirModalEditar(id) {
    const articulo = this.obtenerPorId(id);
    if (!articulo) return;

    this._llenarFormularioCompra(articulo);
    this.dom.get('compraModalTitulo').textContent = `Editar: ${articulo.nombre}`;
    this.dom.get('compraEditId').value = id;
    this.dom.get('modalCompra').hidden = false;
  }

  cerrarModal() {
    this.dom.get('modalCompra').hidden = true;
    this._resetearFormularioCompra();
  }

  async guardarArticulo(e) {
    e?.preventDefault();

    const id = parseInt(this.dom.get('compraEditId').value);
    const datos = this._extraerDatosFormularioCompra();

    try {
      if (id) {
        await this.actualizar(id, datos);
      } else {
        await this.crear(datos);
      }
      this.cerrarModal();
    } catch (error) {
      console.error('Error guardando artículo:', error);
      this.notificar('articulo-error', error.message);
    }
  }

  // ===== HELPERS DE FORMULARIO =====
  _extraerDatosFormularioCompra() {
    return {
      nombre: this.dom.get('compraCampoNombre')?.value.trim() || '',
      cantidad: parseInt(this.dom.get('compraCampoCantidad')?.value) || 1,
      unidad: this.dom.get('compraCampoUnidad')?.value.trim() || 'ud',
      categoria: this.dom.get('compraCampoCategoria')?.value || 'Otros',
      icono: this.dom.get('compraCampoIcono')?.value || null,
      sub_descripcion: this.dom.get('compraCampoSubdescripcion')?.value.trim() || null,
    };
  }

  _llenarFormularioCompra(articulo) {
    const form = this.dom.get('formCompra');
    if (!form) return;

    const nombreInput = this.dom.get('compraCampoNombre');
    if (nombreInput) nombreInput.value = articulo.nombre;

    const cantidadInput = this.dom.get('compraCampoCantidad');
    if (cantidadInput) cantidadInput.value = articulo.cantidad || 1;

    const unidadInput = this.dom.get('compraCampoUnidad');
    if (unidadInput) unidadInput.value = articulo.unidad || 'ud';

    const categoriaSelect = this.dom.get('compraCampoCategoria');
    if (categoriaSelect) categoriaSelect.value = articulo.categoria || 'Otros';

    const iconoInput = this.dom.get('compraCampoIcono');
    if (iconoInput) iconoInput.value = articulo.icono || '';

    const subdescInput = this.dom.get('compraCampoSubdescripcion');
    if (subdescInput) subdescInput.value = articulo.sub_descripcion || '';
  }

  _resetearFormularioCompra() {
    const form = this.dom.get('formCompra');
    if (form) form.reset();
  }

  // ===== RENDERIZADO =====
  render() {
    const gruposCompra = this.dom.gruposCompra;
    const compraVacia = this.dom.compraVacia;

    if (!gruposCompra) return;

    // Agrupar artículos por categoría
    const agrupados = this._agruparPorCategoria(this.pendientes);

    // Renderizar grupos
    gruposCompra.innerHTML = Object.entries(agrupados)
      .map(([categoria, articulos]) => this._crearGrupo(categoria, articulos))
      .join('');

    // Mostrar/ocultar mensaje vacío
    if (compraVacia) {
      compraVacia.hidden = this.pendientes.length > 0;
    }

    // Re-agregar event listeners
    gruposCompra.querySelectorAll('[data-articulo-id]').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.dataset.articuloId);
        this.notificar('articulo-seleccionado', this.obtenerPorId(id));
      });
    });
  }

  _agruparPorCategoria(articulos) {
    return articulos.reduce((acc, art) => {
      const cat = art.categoria || 'Otros';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(art);
      return acc;
    }, {});
  }

  _crearGrupo(categoria, articulos) {
    const html = articulos.map(a => this._crearTarjeta(a)).join('');
    return `
      <div class="grupo-compra" data-categoria="${categoria}">
        <h3 class="grupo-titulo">${categoria}</h3>
        <div class="grupo-items">
          ${html}
        </div>
      </div>
    `;
  }

  _crearTarjeta(articulo) {
    const nombre = this._escapeHtml(articulo.nombre);
    const cantidad = articulo.cantidad || 1;
    const unidad = articulo.unidad || 'ud';
    const icono = articulo.icono || '📦';
    const subdesc = articulo.sub_descripcion ? `<p class="subdesc">${this._escapeHtml(articulo.sub_descripcion)}</p>` : '';

    return `
      <div class="articulo-compra" data-articulo-id="${articulo.id}">
        <div class="articulo-content">
          <span class="icono">${icono}</span>
          <div class="articulo-info">
            <span class="nombre">${nombre}</span>
            ${subdesc}
            <span class="cantidad">${cantidad} ${unidad}</span>
          </div>
        </div>
        <input type="checkbox" class="articulo-check" ${articulo.activo ? '' : 'checked'}>
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
window.compraManager = new CompraManager(window.API, window.DOM);
