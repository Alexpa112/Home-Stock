/**
 * Tests para UI Components (ModalBase, FormModal, TicketModal, CatalogModal,
 * ResponsiveList, ValidatedInput, KeyboardManager, ThemeManager, ScreenUtils,
 * ToastManager)
 */
const {
  ModalBase,
  FormModal,
  TicketModal,
  CatalogModal,
  ResponsiveList,
  ValidatedInput,
  KeyboardManager,
  ThemeManager,
  ScreenUtils,
  ToastManager,
} = require('./ui-components.js');

function setInnerWidth(width) {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: width });
}

afterEach(() => {
  document.body.innerHTML = '';
  document.documentElement.removeAttribute('style');
  localStorage.clear();
});

describe('ModalBase', () => {
  test('lanza error si el elemento no existe', () => {
    expect(() => new ModalBase('noexiste')).toThrow('Modal no encontrado: noexiste');
  });

  test('open() muestra el modal y marca isOpen', () => {
    document.body.innerHTML = '<div id="m1" hidden></div>';
    const modal = new ModalBase('m1');

    modal.open();

    expect(modal.element.hidden).toBe(false);
    expect(modal.isOpen).toBe(true);
    expect(document.body.classList.contains('modal-open')).toBe(true);
  });

  test('close() oculta el modal y desmarca isOpen', () => {
    document.body.innerHTML = '<div id="m1"></div>';
    const modal = new ModalBase('m1');

    modal.open();
    modal.close();

    expect(modal.element.hidden).toBe(true);
    expect(modal.isOpen).toBe(false);
    expect(document.body.classList.contains('modal-open')).toBe(false);
  });

  test('open()/close() llaman a los hooks onOpen/onClose', () => {
    document.body.innerHTML = '<div id="m1"></div>';
    const modal = new ModalBase('m1');
    modal.onOpen = jest.fn();
    modal.onClose = jest.fn();

    modal.open();
    modal.close();

    expect(modal.onOpen).toHaveBeenCalledTimes(1);
    expect(modal.onClose).toHaveBeenCalledTimes(1);
  });

  test('handleKeyboard() añade la clase solo si hay campos editables', () => {
    document.body.innerHTML = '<div id="m1"><input type="text"></div>';
    const modal = new ModalBase('m1');

    modal.handleKeyboard();

    expect(document.body.classList.contains('is-keyboard-open')).toBe(true);
  });

  test('unhideKeyboard() quita la clase', () => {
    document.body.innerHTML = '<div id="m1"></div>';
    const modal = new ModalBase('m1');
    document.body.classList.add('is-keyboard-open');

    modal.unhideKeyboard();

    expect(document.body.classList.contains('is-keyboard-open')).toBe(false);
  });
});

describe('FormModal', () => {
  function montarModalConFormulario() {
    document.body.innerHTML = `
      <div id="modal">
        <form id="form">
          <input type="hidden" id="productoId" value="5">
          <input type="text" name="nombre">
        </form>
      </div>`;
  }

  test('lanza error si el formulario no existe', () => {
    document.body.innerHTML = '<div id="modal"></div>';
    expect(() => new FormModal('modal', 'noexiste')).toThrow('Formulario no encontrado: noexiste');
  });

  test('resetForm() limpia el formulario y el id oculto', () => {
    montarModalConFormulario();
    const fm = new FormModal('modal', 'form');
    fm.form.querySelector('input[name="nombre"]').value = 'algo';

    fm.resetForm();

    expect(fm.form.querySelector('input[name="nombre"]').value).toBe('');
    expect(fm.form.querySelector('#productoId').getAttribute('value')).toBe('');
  });

  test('onOpen() resetea el formulario y enfoca el primer input visible', () => {
    jest.useFakeTimers();
    montarModalConFormulario();
    const fm = new FormModal('modal', 'form');
    const primerInput = fm.form.querySelector('input[name="nombre"]');
    const focusSpy = jest.spyOn(primerInput, 'focus');

    fm.onOpen();
    jest.advanceTimersByTime(100);

    expect(focusSpy).toHaveBeenCalled();
    jest.useRealTimers();
  });

  test('focus en un campo activa el modo teclado, blur lo desactiva', () => {
    montarModalConFormulario();
    const fm = new FormModal('modal', 'form');
    const input = fm.form.querySelector('input[name="nombre"]');

    input.dispatchEvent(new Event('focus'));
    expect(document.body.classList.contains('is-keyboard-open')).toBe(true);

    input.dispatchEvent(new Event('blur'));
    expect(document.body.classList.contains('is-keyboard-open')).toBe(false);
  });
});

