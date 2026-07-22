/**
 * UI COMPONENTS - Sistema profesional de componentes reutilizables
 * Arquitectura OOP para garantizar consistencia visual y funcional
 */

/** Base para todos los modales */
class ModalBase {
  constructor(elementId) {
    this.element = document.getElementById(elementId);
    if (!this.element) throw new Error(`Modal no encontrado: ${elementId}`);
    this.isOpen = false;
  }

  init() {
    // Método para sobrescribir en subclases
  }

  open() {
    this.element.hidden = false;
    document.body.classList.add('modal-open');
    this.isOpen = true;
    this.onOpen();
  }

  close() {
    this.element.hidden = true;
    document.body.classList.remove('modal-open');
    this.isOpen = false;
    this.onClose();
  }

  onOpen() {
    // Hook para sobrescribir
  }

  onClose() {
    // Hook para sobrescribir
  }

  /* Asegura que el modal se adapte al teclado */
  handleKeyboard() {
    if (this.element.querySelector('input[type="text"], input[type="number"], select, textarea')) {
      document.body.classList.add('is-keyboard-open');
    }
  }

  unhideKeyboard() {
    document.body.classList.remove('is-keyboard-open');
  }
}

/** Modal de formulario (producto, categoría, etc.) */
class FormModal extends ModalBase {
  constructor(elementId, formId) {
    super(elementId);
    this.formId = formId;
    this.form = document.getElementById(formId);
    if (!this.form) throw new Error(`Formulario no encontrado: ${formId}`);
    this.setupFormListeners();
    this.init();
  }

  init() {
    // Hook para sobrescribir en subclases
  }

  setupFormListeners() {
    if (!this.form) return;
    // Prevenir que se abra el teclado innecesariamente
    const inputs = this.form.querySelectorAll('input, select, textarea');
    if (inputs && inputs.length > 0) {
      inputs.forEach(input => {
        input.addEventListener('focus', () => this.handleKeyboard());
        input.addEventListener('blur', () => this.unhideKeyboard());
      });
    }
  }

  resetForm() {
    this.form.reset();
    this.form.querySelector('input[type="hidden"][id$="Id"]')?.setAttribute('value', '');
  }

  onOpen() {
    this.resetForm();
    // Enfoca el primer input
    const firstInput = this.form.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }
  }

  onClose() {
    this.resetForm();
  }
}

/** Modal de lectura de tickets */
class TicketModal extends ModalBase {
  constructor(elementId) {
    super(elementId);
    this.fileInput = document.getElementById('ticketArchivo');
    this.stepPhoto = document.getElementById('ticketPasoFoto');
    this.stepLoading = document.getElementById('ticketCargando');
    this.stepReview = document.getElementById('ticketPasoRevision');
    this.itemsList = document.getElementById('ticketItems');
    this.currentStep = 'photo';
    this.init();
  }

  init() {
    // Validar elementos necesarios
    if (!this.fileInput || !this.stepPhoto || !this.stepLoading || !this.stepReview) {
      throw new Error('Elementos del modal de ticket incompletos');
    }
  }

  resetModal() {
    this.fileInput.value = '';
    this.showStep('photo');
    this.itemsList.innerHTML = '';
  }

  showStep(step) {
    this.currentStep = step;
    this.stepPhoto.hidden = step !== 'photo';
    this.stepLoading.hidden = step !== 'loading';
    this.stepReview.hidden = step !== 'review';

    // Forzar reflow para adaptar altura
    this.element.style.maxHeight = this.getMaxHeight();
  }

  /** Calcula altura máxima considerando teclado */
  getMaxHeight() {
    const keyboardHeight = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--keyboard-height') || '0');
    const padding = 32; // padding top + bottom
    return `calc(100dvh - ${keyboardHeight}px - ${padding}px)`;
  }

  onOpen() {
    this.resetModal();
  }

  onClose() {
    this.resetModal();
  }
}

/** Modal de catálogo para búsqueda */
class CatalogModal extends ModalBase {
  constructor(elementId) {
    super(elementId);
    this.searchInput = this.element.querySelector('input[type="search"]');
    this.scroll = this.element.querySelector('.catalogo-scroll');
  }

