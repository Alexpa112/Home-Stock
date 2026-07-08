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
      this.setError('Este campo es requerido');
      this.isValid = false;
      return;
    }

    if (this.rules.minLength && this.input.value.length < this.rules.minLength) {
      this.setError(`Mínimo ${this.rules.minLength} caracteres`);
      this.isValid = false;
      return;
    }

    if (this.rules.maxLength && this.input.value.length > this.rules.maxLength) {
      this.setError(`Máximo ${this.rules.maxLength} caracteres`);
      this.isValid = false;
      return;
    }

    if (this.rules.pattern && !this.rules.pattern.test(this.input.value)) {
      this.setError(this.rules.errorMessage || 'Formato inválido');
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
    // Detectar teclado iOS
    window.visualViewport?.addEventListener('resize', () => this.updateKeyboardHeight());

    // Detectar teclado Android
    window.addEventListener('focusin', () => this.handleFocusIn());
    window.addEventListener('focusout', () => this.handleFocusOut());
  }

  updateKeyboardHeight() {
    const viewport = window.visualViewport;
    if (!viewport) return;

    const windowHeight = window.innerHeight;
    const viewportHeight = viewport.height;
    const newHeight = Math.max(0, windowHeight - viewportHeight);

    if (newHeight > 50) {
      this.height = newHeight;
      this.isOpen = true;
    } else {
      this.height = 0;
      this.isOpen = false;
    }

    this.updateCSS();
  }

  handleFocusIn() {
    document.body.classList.add('is-keyboard-open');
  }

  handleFocusOut() {
    setTimeout(() => {
      const activeEl = document.activeElement;
      if (!this.isInputElement(activeEl)) {
        document.body.classList.remove('is-keyboard-open');
      }
    }, 100);
  }

  isInputElement(el) {
    return el && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName);
  }

  updateCSS() {
    document.documentElement.style.setProperty('--keyboard-height', `${this.height}px`);
  }

  getHeight() {
    return this.height;
  }
}

/** Gestor de tema (claro/oscuro) */
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

// Inicializar managers globales
const keyboardManager = new KeyboardManager();
const themeManager = new ThemeManager();

// Exponer globalmente
window.UIComponents = {
  ModalBase,
  FormModal,
  TicketModal,
  CatalogModal,
  ResponsiveList,
  ValidatedInput,
  KeyboardManager,
  ThemeManager,
  ScreenUtils
};