describe('TicketModal', () => {
  function montarTicketModal() {
    document.body.innerHTML = `
      <div id="modalTicket">
        <input type="file" id="ticketArchivo">
        <div id="ticketPasoFoto"></div>
        <div id="ticketCargando"></div>
        <div id="ticketPasoRevision"></div>
        <ul id="ticketItems"><li>viejo</li></ul>
      </div>`;
  }

  test('lanza error si faltan elementos del flujo', () => {
    document.body.innerHTML = '<div id="modalTicket"></div>';
    expect(() => new TicketModal('modalTicket')).toThrow('Elementos del modal de ticket incompletos');
  });

  test('showStep() muestra solo el paso indicado', () => {
    montarTicketModal();
    const tm = new TicketModal('modalTicket');

    tm.showStep('loading');

    expect(tm.stepPhoto.hidden).toBe(true);
    expect(tm.stepLoading.hidden).toBe(false);
    expect(tm.stepReview.hidden).toBe(true);
    expect(tm.currentStep).toBe('loading');
  });

  test('resetModal() vacía el input de archivo, la lista y vuelve al paso foto', () => {
    montarTicketModal();
    const tm = new TicketModal('modalTicket');
    tm.showStep('review');

    tm.resetModal();

    expect(tm.fileInput.value).toBe('');
    expect(tm.itemsList.innerHTML).toBe('');
    expect(tm.currentStep).toBe('photo');
    expect(tm.stepPhoto.hidden).toBe(false);
  });

  test('onOpen() y onClose() reinician el modal', () => {
    montarTicketModal();
    const tm = new TicketModal('modalTicket');
    tm.itemsList.innerHTML = '<li>algo</li>';

    tm.onOpen();
    expect(tm.itemsList.innerHTML).toBe('');

    tm.itemsList.innerHTML = '<li>algo</li>';
    tm.onClose();
    expect(tm.itemsList.innerHTML).toBe('');
  });
});

describe('CatalogModal', () => {
  function montarCatalogModal() {
    document.body.innerHTML = `
      <div id="modalCatalogo">
        <input type="search">
        <div class="catalogo-scroll"></div>
      </div>`;
  }

  test('onSearch() se invoca al escribir en el buscador', () => {
    montarCatalogModal();
    const cm = new CatalogModal('modalCatalogo');
    cm.onSearch = jest.fn();
    cm.init();

    cm.searchInput.value = 'leche';
    cm.searchInput.dispatchEvent(new Event('input'));

    expect(cm.onSearch).toHaveBeenCalledWith('leche');
  });

  test('no falla si no hay buscador ni contenedor de scroll', () => {
    document.body.innerHTML = '<div id="modalCatalogo"></div>';
    const cm = new CatalogModal('modalCatalogo');

    expect(() => cm.init()).not.toThrow();
    expect(() => cm.ensureScroll()).not.toThrow();
  });

  test('onOpen() enfoca el buscador si existe', () => {
    jest.useFakeTimers();
    montarCatalogModal();
    const cm = new CatalogModal('modalCatalogo');
    const focusSpy = jest.spyOn(cm.searchInput, 'focus');

    cm.onOpen();
    jest.advanceTimersByTime(100);

    expect(focusSpy).toHaveBeenCalled();
    jest.useRealTimers();
  });
});