  init() {
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => this.onSearch(e.target.value));
    }
  }

  onSearch(query) {
    // Método para sobrescribir
  }

  /* Mantiene scroll dentro del viewport */
  ensureScroll() {
    if (this.scroll) {
      this.scroll.style.maxHeight = `calc(${this.getMaxHeight()} - 100px)`;
    }
  }

  getMaxHeight() {
    const keyboardHeight = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--keyboard-height') || '0');
    return `calc(100dvh - ${keyboardHeight}px)`;
  }

  onOpen() {
    this.ensureScroll();
    if (this.searchInput) {
      setTimeout(() => this.searchInput.focus(), 100);
    }
  }
}

/** Componente de lista responsive */
class ResponsiveList {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) throw new Error(`Contenedor no encontrado: ${containerId}`);
    this.items = [];
  }

  addItem(item) {
    this.items.push(item);
    this.render();
  }

  removeItem(index) {
    this.items.splice(index, 1);
    this.render();
  }

  clear() {
    this.items = [];
    this.render();
  }

  render() {
    this.container.innerHTML = '';
    this.items.forEach((item, index) => {
      const el = this.createItemElement(item, index);
      this.container.appendChild(el);
    });
    this.onRender();
  }

  createItemElement(item, index) {
    // Método para sobrescribir
    const div = document.createElement('div');
    div.textContent = JSON.stringify(item);
    return div;
  }

  onRender() {
    // Hook para sobrescribir
  }
}

/** Input con validación y feedback */
class ValidatedInput {
  constructor(inputElement, rules = {}) {
    this.input = inputElement;
    this.rules = rules;
    this.isValid = true;
    this.init();
  }

  init() {
    this.input.addEventListener('blur', () => this.validate());
    this.input.addEventListener('input', () => this.clearError());
  }

  validate() {
    this.isValid = true;

    if (this.rules.required && !this.input.value.trim()) {
      this.setError((window.i18n && window.i18n.t('este_campo_es_requerido')) || 'Este campo es requerido');
      this.isValid = false;
      return;
    }

    if (this.rules.minLength && this.input.value.length < this.rules.minLength) {
      const plantillaMin = (window.i18n && window.i18n.t('minimo_n_caracteres')) || 'Mínimo {n} caracteres';
      this.setError(plantillaMin.replace('{n}', this.rules.minLength));
      this.isValid = false;
      return;
    }

    if (this.rules.maxLength && this.input.value.length > this.rules.maxLength) {
      const plantillaMax = (window.i18n && window.i18n.t('maximo_n_caracteres')) || 'Máximo {n} caracteres';
      this.setError(plantillaMax.replace('{n}', this.rules.maxLength));
      this.isValid = false;
      return;
    }

    if (this.rules.pattern && !this.rules.pattern.test(this.input.value)) {
      this.setError(this.rules.errorMessage || (window.i18n && window.i18n.t('formato_invalido')) || 'Formato inválido');
      this.isValid = false;
      return;
    }

    this.clearError();
    return this.isValid;
  }

  setError(message) {
    this.input.setAttribute('aria-invalid', 'true');
    this.input.title = message;
    this.input.classList.add('error');
  }

  clearError() {
    this.input.removeAttribute('aria-invalid');
    this.input.classList.remove('error');
  }

  getValue() {
    return this.input.value;
  }

  setValue(value) {
    this.input.value = value;
  }
}

/** Gestor de teclado virtual */
class KeyboardManager {
  constructor() {
    this.isOpen = false;
    this.height = 0;
    this.init();
  }

  init() {
    // No engancha sus propios listeners de visualViewport/focus: app.js
    // (ajustarViewportMovil) es la única fuente de verdad para el alto de
    // teclado y ya escribe --keyboard-height e is-keyboard-open. Dos
    // trackers independientes (éste usaba un umbral y cálculo distintos)
    // podían desincronizarse y dar una altura de modal incorrecta.
  }

  getHeight() {
    return this.height;
  }
}

