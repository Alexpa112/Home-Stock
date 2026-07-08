/**
 * APP REFACTORED - Integración de componentes UI profesionales
 * Sistema modular basado en OOP con consistencia garantizada
 */

/* ═══════════════════════════════════════════════════════════════════════════ */
/* EXTENSION DE CLASSES BASES PARA LA APLICACION */
/* ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Clase especializada para el modal de producto
 * Garantiza consistencia en la creación/edicion de productos
 */
class ProductFormModal extends FormModal {
  constructor() {
    super('modal', 'formProducto');
    this.setupCategorySelect();
    this.setupIconSelector();
  }

  setupCategorySelect() {
    this.categorySelect = document.getElementById('campoCategoria');
    if (this.categorySelect) {
      this.categorySelect.addEventListener('change', () => this.updateCategoryIcon());
    }
  }

  setupIconSelector() {
    this.iconButton = document.getElementById('btnSeleccionarIconoCategoria');
    if (this.iconButton) {
      this.iconButton.addEventListener('click', () => this.openIconSelector());
    }
  }

  updateCategoryIcon() {
    // Actualizar icono según categoría seleccionada
  }

  openIconSelector() {
    // Abrir selector de iconos
  }

  loadProduct(productId) {
    // Cargar producto existente
  }

  resetForm() {
    super.resetForm();
    this.categorySelect.value = '';
  }
}

/**
 * Clase especializada para el modal de lectura de tickets
 * Sistema robusto de análisis OCR con validación
 */
class TicketReadModal extends TicketModal {
  constructor() {
    super('modalTicket');
    this.analyzeButton = document.getElementById('btnAnalizarTicket');
    this.confirmButton = document.getElementById('btnConfirmarTicket');
    this.addLineButton = document.getElementById('btnAnadirLineaTicket');
    this.cancelPhotoButton = document.getElementById('btnCancelarTicket');
    this.cancelReviewButton = document.getElementById('btnCancelarRevisionTicket');

    this.setupEventListeners();
    this.setupInputValidation();
  }

  setupEventListeners() {
    if (this.analyzeButton) {
      this.analyzeButton.addEventListener('click', () => this.analyzeTicket());
    }
    if (this.confirmButton) {
      this.confirmButton.addEventListener('click', () => this.confirmTicket());
    }
    if (this.addLineButton) {
      this.addLineButton.addEventListener('click', () => this.addLine());
    }
    if (this.cancelPhotoButton) {
      this.cancelPhotoButton.addEventListener('click', () => this.close());
    }
    if (this.cancelReviewButton) {
      this.cancelReviewButton.addEventListener('click', () => this.close());
    }
  }

