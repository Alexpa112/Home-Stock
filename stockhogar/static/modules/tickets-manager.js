/**
 * TICKETS MANAGER - Flujo OCR de tickets desacoplado de app.js
 * Responsabilidad: modal, análisis OCR, revisión y confirmación
 */
class TicketsManager {
  constructor(options = {}) {
    this.fetchImpl = options.fetchImpl || ((...args) => window.fetch(...args));
    this.toast = options.toast || window.Toast || { error: console.error };
    this.escapeHtml = options.escapeHtml || ((texto) => {
      const div = document.createElement('div');
      div.textContent = texto;
      return div.innerHTML;
    });
    this.renderIcon = options.renderIcon || ((icono) => icono || '');
    this.populateCategorySelect = options.populateCategorySelect || (() => {});
    this.getProducts = options.getProducts || (() => []);
    this.onConfirmed = options.onConfirmed || (async () => {});
    this.habilitarBottomSheet = options.habilitarBottomSheet || window.habilitarBottomSheet;

    this.modalFondo = document.getElementById('modalTicket');
    this.ticketPasoFoto = document.getElementById('ticketPasoFoto');
    this.ticketCargando = document.getElementById('ticketCargando');
    this.ticketPasoRevision = document.getElementById('ticketPasoRevision');
    this.ticketArchivo = document.getElementById('ticketArchivo');
    this.ticketDropzone = document.getElementById('ticketDropzone');
    this.ticketPreviewWrap = document.getElementById('ticketPreviewWrap');
    this.ticketPreview = document.getElementById('ticketPreview');
    this.btnCambiarFotoTicket = document.getElementById('btnCambiarFotoTicket');
    this.btnVolverFotoTicket = document.getElementById('btnVolverFotoTicket');
    this.ticketDot1 = document.getElementById('ticketDot1');
    this.ticketDot2 = document.getElementById('ticketDot2');
    this.ticketResumenEl = document.getElementById('ticketResumen');
    this.btnAnalizarTicket = document.getElementById('btnAnalizarTicket');
    this.btnCancelarTicket = document.getElementById('btnCancelarTicket');
    this.btnAnadirLineaTicket = document.getElementById('btnAnadirLineaTicket');
    this.btnConfirmarTicket = document.getElementById('btnConfirmarTicket');
    this.ticketItemsEl = document.getElementById('ticketItems');
    this.ticketAdvertenciasEl = document.getElementById('ticketAdvertencias');
    this.btnEscanearTicket = document.getElementById('btnEscanearTicket');

    this._validarElementos();
    this._registrarEventos();
  }

  _validarElementos() {
    const requeridos = [
      this.modalFondo,
      this.ticketPasoFoto,
      this.ticketCargando,
      this.ticketPasoRevision,
      this.ticketArchivo,
      this.ticketDropzone,
      this.ticketPreviewWrap,
      this.ticketPreview,
      this.btnCambiarFotoTicket,
      this.btnVolverFotoTicket,
      this.ticketDot1,
      this.ticketDot2,
      this.ticketResumenEl,
      this.btnAnalizarTicket,
      this.btnCancelarTicket,
      this.btnAnadirLineaTicket,
      this.btnConfirmarTicket,
      this.ticketItemsEl,
      this.ticketAdvertenciasEl,
    ];
    if (requeridos.some((el) => !el)) {
      throw new Error('Elementos del flujo de tickets incompletos');
    }
  }

  _registrarEventos() {
    if (this.btnEscanearTicket) this.btnEscanearTicket.addEventListener('click', () => this.open());
    this.btnCancelarTicket.addEventListener('click', () => this.close());
    this.btnVolverFotoTicket.addEventListener('click', () => this.irAPasoFoto());
    this.btnAnadirLineaTicket.addEventListener('click', () => {
      this.ticketItemsEl.appendChild(this.crearFilaTicket({ nombre: '', cantidad: 1, unidad: 'ud' }));
    });
    this.btnAnalizarTicket.addEventListener('click', () => this.analizarTicket());
    this.btnConfirmarTicket.addEventListener('click', () => this.confirmarTicket());
    this.ticketArchivo.addEventListener('change', () => {
      const archivo = this.ticketArchivo.files?.[0];
      if (archivo) this.mostrarPreviewTicket(archivo);
    });
    this.btnCambiarFotoTicket.addEventListener('click', () => {
      this.ticketArchivo.value = '';
      this.ticketDropzone.hidden = false;
      this.ticketPreviewWrap.hidden = true;
      this.btnAnalizarTicket.disabled = true;
      this.ticketArchivo.click();
    });

    if (this.modalFondo && this.habilitarBottomSheet) {
      this.habilitarBottomSheet(
        this.modalFondo,
        this.modalFondo.querySelector('.modal'),
        () => this.close()
      );
    }
  }