/** Gestor de tema (claro/oscuro). No se instancia globalmente: app.js
 * (guardarTemaPreferido/temaActual) es la única fuente de verdad para el
 * tema, ya que resuelve "auto" contra prefers-color-scheme y lo persiste
 * en BD por usuario. Instanciar este manager en paralelo pisaba
 * document.documentElement.dataset.theme con el valor crudo de
 * localStorage (p.ej. "auto" sin resolver), rompiendo el tema del sistema.
 * Se mantiene la clase exportada solo por compatibilidad con sus tests. */
class ThemeManager {
  constructor(buttonId = 'btnTema') {
    this.button = document.getElementById(buttonId);
    this.currentTheme = localStorage.getItem('stockhogar-tema') || 'light';
    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    if (this.button) {
      this.button.addEventListener('click', () => this.toggle());
    }
  }

  toggle() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.applyTheme(newTheme);
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('stockhogar-tema', theme);
    if (this.button) {
      this.button.textContent = theme === 'light' ? '☀️' : '🌙';
    }
  }

  getTheme() {
    return this.currentTheme;
  }
}

/** Utilidades de pantalla */
class ScreenUtils {
  static isMobile() {
    return window.innerWidth < 768;
  }

  static isTablet() {
    return window.innerWidth >= 768 && window.innerWidth < 1024;
  }

  static isDesktop() {
    return window.innerWidth >= 1024;
  }

  static getViewportHeight() {
    return Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
  }

  static getAvailableHeight() {
    const keyboardHeight = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--keyboard-height') || '0');
    return this.getViewportHeight() - keyboardHeight;
  }

  static onResize(callback) {
    window.addEventListener('resize', () => {
      callback({
        width: window.innerWidth,
        height: this.getViewportHeight(),
        availableHeight: this.getAvailableHeight(),
        isMobile: this.isMobile(),
        isTablet: this.isTablet(),
        isDesktop: this.isDesktop()
      });
    });
  }
}

/** Notificaciones no bloqueantes (sustituye a alert()) */
class ToastManager {
  constructor() {
    this.container = null;
    this.init();
  }

  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    this.container.setAttribute('role', 'status');
    this.container.setAttribute('aria-live', 'polite');
    document.body.appendChild(this.container);
  }

  show(mensaje, { type = 'info', duration = 5000 } = {}) {
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const texto = document.createElement('span');
    texto.className = 'toast__mensaje';
    texto.textContent = mensaje;
    toast.appendChild(texto);

    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'toast__cerrar';
    cerrar.setAttribute('aria-label', (window.i18n && window.i18n.t('cerrar_notificacion')) || 'Cerrar notificación');
    cerrar.textContent = '×';
    const quitar = () => {
      toast.classList.add('toast--saliendo');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    };
    cerrar.addEventListener('click', quitar);
    toast.appendChild(cerrar);

    this.container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast--visible'));

    if (duration > 0) {
      setTimeout(quitar, duration);
    }
    return toast;
  }

  error(mensaje, opciones = {}) {
    return this.show(mensaje, { duration: 7000, ...opciones, type: 'error' });
  }

  success(mensaje, opciones = {}) {
    return this.show(mensaje, { ...opciones, type: 'success' });
  }

  info(mensaje, opciones = {}) {
    return this.show(mensaje, { ...opciones, type: 'info' });
  }
}

// Inicializar managers globales (solo en navegador: en tests se usa require(),
// que envuelve el fichero como módulo CommonJS y por tanto define `module`).
if (typeof module === 'undefined') {
  const keyboardManager = new KeyboardManager();
  const toastManager = new ToastManager();

  window.UIComponents = {
    ModalBase,
    FormModal,
    TicketModal,
    CatalogModal,
    ResponsiveList,
    ValidatedInput,
    KeyboardManager,
    ThemeManager,
    ScreenUtils,
    ToastManager
  };
  window.Toast = toastManager;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ModalBase,
    FormModal,
    TicketModal,
    CatalogModal,
    ResponsiveList,
    ValidatedInput,
    KeyboardManager,
    ThemeManager,
    ScreenUtils,
    ToastManager
  };
}