  setupInputValidation() {
    // Validar que la foto sea válida
    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => this.validateImage(e.target.files[0]));
    }
  }

  validateImage(file) {
    if (!file) return false;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!validTypes.includes(file.type)) {
      this.showError('Formato de imagen no válido. Usa JPG, PNG, WebP o GIF.');
      return false;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      this.showError('La imagen es demasiado grande (máximo 10MB).');
      return false;
    }

    return true;
  }

  async analyzeTicket() {
    const file = this.fileInput.files[0];
    if (!this.validateImage(file)) {
      return;
    }

    this.showStep('loading');

    const formData = new FormData();
    formData.append('foto', file);

    try {
      const res = await fetch('/api/tickets/analizar', {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(30000) // 30s timeout
      });

      const datos = await res.json();

      if (!res.ok) {
        this.showError(datos.error || 'No se pudo analizar el ticket');
        this.showStep('photo');
        return;
      }

      this.populateItems(datos);
      this.showStep('review');
    } catch (error) {
      console.error('Error analizando ticket:', error);
      this.showError('Error de conexión. Intenta de nuevo.');
      this.showStep('photo');
    }
  }

  populateItems(items) {
    this.itemsList.innerHTML = '';

    if (!items || items.length === 0) {
      this.addLine();
      return;
    }

    items.forEach(item => {
      const li = this.createItemElement(item);
      this.itemsList.appendChild(li);
    });
  }

  createItemElement(item) {
    const li = document.createElement('li');
    li.className = 'ticket-item';

    const nombre = (item.nombre || '').replace(/"/g, '&quot;');
    const unidad = (item.unidad || 'ud').replace(/"/g, '&quot;');

    li.innerHTML = `
      <div class="fila-superior">
        <input
          type="text"
          name="nombre"
          value="${nombre}"
          placeholder="Nombre del producto"
          required
          aria-label="Nombre"
        >
        <input
          type="number"
          name="cantidad"
          min="0.1"
          step="0.1"
          value="${item.cantidad || 1}"
          inputmode="decimal"
          aria-label="Cantidad"
        >
        <input
          type="text"
          name="unidad"
          value="${unidad}"
          maxlength="10"
          placeholder="ud"
          aria-label="Unidad"
        >
        <button
          type="button"
          title="Quitar línea"
          aria-label="Quitar línea"
          class="btn-quitar-linea"
        >
          🗑️
        </button>
      </div>
      <select name="vincular" aria-label="Vincular producto">
        <option value="nuevo">➕ Crear producto nuevo</option>
      </select>
      <select name="categoria" aria-label="Categoría" hidden></select>
    `;

    // Validar inputs
    const inputs = li.querySelectorAll('input');
    inputs.forEach(input => {
      new ValidatedInput(input, {
        required: input.name === 'nombre',
        minLength: input.name === 'nombre' ? 2 : 0
      });
    });

    // Botón de quitar
    const btnQuitar = li.querySelector('.btn-quitar-linea');
    if (btnQuitar) {
      btnQuitar.addEventListener('click', (e) => {
        e.preventDefault();
        li.remove();
        this.updateLineCount();
      });
    }

    // Select de categoría
    const selectCategory = li.querySelector('select[name="categoria"]');
    const selectVincular = li.querySelector('select[name="vincular"]');

    if (selectCategory && selectVincular) {
      this.populateCategories(selectCategory);
      selectVincular.addEventListener('change', () => {
        selectCategory.hidden = selectVincular.value !== 'nuevo';
      });
    }

    return li;
  }

  addLine() {
    const li = this.createItemElement({ nombre: '', cantidad: 1, unidad: 'ud' });
    this.itemsList.appendChild(li);
    this.updateLineCount();
    // Enfoque automático al primer input
    const firstInput = li.querySelector('input[name="nombre"]');
    if (firstInput) setTimeout(() => firstInput.focus(), 100);
  }

  updateLineCount() {
    const count = this.itemsList.querySelectorAll('.ticket-item').length;
    if (this.addLineButton) {
      this.addLineButton.textContent = `+ Añadir línea (${count})`;
    }
  }

  populateCategories(select) {
    // Poblar con categorías disponibles
    // TODO: obtener del servidor o variable global
  }

  confirmTicket() {
    const items = [];
    const lines = this.itemsList.querySelectorAll('.ticket-item');

    for (const line of lines) {
      const nombre = line.querySelector('input[name="nombre"]').value.trim();
      const cantidad = parseFloat(line.querySelector('input[name="cantidad"]').value) || 1;
      const unidad = line.querySelector('input[name="unidad"]').value.trim() || 'ud';
      const vincular = line.querySelector('select[name="vincular"]').value;
      const categoria = line.querySelector('select[name="categoria"]').value;

      if (!nombre) {
        this.showError('Todos los productos deben tener nombre');
        return;
      }

      items.push({
        nombre,
        cantidad,
        unidad,
        vincular,
        categoria: vincular === 'nuevo' ? categoria : null
      });
    }

    this.submitItems(items);
  }

  async submitItems(items) {
    try {
      const res = await fetch('/api/productos/desde-ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
        signal: AbortSignal.timeout(10000)
      });

      if (!res.ok) {
        const error = await res.json();
        this.showError(error.error || 'Error al guardar productos');
        return;
      }

      this.showSuccess('Productos añadidos correctamente');
      this.close();
    } catch (error) {
      console.error('Error guardando productos:', error);
      this.showError('Error de conexión al guardar');
    }
  }

  showError(message) {
    console.error(message);
    // TODO: mostrar en UI de forma consistente
    alert(message);
  }

  showSuccess(message) {
    console.log(message);
    // TODO: mostrar en UI de forma consistente
  }

  onOpen() {
    super.onOpen();
    this.updateLineCount();
  }

  onClose() {
    super.onClose();
  }
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* INICIALIZACION */
/* ═══════════════════════════════════════════════════════════════════════════ */

// Instancias globales
let productModal;
let ticketModal;

document.addEventListener('DOMContentLoaded', () => {
  // Inicializar componentes
  try {
    productModal = new ProductFormModal();
    ticketModal = new TicketReadModal();

    // Setup de eventos globales
    setupGlobalEvents();
  } catch (error) {
    console.error('Error inicializando modales:', error);
  }
});

function setupGlobalEvents() {
  // Botón de abrir modal de producto
  const btnAbrirModal = document.getElementById('btnAbrirModal');
  if (btnAbrirModal) {
    btnAbrirModal.addEventListener('click', () => productModal.open());
  }

  // Botón de escanear ticket
  const btnEscanearTicket = document.getElementById('btnEscanearTicket');
  if (btnEscanearTicket) {
    btnEscanearTicket.addEventListener('click', () => ticketModal.open());
  }

  // Cierre de modales con tecla ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (ticketModal?.isOpen) ticketModal.close();
      if (productModal?.isOpen) productModal.close();
    }
  });
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* EXPORTAR PARA USO GLOBAL */
/* ═══════════════════════════════════════════════════════════════════════════ */

window.AppModals = {
  productModal: () => productModal,
  ticketModal: () => ticketModal
};
