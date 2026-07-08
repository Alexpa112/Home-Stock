/**
 * DRAWER LISTAS - Gestor profesional de lista de listas
 * Patrón Drawer lateral deslizable para cambiar y crear nuevas listas
 * Arquitectura OOP pura con responsabilidad única
 */

/**
 * Clase para gestionar el drawer de listas
 * Responsabilidad: mostrar/ocultar drawer, cargar listas, cambiar lista, crear nueva
 */
class DrawerListasManager {
  constructor() {
    // Elementos DOM - MODAL EN LUGAR DE DRAWER
    this.modal = document.getElementById('modalMisListas');
    this.listaListasEl = document.getElementById('listaListas');
    this.btnCerrarModal = document.getElementById('btnCerrarMisListas');
    this.btnEditarModal = document.getElementById('btnEditarMisListas');
    this.btnCrearNuevaLista = document.getElementById('btnCrearNuevaLista');
    this.btnAbrirModal = document.getElementById('listaActualBtn');
    this.btnAbrirModal2 = document.getElementById('btnCambiarLista');

    // Modal de editar lista
    this.modalEditar = document.getElementById('modalEditarLista');
    this.formEditar = document.getElementById('formEditarLista');
    this.inputEditarNombre = document.getElementById('editarListaNombre');
    this.inputEditarColor = document.getElementById('editarListaColor');
    this.btnEliminarLista = document.getElementById('btnEliminarLista');
    this.listaEditandoId = null;

    // Estado
    this.listaActualId = null;
    this.listas = [];
    this.estaAbierto = false;
    this.modoEdicion = false;

    // Inicializar
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.cargarListas();
  }

  setupEventListeners() {
    // Abrir modal
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
      this.btnCrearNuevaLista.addEventListener('click', () => {
        this.cerrarModal();
        // Abrir modal de crear lista (integración)
        if (window.crearListaModal) {
          window.crearListaModal.open();
        }
      });
    }

