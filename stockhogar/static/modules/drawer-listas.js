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
      btnEditarNombreImagen.addEventListener('click', () => this.abrirModalNombreImagen());
    }

    // Event listener para ordenando
    const btnOrdenando = document.getElementById('btnOrdenando');
    if (btnOrdenando) {
      btnOrdenando.addEventListener('click', () => this.abrirModalOrdenando());
    }

    // Event listener para región
    const btnRegion = document.getElementById('btnRegion');
    if (btnRegion) {
      btnRegion.addEventListener('click', () => this.abrirModalRegion());
    }

    // Event listeners para iconos en modal nombre/imagen
    const iconButtons = document.querySelectorAll('.icon-button');
    iconButtons.forEach(btn => {
      btn.addEventListener('click', (e) => this.seleccionarIcon(e));
    });

    // Event listener para color en modal nombre/imagen
    const colorInput = document.getElementById('inputColorLista');
    if (colorInput) {
      colorInput.addEventListener('change', (e) => this.actualizarPreviewColor(e.target.value));
    }

    // Event listener para gestionar miembros
    const btnGestionarMiembros = document.getElementById('btnGestionarMiembros');
    if (btnGestionarMiembros) {
      btnGestionarMiembros.addEventListener('click', () => {
        this.abrirGestionarMiembros();
        // Asegurar que los tabs de compartir estén disponibles
        setTimeout(() => this.initEventListenersTabs(), 100);
      });
    }

    // Event listeners para tabs de compartir
    const tabPorUsuario = document.getElementById('tabPorUsuario');
    const tabPorEmail = document.getElementById('tabPorEmail');
    const tabPorEnlace = document.getElementById('tabPorEnlace');

    if (tabPorUsuario) tabPorUsuario.addEventListener('click', () => this.cambiarTabCompartir('usuario'));
    if (tabPorEmail) tabPorEmail.addEventListener('click', () => this.cambiarTabCompartir('email'));
    if (tabPorEnlace) tabPorEnlace.addEventListener('click', () => this.cambiarTabCompartir('enlace'));

    // Event listener para búsqueda de usuarios
    const buscarUsuario = document.getElementById('buscarUsuario');
    if (buscarUsuario) {
      buscarUsuario.addEventListener('input', (e) => this.buscarUsuarios(e.target.value));
    }

    // Event listeners para formularios de compartir
    const formCompartirPorUsuario = document.getElementById('formCompartirPorUsuario');
    if (formCompartirPorUsuario) {
      formCompartirPorUsuario.addEventListener('submit', (e) => this.compartirPorUsuario(e));
    }

    const formCompartirPorEmail = document.getElementById('formCompartirPorEmail');
    if (formCompartirPorEmail) {
      formCompartirPorEmail.addEventListener('submit', (e) => this.compartirPorEmail(e));
    }

    // Event listener para generar enlace
    const btnGenerarEnlace = document.getElementById('btnGenerarEnlace');
    if (btnGenerarEnlace) {
      btnGenerarEnlace.addEventListener('click', () => this.generarEnlaceCompartir());
    }

    // Event listener para compartir por WhatsApp
    const btnCompartirWhatsApp = document.getElementById('btnCompartirWhatsApp');
    if (btnCompartirWhatsApp) {
      btnCompartirWhatsApp.addEventListener('click', () => this.compartirPorWhatsApp());
    }

    // Event listener para copiar enlace
    const btnCopiarEnlace = document.getElementById('btnCopiarEnlace');
    if (btnCopiarEnlace) {
      btnCopiarEnlace.addEventListener('click', () => this.copiarEnlace());
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

  abrirModalNombreImagen() {
    const modal = document.getElementById('modalNombreImagen');
    const input = document.getElementById('inputNombreLista');
    const color = document.getElementById('inputColorLista');
    const lista = this.listas.find(l => l.id === this.listaEditandoId);

    if (modal && lista) {
      if (input) input.value = lista.nombre;
      if (color) color.value = lista.color || '#B5551A';
      this.actualizarPreviewColor(lista.color || '#B5551A');

      // Establecer icono seleccionado
      document.querySelectorAll('.icon-button').forEach(btn => {
        btn.style.border = '1px solid var(--border)';
      });
      const iconoActual = document.querySelector(`.icon-button[data-icon="${lista.icono || '📋'}"]`);
      if (iconoActual) iconoActual.style.border = '2px solid var(--accent)';

      modal.hidden = false;
      if (input) input.focus();
    }
  }

  async guardarNombreImagen() {
    if (!this.listaEditandoId) return;

    const nombre = document.getElementById('inputNombreLista')?.value.trim();
    const color = document.getElementById('inputColorLista')?.value;
    const iconoSeleccionado = document.querySelector('.icon-button[style*="border-bottom: 3px"]');
    const icono = document.querySelector('.icon-button[style*="2px solid var(--accent)"]')?.dataset.icon;

    if (!nombre) {
      alert('El nombre no puede estar vacío');
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, color, icono })
      });

      if (!res.ok) {
        const error = await res.json();
        alert(error.error || 'Error al guardar');
        return;
      }

      // Actualizar en memoria
      const lista = this.listas.find(l => l.id === this.listaEditandoId);
      if (lista) {
        lista.nombre = nombre;
        lista.color = color;
        if (icono) lista.icono = icono;
      }

      // Actualizar preview
      const previewEl = document.getElementById('previewLista');
      if (previewEl) {
        previewEl.style.backgroundColor = color;
        previewEl.innerHTML = `<h3>${this.escaparHTML(nombre)}</h3>`;
      }

      // Cerrar modal
      document.getElementById('modalNombreImagen').hidden = true;
      alert('Cambios guardados correctamente');
      this.refrescar();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al guardar cambios');
    }
  }

  abrirModalOrdenando() {
    const modal = document.getElementById('modalOrdenando');
    if (modal) modal.hidden = false;
  }

  abrirModalRegion() {
    const modal = document.getElementById('modalRegion');
    if (modal) modal.hidden = false;
  }

  seleccionarIcon(e) {
    e.preventDefault();
    e.target.parentElement?.querySelectorAll('.icon-button').forEach(btn => {
      btn.style.border = '1px solid var(--border)';
    });
    e.target.style.border = '2px solid var(--accent)';
  }

  actualizarPreviewColor(color) {
    const preview = document.getElementById('previewColorLista');
    if (preview) preview.style.backgroundColor = color;
  }

  abrirGestionarMiembros() {
    const seccionMiembros = document.getElementById('seccionMiembros');
    if (seccionMiembros) {
      seccionMiembros.style.display = 'block';
      this.cargarMiembros();
      this.initEventListenersTabs();
    }
  }

  initEventListenersTabs() {
    // Tabs de compartir
    const tabPorUsuario = document.getElementById('tabPorUsuario');
    const tabPorEmail = document.getElementById('tabPorEmail');
    const tabPorEnlace = document.getElementById('tabPorEnlace');

    if (tabPorUsuario) tabPorUsuario.addEventListener('click', () => this.cambiarTabCompartir('usuario'));
    if (tabPorEmail) tabPorEmail.addEventListener('click', () => this.cambiarTabCompartir('email'));
    if (tabPorEnlace) tabPorEnlace.addEventListener('click', () => this.cambiarTabCompartir('enlace'));

    // Búsqueda de usuarios
    const buscarUsuario = document.getElementById('buscarUsuario');
    if (buscarUsuario) {
      buscarUsuario.addEventListener('input', (e) => this.buscarUsuarios(e.target.value));
    }

    // Formularios de compartir
    const formCompartirPorUsuario = document.getElementById('formCompartirPorUsuario');
    if (formCompartirPorUsuario) {
      formCompartirPorUsuario.addEventListener('submit', (e) => this.compartirPorUsuario(e));
    }

    const formCompartirPorEmail = document.getElementById('formCompartirPorEmail');
    if (formCompartirPorEmail) {
      formCompartirPorEmail.addEventListener('submit', (e) => this.compartirPorEmail(e));
    }

    // Botón generar enlace
    const btnGenerarEnlace = document.getElementById('btnGenerarEnlace');
    if (btnGenerarEnlace) {
      btnGenerarEnlace.addEventListener('click', () => this.generarEnlaceCompartir());
    }

    // Botón copiar enlace
    const btnCopiarEnlace = document.getElementById('btnCopiarEnlace');
    if (btnCopiarEnlace) {
      btnCopiarEnlace.addEventListener('click', () => this.copiarEnlace());
    }

    // Botón WhatsApp
    const btnCompartirWhatsApp = document.getElementById('btnCompartirWhatsApp');
    if (btnCompartirWhatsApp) {
      btnCompartirWhatsApp.addEventListener('click', () => this.compartirPorWhatsApp());
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

  async cargarMiembros() {
    if (!this.listaEditandoId) return;

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/miembros`);
      if (!res.ok) {
        throw new Error('No se pudieron cargar los miembros');
      }

      const data = await res.json();
      this.renderizarMiembros(data.data);
    } catch (error) {
      console.error('Error cargando miembros:', error);
      const listaMiembros = document.getElementById('listaMiembros');
      if (listaMiembros) {
        listaMiembros.innerHTML = '<div style="padding: 12px; text-align: center; color: var(--text-soft);">Error al cargar miembros</div>';
      }
    }
  }

  renderizarMiembros(data) {
    const listaMiembros = document.getElementById('listaMiembros');
    if (!listaMiembros) return;

    const propietario = data.propietario;
    const miembros = data.miembros || [];

    let html = '';

    // Propietario
    html += `
      <div style="padding: 12px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
        <div>
          <strong>${this.escaparHTML(propietario.nombre_usuario)}</strong>
          <div style="font-size: 0.85rem; color: var(--text-soft);">Propietario</div>
        </div>
        <span style="font-size: 0.85rem; color: var(--text-soft);">Propietario</span>
      </div>
    `;

    // Miembros compartidos
    if (miembros.length === 0) {
      html += '<div style="padding: 12px; text-align: center; color: var(--text-soft);">No hay miembros compartidos</div>';
    } else {
      miembros.forEach(m => {
        html += `
          <div style="padding: 12px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>${this.escaparHTML(m.nombre_usuario)}</strong>
              <div style="font-size: 0.85rem; color: var(--text-soft);">${m.email || '-'}</div>
            </div>
            <div style="display: flex; gap: 6px; align-items: center;">
              <select
                data-usuario-id="${m.id}"
                class="selectNivelPermiso"
                style="padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border); font-size: 0.85rem; background: var(--surface-2); color: var(--text);"
              >
                <option value="ver" ${m.nivel === 'ver' ? 'selected' : ''}>Ver</option>
                <option value="editar" ${m.nivel === 'editar' ? 'selected' : ''}>Editar</option>
              </select>
              <button
                class="btnEliminarMiembro"
                data-usuario-id="${m.id}"
                type="button"
                style="padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border); background: var(--surface-2); color: var(--danger); cursor: pointer; font-size: 0.85rem;"
              >
                ✕
              </button>
            </div>
          </div>
        `;
      });
    }

    listaMiembros.innerHTML = html;

    // Event listeners para los select de nivel
    document.querySelectorAll('.selectNivelPermiso').forEach(select => {
      select.addEventListener('change', (e) => this.actualizarPermiso(e));
    });

    // Event listeners para los botones de eliminar
    document.querySelectorAll('.btnEliminarMiembro').forEach(btn => {
      btn.addEventListener('click', (e) => this.revocarAcceso(e));
    });
  }

  async actualizarPermiso(e) {
    const usuarioId = e.target.dataset.usuarioId;
    const nuevoNivel = e.target.value;

    if (!this.listaEditandoId) return;

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/permisos/${usuarioId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nivel: nuevoNivel })
      });

      if (!res.ok) {
        throw new Error('No se pudo actualizar el permiso');
      }

      this.mostrarMensaje('Permiso actualizado', 'exito');
    } catch (error) {
      console.error('Error actualizando permiso:', error);
      this.mostrarMensaje('Error al actualizar el permiso', 'error');
      this.cargarMiembros();
    }
  }

  async revocarAcceso(e) {
    const usuarioId = e.target.dataset.usuarioId;

    if (!this.listaEditandoId) return;

    if (!confirm('¿Estás seguro de que deseas revocar el acceso?')) {
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/permisos/${usuarioId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        throw new Error('No se pudo revocar el acceso');
      }

      this.mostrarMensaje('Acceso revocado', 'exito');
      this.cargarMiembros();
    } catch (error) {
      console.error('Error revocando acceso:', error);
      this.mostrarMensaje('Error al revocar el acceso', 'error');
    }
  }

  cambiarTabCompartir(tab) {
    // Ocultar todos los paneles
    document.getElementById('panelUsuario').style.display = 'none';
    document.getElementById('panelEmail').style.display = 'none';
    document.getElementById('panelEnlace').style.display = 'none';

    // Mostrar panel activo
    if (tab === 'usuario') {
      document.getElementById('panelUsuario').style.display = 'block';
      document.getElementById('buscarUsuario').focus();
    } else if (tab === 'email') {
      document.getElementById('panelEmail').style.display = 'block';
      document.getElementById('emailDestino').focus();
    } else if (tab === 'enlace') {
      document.getElementById('panelEnlace').style.display = 'block';
    }

    // Actualizar estilos de tabs
    document.getElementById('tabPorUsuario').style.color = tab === 'usuario' ? 'var(--text)' : 'var(--text-soft)';
    document.getElementById('tabPorEmail').style.color = tab === 'email' ? 'var(--text)' : 'var(--text-soft)';
    document.getElementById('tabPorEnlace').style.color = tab === 'enlace' ? 'var(--text)' : 'var(--text-soft)';

    document.getElementById('tabPorUsuario').style.borderBottomColor = tab === 'usuario' ? 'var(--accent)' : 'transparent';
    document.getElementById('tabPorEmail').style.borderBottomColor = tab === 'email' ? 'var(--accent)' : 'transparent';
    document.getElementById('tabPorEnlace').style.borderBottomColor = tab === 'enlace' ? 'var(--accent)' : 'transparent';
  }

  async buscarUsuarios(query) {
    if (!query || query.length < 2) {
      document.getElementById('resultadosBusqueda').innerHTML = '';
      return;
    }

    try {
      const res = await fetch(`/api/listas/buscar-usuarios?q=${encodeURIComponent(query)}`);
      if (!res.ok) {
        document.getElementById('resultadosBusqueda').innerHTML = '<p style="color: var(--text-soft); font-size: 0.9rem;">No se encontraron usuarios</p>';
        return;
      }

      const data = await res.json();
      const usuarios = data.data?.usuarios || [];

      if (usuarios.length === 0) {
        document.getElementById('resultadosBusqueda').innerHTML = '<p style="color: var(--text-soft); font-size: 0.9rem;">No se encontraron usuarios</p>';
        return;
      }

      let html = '<div style="display: flex; flex-direction: column; gap: 6px;">';
      usuarios.forEach(u => {
        html += `
          <button type="button" class="usuario-resultado" data-usuario="${u.nombre_usuario}" style="padding: 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); text-align: left; cursor: pointer; transition: all 0.2s;">
            <div style="font-weight: 600; color: var(--text);">${this.escaparHTML(u.nombre_usuario)}</div>
            <div style="font-size: 0.8rem; color: var(--text-soft);">${this.escaparHTML(u.email || '-')}</div>
          </button>
        `;
      });
      html += '</div>';

      document.getElementById('resultadosBusqueda').innerHTML = html;

      // Event listeners para seleccionar usuario
      document.querySelectorAll('.usuario-resultado').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          document.getElementById('buscarUsuario').value = btn.dataset.usuario;
          document.getElementById('resultadosBusqueda').innerHTML = '';
        });
      });
    } catch (error) {
      console.error('Error buscando usuarios:', error);
      document.getElementById('resultadosBusqueda').innerHTML = '<p style="color: var(--text-soft); font-size: 0.9rem;">Error al buscar</p>';
    }
  }

  async compartirPorUsuario(e) {
    e.preventDefault();

    if (!this.listaEditandoId) return;

    const nombreUsuario = document.getElementById('buscarUsuario')?.value.trim() || '';
    const nivel = document.getElementById('nivelPermisoUsuario')?.value || 'editar';

    if (!nombreUsuario) {
      this.mostrarMensaje('Selecciona un usuario', 'error');
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/compartir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre_usuario: nombreUsuario, nivel })
      });

      if (!res.ok) {
        const error = await res.json();
        this.mostrarMensaje(error.error || 'Error al compartir', 'error');
        return;
      }

      this.mostrarMensaje('Lista compartida correctamente!', 'exito');
      document.getElementById('buscarUsuario').value = '';
      document.getElementById('resultadosBusqueda').innerHTML = '';
      this.cargarMiembros();
    } catch (error) {
      console.error('Error:', error);
      this.mostrarMensaje('Error al compartir', 'error');
    }
  }

  async compartirPorEmail(e) {
    e.preventDefault();

    if (!this.listaEditandoId) return;

    const email = document.getElementById('emailDestino')?.value.trim() || '';
    const nivel = document.getElementById('nivelPermisoEmail')?.value || 'editar';

    if (!email) {
      this.mostrarMensaje('Ingresa un email válido', 'error');
      return;
    }

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/compartir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, nivel })
      });

      if (!res.ok) {
        const error = await res.json();
        this.mostrarMensaje(error.error || 'Error al compartir', 'error');
        return;
      }

      const resultado = await res.json();
      if (resultado.data?.codigo) {
        this.mostrarEnlaceInvitacion(resultado.data.codigo);
        this.mostrarMensaje('Enlace de invitación generado!', 'exito');
      }

      document.getElementById('emailDestino').value = '';
      this.cargarMiembros();
    } catch (error) {
      console.error('Error:', error);
      this.mostrarMensaje('Error al compartir', 'error');
    }
  }

  async generarEnlaceCompartir() {
    if (!this.listaEditandoId) return;

    const nivel = document.getElementById('nivelPermisoEnlace')?.value || 'editar';

    // Generar un email temporal para obtener código
    const emailTemporal = `temp_${Date.now()}@dreame.local`;

    try {
      const res = await fetch(`/api/listas/${this.listaEditandoId}/compartir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailTemporal, nivel })
      });

      if (!res.ok) {
        const error = await res.json();
        this.mostrarMensaje(error.error || 'Error al generar enlace', 'error');
        return;
      }

      const resultado = await res.json();
      if (resultado.data?.codigo) {
        this.mostrarEnlaceInvitacion(resultado.data.codigo);
        this.mostrarMensaje('Enlace generado - cópialo y comparte!', 'exito');
      }
    } catch (error) {
      console.error('Error:', error);
      this.mostrarMensaje('Error al generar enlace', 'error');
    }
  }

  mostrarEnlaceInvitacion(codigo) {
    const modal = document.getElementById('modalEnlaceInvitacion');
    const input = document.getElementById('enlaceInvitacionInput');

    if (modal && input) {
      const enlace = `${window.location.origin}/aceptar-invitacion/${codigo}`;
      input.value = enlace;
      modal.style.display = 'block';

      // Auto-ocultar después de 30 segundos
      setTimeout(() => {
        modal.style.display = 'none';
      }, 30000);
    }
  }

  copiarEnlace() {
    const input = document.getElementById('enlaceInvitacionInput');
    if (!input) return;

    input.select();
    document.execCommand('copy');

    this.mostrarMensaje('Enlace copiado al portapapeles!', 'exito');
  }

  mostrarMensaje(mensaje, tipo) {
    const errorEl = document.getElementById('miembrosError');
    const exitoEl = document.getElementById('miembrosExito');

    if (tipo === 'error') {
      if (errorEl) {
        errorEl.textContent = mensaje;
        errorEl.hidden = false;
      }
      if (exitoEl) exitoEl.hidden = true;
    } else {
      if (exitoEl) {
        exitoEl.textContent = mensaje;
        exitoEl.hidden = false;
      }
      if (errorEl) errorEl.hidden = true;
      setTimeout(() => {
        if (exitoEl) exitoEl.hidden = true;
      }, 3000);
    }
  }

  compartirPorWhatsApp() {
    if (!this.listaEditandoId) return;

    const telefonoInput = document.getElementById('inputTelefonoWhatsApp');
    const telefono = (telefonoInput?.value || '').trim();

    // Obtener nombre de la lista
    const lista = this.listas.find(l => l.id === this.listaEditandoId);
    const nombreLista = lista?.nombre || 'Mi lista';

    // Mensaje para WhatsApp con instrucciones
    const mensaje = encodeURIComponent(
      `Hola! Te quiero compartir mi lista de compra "${nombreLista}" en Dreame! (aplicacion de listas compartidas).\n\n` +
      `Puedes verla y actualizarla en tiempo real.\n\n` +
      `Instalate la app en: https://dreame.app (o desde tu navegador en el navegador)\n\n` +
      `¿Te gustaría aceptar?`
    );

    // URL de WhatsApp
    let urlWhatsApp;
    if (telefono) {
      // Con número específico (web.whatsapp)
      urlWhatsApp = `https://wa.me/${telefono}?text=${mensaje}`;
    } else {
      // Sin número (abre chat list en móvil)
      urlWhatsApp = `https://web.whatsapp.com/send?text=${mensaje}`;
    }

    // Abrir WhatsApp
    window.open(urlWhatsApp, '_blank');

    this.mostrarMensaje(
      telefono ? 'Abriendo WhatsApp con el número...' : 'Abriendo WhatsApp...',
      'exito'
    );
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
      await new Promise(resolve => setTimeout(resolve, 300));
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
    this.setupCloseButton();
  }

  setupCloseButton() {
    const btnClose = document.getElementById('btnCerrarCrearLista');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.close());
    }
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
