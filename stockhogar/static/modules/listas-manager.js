/**
 * LISTAS MANAGER - Gestión completa de listas de compra
 * Patrón: Manager OOP + Event Emitter
 * Responsabilidad: CRUD listas, cambio de lista activa, renderizado
 */

class ListasManager {
  constructor(api, dom) {
    this.api = api;
    this.dom = dom;

    // Estado
    this.listas = [];
    this.listaActualId = null;
    this.estaAbiertoModal = false;
    this.modoEdicion = false;
    this.listaEditandoId = null;

    // Event emitter
    this.listeners = new Set();

    // Elementos DOM
    this.modal = this.dom.get('modalMisListas');
    this.listaListasEl = this.dom.get('listaListas');
    this.btnCerrarModal = this.dom.get('btnCerrarMisListas');
    this.btnEditarModal = this.dom.get('btnEditarMisListas');
    this.btnCrearNuevaLista = this.dom.get('btnCrearNuevaLista');
    this.btnAbrirModal = this.dom.get('listaActualBtn');
    this.btnAbrirModal2 = this.dom.get('btnCambiarLista');

    // Modal de editar
    this.modalEditar = this.dom.get('modalEditarLista');
    this.formEditar = this.dom.get('formEditarLista');
    this.inputEditarNombre = this.dom.get('editarListaNombre');
    this.inputEditarColor = this.dom.get('editarListaColor');
    this.btnEliminarLista = this.dom.get('btnEliminarLista');

    // Modal de crear
    this.modalCrear = this.dom.get('modalCrearLista');
    this.formCrear = this.dom.get('formCrearLista');
    this.inputCrearNombre = this.modalCrear?.querySelector('input[name="nombre"]');
    this.inputCrearColor = this.modalCrear?.querySelector('input[name="color"]');

    // Inicializar
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

  // ===== SETUP EVENTOS =====
  _setupEventListeners() {
    // Abrir modal de listas
    if (this.btnAbrirModal) {
      this.btnAbrirModal.addEventListener('click', () => this.abrirModal());
      this.btnAbrirModal.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.abrirModal();
        }
      });
    }

    if (this.btnAbrirModal2) {
      this.btnAbrirModal2.addEventListener('click', () => this.abrirModal());
    }

    // Cerrar modal
    if (this.btnCerrarModal) {
      this.btnCerrarModal.addEventListener('click', () => this.cerrarModal());
    }

    // Editar listas
    if (this.btnEditarModal) {
      this.btnEditarModal.addEventListener('click', () => this.toggleModoEdicion());
    }

    // Crear nueva lista
    if (this.btnCrearNuevaLista) {
      this.btnCrearNuevaLista.addEventListener('click', () => this.abrirModalCrear());
    }

    // Cerrar con ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.estaAbiertoModal) {
        this.cerrarModal();
      }
    });

    // Form editar
    if (this.formEditar) {
      this.formEditar.addEventListener('submit', (e) => this._guardarCambios(e));
    }

    // Form crear
    if (this.formCrear) {
      this.formCrear.addEventListener('submit', (e) => this._guardarNuevaLista(e));
    }

    // Color picker edit
    if (this.inputEditarColor) {
      this.inputEditarColor.addEventListener('change', (e) => {
        const preview = document.getElementById('colorPreview');
        if (preview) preview.style.backgroundColor = e.target.value;
      });
    }

    // Color picker crear
    const colorInputCrear = this.modalCrear?.querySelector('input[name="color"]');
    if (colorInputCrear) {
      colorInputCrear.addEventListener('change', (e) => {
        const preview = document.getElementById('colorPreviewCrear');
        if (preview) preview.style.backgroundColor = e.target.value;
      });
    }

    // Botón eliminar
    if (this.btnEliminarLista) {
      this.btnEliminarLista.addEventListener('click', () => this.borrar(this.listaEditandoId));
    }
  }

  // ===== CRUD =====
  async cargar() {
    try {
      const data = await this.api.obtenerListas();
      this.listas = Array.isArray(data) ? data : [];

      // Obtener lista actual del DOM o localStorage
      const listaActualEl = document.getElementById('listaActualNombre');
      if (listaActualEl && this.listas.length > 0) {
        const nombreActual = listaActualEl.textContent;
        const listaActual = this.listas.find(l => l.nombre === nombreActual);
        if (listaActual) {
          this.listaActualId = listaActual.id;
        }
      }

      this.render();
      this.notificar('listas-cargadas', this.listas);
    } catch (error) {
      console.error('Error cargando listas:', error);
      this.listas = [];
      this.render();
    }
  }

  async crear(datos) {
    try {
      const nuevaLista = await this.api.crearLista(datos);
      this.listas.push(nuevaLista);
      this.render();
      this.notificar('lista-creada', nuevaLista);
      return nuevaLista;
    } catch (error) {
      console.error('Error creando lista:', error);
      throw error;
    }
  }

  async actualizar(id, datos) {
    try {
      const actualizada = await this.api.actualizarLista(id, datos);
      const idx = this.listas.findIndex(l => l.id === id);
      if (idx >= 0) {
        this.listas[idx] = actualizada;
      }
      this.render();
      this.notificar('lista-actualizada', actualizada);
      return actualizada;
    } catch (error) {
      console.error('Error actualizando lista:', error);
      throw error;
    }
  }

  async borrar(id) {
    if (!confirm('¿Eliminar esta lista?')) return;

    try {
      await this.api.borrarLista(id);
      this.listas = this.listas.filter(l => l.id !== id);
      this.render();
      this.cerrarModalEditar();
      this.notificar('lista-borrada', id);

      if (this.listaActualId === id) {
        location.reload();
      }
    } catch (error) {
      console.error('Error borrando lista:', error);
      throw error;
    }
  }

  // ===== CAMBIO DE LISTA =====
  async cambiarLista(listaId) {
    try {
      await this.api.seleccionarLista(listaId);

      // Actualizar localStorage
      const lista = this.listas.find(l => l.id === listaId);
      if (lista) {
        localStorage.setItem('lista-actual', lista.id);
        localStorage.setItem('lista-actual-nombre', lista.nombre);
        localStorage.setItem('lista-actual-icono', lista.icono || '📋');
      }

      this.listaActualId = listaId;
      this.render();
      this.cerrarModal();
      this.notificar('lista-cambiada', listaId);

      // Recargar después de un pequeño delay
      setTimeout(() => location.reload(), 300);
    } catch (error) {
      console.error('Error cambiando lista:', error);
      throw error;
    }
  }

  // ===== MODALES =====
  abrirModal() {
    if (this.estaAbiertoModal) return;
    this.estaAbiertoModal = true;
    if (this.modal) {
      this.modal.hidden = false;
      document.body.classList.add('modal-open');
      this.cargar();
    }
  }

  cerrarModal() {
    if (!this.estaAbiertoModal) return;
    this.estaAbiertoModal = false;
    if (this.modal) {
      this.modal.hidden = true;
      document.body.classList.remove('modal-open');
    }
  }

  abrirModalCrear() {
    if (this.modalCrear) {
      this.cerrarModal();
      this.modalCrear.hidden = false;
      document.body.classList.add('modal-open');
      if (this.inputCrearNombre) {
        setTimeout(() => this.inputCrearNombre.focus(), 100);
      }
    }
  }

  cerrarModalCrear() {
    if (this.modalCrear) {
      this.modalCrear.hidden = true;
      document.body.classList.remove('modal-open');
      if (this.formCrear) this.formCrear.reset();
    }
  }

  abrirModalEditar(listaId) {
    const lista = this.listas.find(l => l.id === listaId);
    if (!lista) return;

    this.listaEditandoId = listaId;
    if (this.inputEditarNombre) this.inputEditarNombre.value = lista.nombre;
    if (this.inputEditarColor) this.inputEditarColor.value = lista.color || '#B5551A';

    const preview = document.getElementById('colorPreview');
    if (preview) preview.style.backgroundColor = lista.color || '#B5551A';

    const previewLista = document.getElementById('previewLista');
    if (previewLista) {
      previewLista.style.backgroundColor = lista.color || '#B5551A';
      previewLista.innerHTML = `<h3>${this._escapeHtml(lista.nombre)}</h3>`;
    }

    if (this.modalEditar) {
      this.cerrarModal();
      this.modalEditar.hidden = false;
      document.body.classList.add('modal-open');
    }
  }

  cerrarModalEditar() {
    if (this.modalEditar) {
      this.modalEditar.hidden = true;
      document.body.classList.remove('modal-open');
    }
    this.listaEditandoId = null;
  }

  toggleModoEdicion() {
    this.modoEdicion = !this.modoEdicion;

    if (this.btnEditarModal) {
      if (this.modoEdicion) {
        this.btnEditarModal.textContent = '✓';
        this.btnEditarModal.style.background = '#4CAF50';
        this.btnEditarModal.style.color = 'white';
      } else {
        this.btnEditarModal.textContent = 'Editar';
        this.btnEditarModal.style.background = 'none';
        this.btnEditarModal.style.color = 'var(--text)';
      }
    }

    this.render();
  }

  // ===== RENDERIZADO =====
  render() {
    if (!this.listaListasEl) return;

    this.listaListasEl.innerHTML = '';

    if (!Array.isArray(this.listas) || this.listas.length === 0) {
      this.listaListasEl.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px 20px; color: var(--text-soft);">Sin listas aún</div>';
      return;
    }

    this.listas.forEach(lista => {
      const tarjeta = this._crearTarjeta(lista);
      this.listaListasEl.appendChild(tarjeta);
    });
  }

  _crearTarjeta(lista) {
    const div = document.createElement('div');
    div.className = 'tarjeta-lista';
    div.style.backgroundColor = lista.color || '#B5551A';
    div.dataset.listaId = lista.id;

    const esActual = this.listaActualId === lista.id;
    div.innerHTML = `
      <div class="tarjeta-header">
        <h3>${this._escapeHtml(lista.nombre)}</h3>
        <button class="btn-editar-tarjeta" aria-label="Editar lista">⚙️</button>
      </div>
      ${esActual ? '<div style="text-align: center; color: white; font-weight: bold;">✓ Activa</div>' : ''}
    `;

    div.addEventListener('click', (e) => {
      if (e.target.closest('.btn-editar-tarjeta')) return;
      if (this.modoEdicion) {
        this.abrirModalEditar(lista.id);
      } else {
        this.cambiarLista(lista.id);
      }
    });

    const btnEditar = div.querySelector('.btn-editar-tarjeta');
    btnEditar.addEventListener('click', (e) => {
      e.stopPropagation();
      this.abrirModalEditar(lista.id);
    });

    return div;
  }

  // ===== HANDLERS PRIVADOS =====
  async _guardarCambios(e) {
    e.preventDefault();

    if (!this.listaEditandoId) {
      alert('Error: No hay lista seleccionada');
      return;
    }

    const nombre = this.inputEditarNombre.value.trim();
    const color = this.inputEditarColor.value;

    if (!nombre) {
      alert('El nombre es requerido');
      return;
    }

    try {
      await this.actualizar(this.listaEditandoId, { nombre, color });
      this.cerrarModalEditar();
      alert('Lista actualizada');
    } catch (error) {
      alert('Error al guardar cambios');
    }
  }

  async _guardarNuevaLista(e) {
    e.preventDefault();

    const nombre = this.inputCrearNombre?.value.trim();
    const color = this.inputCrearColor?.value || '#B5551A';

    if (!nombre) {
      alert('El nombre es requerido');
      return;
    }

    try {
      await this.crear({ nombre, color });
      this.cerrarModalCrear();
      alert('Lista creada');
    } catch (error) {
      alert('Error al crear lista');
    }
  }

  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }
}

// Instanciar cuando esté listo
document.addEventListener('DOMContentLoaded', () => {
  if (window.API && window.DOM) {
    window.listasManager = new ListasManager(window.API, window.DOM);
  }
});