    // Cerrar con tecla ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.estaAbierto) {
        this.cerrarModal();
      }
    });

    // Event listener para guardar cambios en lista
    if (this.formEditar) {
      this.formEditar.addEventListener('submit', (e) => this.guardarCambiosLista(e));
    }

    // Event listener para editar nombre/imagen
    const btnEditarNombreImagen = document.getElementById('btnEditarNombreImagen');
    if (btnEditarNombreImagen) {
      btnEditarNombreImagen.addEventListener('click', () => this.abrirEditarNombreImagen());
    }

    // Event listener para salir de lista
    const btnSalirLista = document.getElementById('btnSalirLista');
    if (btnSalirLista) {
      btnSalirLista.addEventListener('click', () => this.salirDeLista());
    }

    // Actualizar color preview
    if (this.inputEditarColor) {
      this.inputEditarColor.addEventListener('change', (e) => {
        const preview = document.getElementById('colorPreview');
        if (preview) preview.style.backgroundColor = e.target.value;
      });
    }
  }


  async cargarListas() {
    try {
      const res = await fetch('/api/listas');
      if (!res.ok) {
        console.error('Error cargando listas:', res.status);
        this.listas = [];
        this.renderizarListas();
        return;
      }

      const data = await res.json();
      this.listas = [
        ...(Array.isArray(data.propias) ? data.propias : []),
        ...(Array.isArray(data.compartidas) ? data.compartidas : [])
      ];
      console.log('Listas cargadas:', this.listas);

      // Obtener lista actual desde el DOM (más robusto que API)
      const listaActualEl = document.getElementById('listaActualNombre');
      if (listaActualEl && this.listas.length > 0) {
        const nombreActual = listaActualEl.textContent;
        const listaActual = this.listas.find(l => l.nombre === nombreActual);
        if (listaActual) {
          this.listaActualId = listaActual.id;
        }
      }

      this.renderizarListas();
    } catch (error) {
      console.error('Error en cargarListas:', error);
      this.listas = [];
      this.renderizarListas();
    }
  }

  renderizarListas() {
    if (!this.listaListasEl) return;

    this.listaListasEl.innerHTML = '';

    // Asegurar que this.listas es un array
    if (!Array.isArray(this.listas) || this.listas.length === 0) {
      const emptyMsg = document.createElement('div');
      emptyMsg.style.gridColumn = '1 / -1';
      emptyMsg.style.textAlign = 'center';
      emptyMsg.style.padding = '40px 20px';
      emptyMsg.style.color = 'var(--text-soft)';
      emptyMsg.textContent = 'Sin listas aún. Crea una nueva.';
      this.listaListasEl.appendChild(emptyMsg);
      return;
    }

    this.listas.forEach((lista) => {
      const tarjeta = this.crearElementoLista(lista);
      this.listaListasEl.appendChild(tarjeta);
    });
  }

  crearElementoLista(lista) {
    const tarjeta = document.createElement('div');
    tarjeta.className = 'tarjeta-lista';
    tarjeta.style.backgroundColor = lista.color || '#B5551A';
    tarjeta.dataset.listaId = lista.id;

    tarjeta.innerHTML = `
      <div class="tarjeta-header">
        <h3>${this.escaparHTML(lista.nombre)}</h3>
        <button class="btn-editar-tarjeta" aria-label="Editar lista">⚙️</button>
      </div>
      <div class="tarjeta-contenido"></div>
      <div class="tarjeta-avatares" id="avatares-${lista.id}"></div>
    `;

    // Click en tarjeta: depende del modo
    tarjeta.addEventListener('click', (e) => {
      if (e.target.closest('.btn-editar-tarjeta')) return;
      if (this.modoEdicion) {
        this.abrirAjustesLista(lista.id);
      } else {
        this.cambiarLista(lista.id);
      }
    });

    // Click en ⚙️ = siempre abre Ajustes de la lista
    const btnEditar = tarjeta.querySelector('.btn-editar-tarjeta');
    btnEditar.addEventListener('click', (e) => {
      e.stopPropagation();
      this.abrirAjustesLista(lista.id);
    });

    return tarjeta;
  }

  abrirAjustesLista(listaId) {
    const lista = this.listas.find(l => l.id === listaId);
    if (!lista) {
      console.error('Lista no encontrada:', listaId);
      return;
    }

    this.listaEditandoId = listaId;

    // Llenar campos del modal
    if (this.inputEditarNombre) this.inputEditarNombre.value = lista.nombre;
    if (this.inputEditarColor) this.inputEditarColor.value = lista.color || '#B5551A';

    // Actualizar color preview
    const preview = document.getElementById('colorPreview');
    if (preview) preview.style.backgroundColor = lista.color || '#B5551A';

    // Renderizar preview de la lista
    const previewEl = document.getElementById('previewLista');
    if (previewEl) {
      previewEl.style.backgroundColor = lista.color || '#B5551A';
      previewEl.innerHTML = `<h3>${this.escaparHTML(lista.nombre)}</h3>`;
    }

    // Abrir modal
    if (this.modalEditar) {
      this.modalEditar.hidden = false;
      document.body.classList.add('modal-open');
    }

    // Cerrar modal de listas
    this.cerrarModal();
  }

  cerrarModalEditar() {
    if (this.modalEditar) {
      this.modalEditar.hidden = true;
      document.body.classList.remove('modal-open');
    }
    this.listaEditandoId = null;
  }

  async guardarCambiosLista(e) {
    e.preventDefault();

    if (!this.listaEditandoId) {
      alert('Error: No hay lista seleccionada');
      return;
    }

    const nombre = this.inputEditarNombre.value.trim();
    const color = this.inputEditarColor.value;

    if (!nombre) {
      alert('El nombre de la lista es requerido');
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, color })
      });

      if (!res.ok) {
        const error = await res.json();
        alert(error.error || 'Error al guardar cambios');
        return;
      }

      // Actualizar en memoria
      const lista = this.listas.find(l => l.id === this.listaEditandoId);
      if (lista) {
        lista.nombre = nombre;
        lista.color = color;
      }

      this.cerrarModalEditar();
      this.renderizarListas();
      alert('Lista actualizada correctamente');
    } catch (error) {
      console.error('Error guardando cambios:', error);
      alert('Error al guardar cambios');
    }
  }

  abrirEditarNombreImagen() {
    const form = document.getElementById('formEditarLista');
    if (form) {
      form.style.display = 'block';
      const inputNombre = form.querySelector('input[name="nombre"]');
      if (inputNombre) inputNombre.focus();
    }
  }

  async salirDeLista() {
    if (!this.listaEditandoId) return;

    if (!confirm('¿Estás seguro de que deseas salir de esta lista?')) {
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/salir`, {
        method: 'POST'
      });

      if (!res.ok) {
        const error = await res.json();
        alert(error.error || 'Error al salir de la lista');
        return;
      }

      // Eliminar de memoria
      this.listas = this.listas.filter(l => l.id !== this.listaEditandoId);

      this.cerrarModalEditar();
      this.renderizarListas();
      alert('Has salido de la lista');

      // Si la lista era la actual, recargar
      if (this.listaActualId === this.listaEditandoId) {
        location.reload();
      }
    } catch (error) {
      console.error('Error al salir:', error);
      alert('Error al salir de la lista');
    }
  }

  toggleModoEdicion() {
    this.modoEdicion = !this.modoEdicion;

    if (this.modoEdicion) {
      // Agregar clase modo-edicion al contenedor
      if (this.listaListasEl) {
        this.listaListasEl.classList.add('modo-edicion');
      }

      // Cambiar botón a checkmark verde
      this.btnEditarModal.textContent = '✓';
      this.btnEditarModal.style.background = '#4CAF50';
      this.btnEditarModal.style.borderRadius = '50%';
      this.btnEditarModal.style.width = '44px';
      this.btnEditarModal.style.height = '44px';
      this.btnEditarModal.style.display = 'flex';
      this.btnEditarModal.style.alignItems = 'center';
      this.btnEditarModal.style.justifyContent = 'center';
      this.btnEditarModal.style.color = 'white';
      this.btnEditarModal.style.fontSize = '1.5rem';
    } else {
      // Remover clase modo-edicion
      if (this.listaListasEl) {
        this.listaListasEl.classList.remove('modo-edicion');
      }

      // Cambiar botón de vuelta a "Editar"
      this.btnEditarModal.textContent = 'Editar';
      this.btnEditarModal.style.background = 'none';
      this.btnEditarModal.style.borderRadius = '0';
      this.btnEditarModal.style.width = 'auto';
      this.btnEditarModal.style.height = 'auto';
      this.btnEditarModal.style.display = 'block';
      this.btnEditarModal.style.color = 'var(--text)';
      this.btnEditarModal.style.fontSize = '1rem';
    }
  }

  async cambiarLista(listaId) {
    try {
      const res = await fetch(`/api/listas/${listaId}/seleccionar`, {
        method: 'POST'
      });

      if (!res.ok) {
        console.error('Error cambiando lista:', res.status);
        alert('No se pudo cambiar la lista');
        return;
      }

      // Actualizar localStorage para que la app sepa qué lista cargar
      const listaSeleccionada = this.listas.find(l => l.id === listaId);
      if (listaSeleccionada) {
        localStorage.setItem('lista-actual', listaSeleccionada.id);
        localStorage.setItem('lista-actual-nombre', listaSeleccionada.nombre);
        localStorage.setItem('lista-actual-icono', listaSeleccionada.icono || '📋');
      }

      // Actualizar en memoria
      this.listaActualId = listaId;
      this.renderizarListas();
      this.cerrarModal();

      console.log(`Lista seleccionada: ${listaId}`);

      // Recargar la aplicación para mostrar nueva lista
      await this.wait(300);
      location.reload();
    } catch (error) {
      console.error('Error en cambiarLista:', error);
      alert('Error al cambiar de lista');
    }
  }

  abrirModal() {
    if (this.estaAbierto) return;

    this.estaAbierto = true;
    this.modal.hidden = false;
    document.body.classList.add('modal-open');

    // Recargar listas cuando se abre la modal
    this.cargarListas();

    // Agregar drag-down para cerrar
    this.setupDragDown();

    // Enfoque para accesibilidad
    const primerTarjeta = this.listaListasEl.querySelector('.tarjeta-lista');
    if (primerTarjeta) {
      primerTarjeta.focus();
    }
  }

  setupDragDown() {
    const contenedor = this.modal.querySelector('.modal');
    if (!contenedor) return;

    let startY = 0;
    let currentY = 0;
    let isDragging = false;

    contenedor.addEventListener('touchstart', (e) => {
      startY = e.touches[0].clientY;
      currentY = startY;
      isDragging = true;
    });

    contenedor.addEventListener('touchmove', (e) => {
      if (!isDragging) return;
      currentY = e.touches[0].clientY;
      const diff = currentY - startY;
      if (diff > 0) {
        contenedor.style.transform = `translateY(${diff}px)`;
      }
    });

    contenedor.addEventListener('touchend', () => {
      if (!isDragging) return;
      const diff = currentY - startY;
      isDragging = false;

      if (diff > 80) {
        contenedor.style.transform = '';
        this.cerrarModal();
      } else {
        contenedor.style.transform = '';
      }
    });
  }

  cerrarModal() {
    if (!this.estaAbierto) return;

    this.estaAbierto = false;
    this.modal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  escaparHTML(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  // Método para refrescar lista (útil después de crear nueva lista)
  refrescar() {
    this.cargarListas();
  }
}

/**
 * Clase para gestionar el modal de crear nueva lista
 * Responsabilidad: formulario, validación, creación de lista
 */
class CrearListaModal extends FormModal {
  constructor() {
    super('modalCrearLista', 'formCrearLista');
    this.drawerManager = null; // Se asigna después de inicializar
  }

  init() {
    super.init();
    this.setupIconoSelector();
    this.setupValidaciones();
  }

  setupIconoSelector() {
    this.btnIcono = document.getElementById('btnSeleccionarIconoNuevaLista');
    this.iconoSeleccionado = document.getElementById('iconoSeleccionadoNuevaLista');

    if (this.btnIcono) {
      this.btnIcono.addEventListener('click', () => this.abrirSelectorIconos());
    }

    // Color picker
    const colorInput = this.form.querySelector('input[name="color"]');
    if (colorInput) {
      colorInput.addEventListener('change', (e) => {
        const preview = document.getElementById('colorPreviewCrear');
        if (preview) preview.style.backgroundColor = e.target.value;
      });
    }
  }

  setupValidaciones() {
    const inputNombre = this.form.querySelector('input[name="nombre"]');
    if (inputNombre) {
      new ValidatedInput(inputNombre, {
        required: true,
        minLength: 2,
        maxLength: 50,
        errorMessage: 'Entre 2 y 50 caracteres'
      });
    }
  }

  abrirSelectorIconos() {
    // Reutilizar selector de iconos existente
    if (window.abrirModalSelectorIconos) {
      window.abrirModalSelectorIconos();
    }
  }

  onOpen() {
    super.onOpen();
    // Focus en nombre
    const inputNombre = this.form.querySelector('input[name="nombre"]');
    if (inputNombre) {
      setTimeout(() => inputNombre.focus(), 100);
    }
  }

  async onSubmit(e) {
    e.preventDefault();

    const nombre = this.form.querySelector('input[name="nombre"]').value.trim();
    const icono = this.form.querySelector('input[name="icono"]').value || '📋';
    const color = this.form.querySelector('input[name="color"]').value || '#B5551A';

    if (!nombre) {
      alert('El nombre es requerido');
      return;
    }

    try {
      const res = await fetch('/api/listas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, icono, color })
      });

      if (!res.ok) {
        const error = await res.json();
        alert(error.error || 'Error al crear lista');
        return;
      }

      const nuevaLista = await res.json();

      // Actualizar drawer
      if (this.drawerManager) {
        this.drawerManager.refrescar();
      }

      this.close();

      // Mensaje de éxito
      console.log('Lista creada:', nuevaLista.nombre);
    } catch (error) {
      console.error('Error creando lista:', error);
      alert('Error al crear lista');
    }
  }
}

// Inicializar inmediatamente (no esperar a DOMContentLoaded porque app.js ya se ejecutó)
function initializeDrawerListas() {
  console.log('🚀 Inicializando DrawerListasManager...');
  // Crear instancias
  window.drawerListasManager = new DrawerListasManager();
  window.crearListaModal = new CrearListaModal();
  console.log('✅ DrawerListasManager inicializado');

  // Conectar drawer con modal
  if (window.crearListaModal) {
    window.crearListaModal.drawerManager = window.drawerListasManager;
  }

  // Agregar event listener al form
  const form = document.getElementById('formCrearLista');
  if (form) {
    form.addEventListener('submit', (e) => window.crearListaModal.onSubmit(e));
  }
}

// Inicializar si DOM ya está listo, o esperar a que esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDrawerListas);
} else {
  initializeDrawerListas();
}

// Exportar para uso global
window.DrawerListasManager = DrawerListasManager;
window.CrearListaModal = CrearListaModal;