describe('ResponsiveList', () => {
  test('lanza error si el contenedor no existe', () => {
    expect(() => new ResponsiveList('noexiste')).toThrow('Contenedor no encontrado: noexiste');
  });

  test('addItem() añade el elemento y renderiza', () => {
    document.body.innerHTML = '<div id="lista"></div>';
    const list = new ResponsiveList('lista');

    list.addItem({ nombre: 'Leche' });

    expect(list.items).toHaveLength(1);
    expect(list.container.children).toHaveLength(1);
    expect(list.container.textContent).toContain('Leche');
  });

  test('removeItem() quita el elemento por índice', () => {
    document.body.innerHTML = '<div id="lista"></div>';
    const list = new ResponsiveList('lista');
    list.addItem({ nombre: 'Leche' });
    list.addItem({ nombre: 'Pan' });

    list.removeItem(0);

    expect(list.items).toHaveLength(1);
    expect(list.items[0].nombre).toBe('Pan');
  });

  test('clear() vacía la lista', () => {
    document.body.innerHTML = '<div id="lista"></div>';
    const list = new ResponsiveList('lista');
    list.addItem({ nombre: 'Leche' });

    list.clear();

    expect(list.items).toHaveLength(0);
    expect(list.container.children).toHaveLength(0);
  });

  test('render() llama a onRender()', () => {
    document.body.innerHTML = '<div id="lista"></div>';
    const list = new ResponsiveList('lista');
    list.onRender = jest.fn();

    list.render();

    expect(list.onRender).toHaveBeenCalled();
  });
});

describe('ValidatedInput', () => {
  function crearInput() {
    const input = document.createElement('input');
    document.body.appendChild(input);
    return input;
  }

  test('required: marca error si está vacío', () => {
    const input = crearInput();
    const vi = new ValidatedInput(input, { required: true });

    vi.validate();

    expect(vi.isValid).toBe(false);
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.title).toBe('Este campo es requerido');
  });

  test('minLength: marca error si es más corto de lo permitido', () => {
    const input = crearInput();
    input.value = 'ab';
    const vi = new ValidatedInput(input, { minLength: 3 });

    vi.validate();

    expect(vi.isValid).toBe(false);
    expect(input.title).toBe('Mínimo 3 caracteres');
  });

  test('maxLength: marca error si es más largo de lo permitido', () => {
    const input = crearInput();
    input.value = 'demasiado largo';
    const vi = new ValidatedInput(input, { maxLength: 5 });

    vi.validate();

    expect(vi.isValid).toBe(false);
    expect(input.title).toBe('Máximo 5 caracteres');
  });

  test('pattern: usa el mensaje de error personalizado', () => {
    const input = crearInput();
    input.value = 'abc';
    const vi = new ValidatedInput(input, { pattern: /^\d+$/, errorMessage: 'Solo números' });

    vi.validate();

    expect(vi.isValid).toBe(false);
    expect(input.title).toBe('Solo números');
  });

  test('valor válido limpia el error', () => {
    const input = crearInput();
    input.value = 'ok';
    const vi = new ValidatedInput(input, { required: true });
    vi.setError('previo');

    vi.validate();

    expect(vi.isValid).toBe(true);
    expect(input.hasAttribute('aria-invalid')).toBe(false);
  });

  test('validate() se dispara automáticamente al perder el foco', () => {
    const input = crearInput();
    const vi = new ValidatedInput(input, { required: true });
    const spy = jest.spyOn(vi, 'validate');

    input.dispatchEvent(new Event('blur'));

    expect(spy).toHaveBeenCalled();
  });

  test('clearError() se dispara automáticamente al escribir', () => {
    const input = crearInput();
    const vi = new ValidatedInput(input, {});
    const spy = jest.spyOn(vi, 'clearError');

    input.dispatchEvent(new Event('input'));

    expect(spy).toHaveBeenCalled();
  });

  test('getValue()/setValue() leen y escriben el input', () => {
    const input = crearInput();
    const vi = new ValidatedInput(input, {});

    vi.setValue('nuevo valor');

    expect(vi.getValue()).toBe('nuevo valor');
    expect(input.value).toBe('nuevo valor');
  });
});