  t(clave, fallback) {
    return window.i18n ? window.i18n.t(clave) : fallback;
  }

  open() {
    this.ticketArchivo.value = '';
    this.ticketPreview.src = '';
    this.ticketDropzone.hidden = false;
    this.ticketPreviewWrap.hidden = true;
    this.btnAnalizarTicket.disabled = true;
    this.irAPasoFoto();
    this.ticketItemsEl.innerHTML = '';
    this.ticketResumenEl.textContent = '';
    this.mostrarAdvertenciasTicket([]);
    this.modalFondo.hidden = false;
  }

  close() {
    this.modalFondo.hidden = true;
  }

  irAPasoFoto() {
    this.ticketPasoFoto.hidden = false;
    this.ticketCargando.hidden = true;
    this.ticketPasoRevision.hidden = true;
    this.btnVolverFotoTicket.hidden = true;
    this.btnAnalizarTicket.hidden = false;
    this.btnConfirmarTicket.hidden = true;
    this.ticketDot1.classList.add('activo');
    this.ticketDot2.classList.remove('activo');
  }

  irAPasoRevision() {
    this.ticketPasoFoto.hidden = true;
    this.ticketCargando.hidden = true;
    this.ticketPasoRevision.hidden = false;
    this.btnVolverFotoTicket.hidden = false;
    this.btnAnalizarTicket.hidden = true;
    this.btnConfirmarTicket.hidden = false;
    this.ticketDot1.classList.remove('activo');
    this.ticketDot2.classList.add('activo');
  }

  mostrarPreviewTicket(archivo) {
    const lector = new FileReader();
    lector.onload = () => {
      this.ticketPreview.src = lector.result;
      this.ticketDropzone.hidden = true;
      this.ticketPreviewWrap.hidden = false;
      this.btnAnalizarTicket.disabled = false;
    };
    lector.readAsDataURL(archivo);
  }

  opcionesVincular(nombreDetectado) {
    const productos = this.getProducts();
    const coincidencia = productos.find(
      (p) => p.nombre.trim().toLowerCase() === (nombreDetectado || '').trim().toLowerCase()
    );
    let html = '<option value="nuevo">➕ Crear producto nuevo</option>';
    html += productos
      .map(
        (p) =>
          `<option value="${p.id}" ${coincidencia && coincidencia.id === p.id ? 'selected' : ''}>Sumar a: ${this.escapeHtml(p.nombre)} (${p.cantidad} ${this.escapeHtml(p.unidad)})</option>`
      )
      .join('');
    return html;
  }

  mostrarAdvertenciasTicket(advertencias) {
    if (!advertencias || advertencias.length === 0) {
      this.ticketAdvertenciasEl.innerHTML = '';
      this.ticketAdvertenciasEl.hidden = true;
      return;
    }
    this.ticketAdvertenciasEl.hidden = false;
    this.ticketAdvertenciasEl.innerHTML = advertencias
      .map((a) => `<p class="aviso aviso-advertencia">⚠️ ${this.escapeHtml(a.mensaje || '')}</p>`)
      .join('');
  }

  nivelConfianza(confianza) {
    if (confianza === undefined || confianza === null) {
      return { nivel: 'nueva', porcentaje: null, titulo: 'Línea añadida a mano: revísala' };
    }
    let nivel = 'baja';
    if (confianza >= 0.7) nivel = 'alta';
    else if (confianza >= 0.4) nivel = 'media';
    const porcentaje = Math.round(confianza * 100);
    const titulo = nivel === 'alta'
      ? 'Coincidencia fiable con el catálogo'
      : 'Revisa el nombre y la vinculación: coincidencia poco fiable';
    return { nivel, porcentaje, titulo };
  }