describe('KeyboardManager', () => {
  test('empieza cerrado y con altura 0', () => {
    const km = new KeyboardManager();

    expect(km.isOpen).toBe(false);
    expect(km.getHeight()).toBe(0);
  });
});

describe('ThemeManager', () => {
  test('usa "light" por defecto si no hay tema guardado', () => {
    const tm = new ThemeManager('noexiste');

    expect(tm.getTheme()).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });

  test('respeta el tema guardado en localStorage', () => {
    localStorage.setItem('stockhogar-tema', 'dark');

    const tm = new ThemeManager('noexiste');

    expect(tm.getTheme()).toBe('dark');
  });

  test('toggle() alterna entre light y dark y lo persiste', () => {
    const tm = new ThemeManager('noexiste');

    tm.toggle();
    expect(tm.getTheme()).toBe('dark');
    expect(localStorage.getItem('stockhogar-tema')).toBe('dark');

    tm.toggle();
    expect(tm.getTheme()).toBe('light');
  });

  test('actualiza el icono del botón si existe', () => {
    document.body.innerHTML = '<button id="btnTema"></button>';
    const tm = new ThemeManager('btnTema');

    expect(tm.button.textContent).toBe('☀️');

    tm.toggle();
    expect(tm.button.textContent).toBe('🌙');
  });

  test('un click en el botón alterna el tema', () => {
    document.body.innerHTML = '<button id="btnTema"></button>';
    const tm = new ThemeManager('btnTema');

    tm.button.click();

    expect(tm.getTheme()).toBe('dark');
  });

  test('no falla si el botón no existe', () => {
    expect(() => new ThemeManager('noexiste').toggle()).not.toThrow();
  });
});

describe('ScreenUtils', () => {
  test('isMobile()/isTablet()/isDesktop() clasifican según el ancho', () => {
    setInnerWidth(500);
    expect(ScreenUtils.isMobile()).toBe(true);
    expect(ScreenUtils.isTablet()).toBe(false);
    expect(ScreenUtils.isDesktop()).toBe(false);

    setInnerWidth(800);
    expect(ScreenUtils.isMobile()).toBe(false);
    expect(ScreenUtils.isTablet()).toBe(true);

    setInnerWidth(1200);
    expect(ScreenUtils.isDesktop()).toBe(true);
  });

  test('onResize() invoca el callback con la info de pantalla', () => {
    setInnerWidth(500);
    const callback = jest.fn();
    ScreenUtils.onResize(callback);

    window.dispatchEvent(new Event('resize'));

    expect(callback).toHaveBeenCalledWith(expect.objectContaining({
      width: 500,
      isMobile: true,
    }));
  });
});

describe('ToastManager', () => {
  test('el constructor crea el contenedor accesible en el body', () => {
    const tm = new ToastManager();

    expect(tm.container.parentElement).toBe(document.body);
    expect(tm.container.getAttribute('role')).toBe('status');
    expect(tm.container.getAttribute('aria-live')).toBe('polite');
  });

  test('show() añade un toast con el mensaje', () => {
    const tm = new ToastManager();

    const toast = tm.show('Hola mundo');

    expect(toast.textContent).toContain('Hola mundo');
    expect(tm.container.contains(toast)).toBe(true);
  });

  test('error() usa role="alert" y clase toast--error', () => {
    const tm = new ToastManager();

    const toast = tm.error('Algo falló');

    expect(toast.classList.contains('toast--error')).toBe(true);
    expect(toast.getAttribute('role')).toBe('alert');
  });

  test('success() e info() usan sus clases respectivas', () => {
    const tm = new ToastManager();

    expect(tm.success('ok').classList.contains('toast--success')).toBe(true);
    expect(tm.info('fyi').classList.contains('toast--info')).toBe(true);
  });

  test('el botón de cerrar quita el toast al terminar la transición', () => {
    const tm = new ToastManager();
    const toast = tm.show('Cerrable', { duration: 0 });
    const btnCerrar = toast.querySelector('.toast__cerrar');

    btnCerrar.click();
    toast.dispatchEvent(new Event('transitionend'));

    expect(tm.container.contains(toast)).toBe(false);
  });
});