  badgeConfianzaMatch(confianza) {
    const { nivel, porcentaje, titulo } = this.nivelConfianza(confianza);
    if (porcentaje === null) return '';
    return `<span class="badge-confianza badge-confianza-${nivel}" title="${titulo}">${porcentaje}% match</span>`;
  }

  crearFilaTicket(item) {
    const { nivel, porcentaje, titulo } = this.nivelConfianza(item.confianza_match);
    const necesitaRevision = nivel !== 'alta';
    const textoConfianza = porcentaje === null ? 'Nueva' : `${porcentaje}%`;

    const li = document.createElement('li');
    li.className = 'ticket-item';
    li.innerHTML = `
      <button type="button" class="ticket-item-resumen" aria-expanded="${necesitaRevision ? 'true' : 'false'}">
        <span class="ticket-item-dot ticket-item-dot-${nivel}" title="${titulo}">${necesitaRevision ? '' : '✓'}</span>
        <span class="ticket-item-resumen-texto">
          <span class="ticket-item-resumen-nombre">${this.escapeHtml(item.nombre || 'Nueva línea')}</span>
          <span class="ticket-item-resumen-meta">
            <span class="ticket-item-resumen-cantidad">${item.cantidad || 1} ${this.escapeHtml(item.unidad || 'ud')}</span>
            <span class="ticket-item-resumen-confianza ticket-item-dot-${nivel}">${textoConfianza}</span>
          </span>
        </span>
        <span class="ticket-item-chevron" aria-hidden="true">⌄</span>
      </button>
      <div class="ticket-item-detalle" ${necesitaRevision ? '' : 'hidden'}>
        <div class="ticket-item-cabecera">
          <input type="text" name="nombre" class="ticket-item-nombre" value="${this.escapeHtml(item.nombre || '')}" placeholder="Nombre del artículo">
          ${this.badgeConfianzaMatch(item.confianza_match)}
          <button type="button" class="ticket-item-quitar" title="Quitar línea" aria-label="Quitar línea">🗑️</button>
        </div>
        <div class="ticket-item-fila">
          <div class="ticket-stepper">
            <button type="button" class="ticket-stepper-btn" data-accion="restar" aria-label="Menos cantidad">−</button>
            <input type="number" name="cantidad" min="1" value="${item.cantidad || 1}" inputmode="numeric">
            <button type="button" class="ticket-stepper-btn" data-accion="sumar" aria-label="Más cantidad">+</button>
          </div>
          <input type="text" name="unidad" class="ticket-item-unidad" value="${this.escapeHtml(item.unidad || 'ud')}" maxlength="10" placeholder="ud" aria-label="Unidad">
        </div>
        <label class="ticket-item-label">Vincular con
          <select name="vincular">${this.opcionesVincular(item.nombre)}</select>
        </label>
        <label class="ticket-item-label" data-campo-categoria>Categoría
          <select name="categoria"></select>
        </label>
      </div>
    `;

    const botonResumen = li.querySelector('.ticket-item-resumen');
    const detalle = li.querySelector('.ticket-item-detalle');
    const nombreResumenEl = li.querySelector('.ticket-item-resumen-nombre');
    const cantidadResumenEl = li.querySelector('.ticket-item-resumen-cantidad');
    const inputNombre = li.querySelector('input[name="nombre"]');
    const inputCantidad = li.querySelector('input[name="cantidad"]');
    const inputUnidad = li.querySelector('input[name="unidad"]');

    botonResumen.addEventListener('click', () => {
      const abierto = botonResumen.getAttribute('aria-expanded') === 'true';
      botonResumen.setAttribute('aria-expanded', abierto ? 'false' : 'true');
      detalle.hidden = abierto;
      if (!abierto) inputNombre.focus();
    });

    const sincronizarResumen = () => {
      nombreResumenEl.textContent = inputNombre.value.trim() || 'Nueva línea';
      cantidadResumenEl.textContent = `${Number(inputCantidad.value) || 1} ${inputUnidad.value.trim() || 'ud'}`;
    };
    inputNombre.addEventListener('input', sincronizarResumen);
    inputUnidad.addEventListener('input', sincronizarResumen);
    inputCantidad.addEventListener('input', sincronizarResumen);

    const selectVincular = li.querySelector('select[name="vincular"]');
    const selectCategoria = li.querySelector('select[name="categoria"]');
    const campoCategoria = li.querySelector('[data-campo-categoria]');
    this.populateCategorySelect(selectCategoria, 'Otros');
    const actualizarVisibilidadCategoria = () => {
      campoCategoria.hidden = selectVincular.value !== 'nuevo';
    };
    selectVincular.addEventListener('change', actualizarVisibilidadCategoria);
    actualizarVisibilidadCategoria();

    li.querySelectorAll('.ticket-stepper-btn').forEach((boton) => {
      boton.addEventListener('click', () => {
        const actual = Number(inputCantidad.value) || 1;
        const siguiente = boton.dataset.accion === 'sumar' ? actual + 1 : actual - 1;
        inputCantidad.value = Math.max(1, siguiente);
        sincronizarResumen();
      });
    });

    li.querySelector('.ticket-item-quitar').addEventListener('click', () => li.remove());
    return li;
  }

  async analizarTicket() {
    const archivo = this.ticketArchivo.files?.[0];
    if (!archivo) {
      this.toast.error('Elige antes una foto del ticket');
      return;
    }

    this.ticketPasoFoto.hidden = true;
    this.ticketCargando.hidden = false;

    const formData = new FormData();
    formData.append('foto', archivo);

    try {
      const res = await this.fetchImpl('/api/tickets/analizar', { method: 'POST', body: formData });
      const datos = await res.json();
      if (!res.ok) {
        this.toast.error(datos.error || 'No se pudo analizar el ticket');
        this.ticketPasoFoto.hidden = false;
        this.ticketCargando.hidden = true;
        return;
      }

      const items = datos.items || [];
      this.ticketItemsEl.innerHTML = '';
      if (items.length === 0) {
        this.ticketItemsEl.appendChild(this.crearFilaTicket({ nombre: '', cantidad: 1, unidad: 'ud' }));
      } else {
        for (const item of items) {
          this.ticketItemsEl.appendChild(this.crearFilaTicket(item));
        }
      }
      const paraRevisar = items.filter((it) => this.nivelConfianza(it.confianza_match).nivel !== 'alta').length;
      this.ticketResumenEl.textContent = items.length === 0
        ? 'No se detectó ningún artículo. Añádelos a mano.'
        : paraRevisar === 0
        ? `${items.length} artículo${items.length === 1 ? '' : 's'} detectado${items.length === 1 ? '' : 's'} · todo con buena confianza`
        : `${items.length} artículo${items.length === 1 ? '' : 's'} detectado${items.length === 1 ? '' : 's'} · ${paraRevisar} para revisar`;
      this.mostrarAdvertenciasTicket(datos.advertencias || []);
      this.irAPasoRevision();
    } catch (error) {
      console.error('Error analizando ticket:', error);
      this.toast.error('No se pudo analizar el ticket. Comprueba tu conexión e inténtalo de nuevo.');
      this.irAPasoFoto();
    }
  }

  async confirmarTicket() {
    const filas = [...this.ticketItemsEl.querySelectorAll('.ticket-item')];
    const items = filas
      .map((fila) => {
        const nombre = fila.querySelector('[name="nombre"]').value.trim();
        const cantidad = Number(fila.querySelector('[name="cantidad"]').value) || 1;
        const unidad = fila.querySelector('[name="unidad"]').value.trim() || 'ud';
        const vincular = fila.querySelector('[name="vincular"]').value;
        const categoria = fila.querySelector('[name="categoria"]').value;
        if (!nombre) return null;
        return vincular === 'nuevo'
          ? { nombre, cantidad, unidad, categoria }
          : { nombre, cantidad, unidad, producto_id: Number(vincular) };
      })
      .filter(Boolean);

    if (items.length === 0) {
      this.close();
      return;
    }

    this.btnConfirmarTicket.disabled = true;
    try {
      await this.fetchImpl('/api/tickets/confirmar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      });
      await this.onConfirmed();
      this.close();
    } finally {
      this.btnConfirmarTicket.disabled = false;
    }
  }
}

if (typeof module === 'undefined') {
  window.TicketsManager = TicketsManager;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { TicketsManager };
}
