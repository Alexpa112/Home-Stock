/**
 * Tests para el teclado virtual propio (fase 1: solo layout numérico)
 */
const {
  VirtualKeyboardDetector,
  VirtualKeyboardLayout,
  VirtualKeyboardController,
} = require('./virtual-keyboard.js');

function mockMatchMedia(reglas) {
  window.matchMedia = jest.fn((query) => ({
    matches: !!reglas[query],
    media: query,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }));
}

afterEach(() => {
  document.body.innerHTML = '';
  document.documentElement.removeAttribute('style');
  document.body.className = '';
  delete document.body.dataset.tecladoVirtualActivo;
  delete window.__a11y_tabDetectado;
  delete window.__teclado_fisico_detectado;
  sessionStorage.clear();
  localStorage.clear();
  jest.restoreAllMocks();
});

describe('VirtualKeyboardDetector.isTouchOnly()', () => {
  test('true cuando hay puntero grueso, sin hover y sin puntero fino', () => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
    expect(VirtualKeyboardDetector.isTouchOnly()).toBe(true);
  });

  test('false si hay un puntero fino disponible (mouse/trackpad conectado)', () => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': true,
    });
    expect(VirtualKeyboardDetector.isTouchOnly()).toBe(false);
  });

  test('false en desktop (puntero fino, con hover)', () => {
    mockMatchMedia({
      '(pointer: coarse)': false,
      '(hover: none)': false,
      '(any-pointer: fine)': true,
    });
    expect(VirtualKeyboardDetector.isTouchOnly()).toBe(false);
  });
});

describe('VirtualKeyboardDetector.shouldUseCustomKeyboard()', () => {
  beforeEach(() => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
  });

  test('false si la preferencia de usuario está desactivada', () => {
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(false)).toBe(false);
  });

  test('false si se detectó navegación por Tab (heurística de lector de pantalla)', () => {
    window.__a11y_tabDetectado = true;
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(true)).toBe(false);
  });

  test('false si se detectó teclado físico real', () => {
    window.__teclado_fisico_detectado = true;
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(true)).toBe(false);
  });

  test('true cuando todo lo demás es favorable', () => {
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(true)).toBe(true);
  });
});

describe('VirtualKeyboardLayout.esInputNumerico()', () => {
  test('type="number" es numérico', () => {
    document.body.innerHTML = '<input type="number">';
    expect(VirtualKeyboardLayout.esInputNumerico(document.querySelector('input'))).toBe(true);
  });

  test('inputmode="numeric" es numérico aunque type sea text', () => {
    document.body.innerHTML = '<input type="text" inputmode="numeric">';
    expect(VirtualKeyboardLayout.esInputNumerico(document.querySelector('input'))).toBe(true);
  });

  test('type="text" sin inputmode numérico no es numérico', () => {
    document.body.innerHTML = '<input type="text">';
    expect(VirtualKeyboardLayout.esInputNumerico(document.querySelector('input'))).toBe(false);
  });

  test('type="email"/"password" no son numéricos', () => {
    document.body.innerHTML = '<input type="email"><input type="password">';
    document.querySelectorAll('input').forEach((el) => {
      expect(VirtualKeyboardLayout.esInputNumerico(el)).toBe(false);
    });
  });
});

describe('VirtualKeyboardController.attach()/detach() (panel)', () => {
  let controller;

  beforeEach(() => {
    document.body.innerHTML = '<input id="cantidad" type="number" value="1">';
    controller = new VirtualKeyboardController();
  });

  test('attach() marca inputmode="none" y readonly (red de seguridad si no se pasó por _sincronizarMarcado)', () => {
    const input = document.getElementById('cantidad');
    controller.attach(input);

    expect(input.getAttribute('inputmode')).toBe('none');
    expect(input.hasAttribute('readonly')).toBe(true);
  });

  test('attach() fija --keyboard-height/--keyboard-offset y body.keyboard-open', () => {
    const input = document.getElementById('cantidad');
    controller.attach(input);

    expect(document.body.classList.contains('keyboard-open')).toBe(true);
    expect(document.body.dataset.tecladoVirtualActivo).toBe('1');
    const alto = document.documentElement.style.getPropertyValue('--keyboard-height');
    expect(alto).not.toBe('');
    expect(document.documentElement.style.getPropertyValue('--keyboard-offset')).toBe(alto);
  });

  // Importante: detach() (invocado también al perder el foco) SOLO oculta
  // el panel, no retira inputmode="none"/readonly. Si lo hiciera en cada
  // cambio de foco, iOS volvería a mostrar su teclado nativo brevemente en
  // el siguiente toque, porque decide si mostrarlo en el instante en que
  // arranca el foco, antes de que un handler de focus pueda reaccionar.
  test('detach() oculta el panel y limpia clases/variables, pero NO retira inputmode/readonly', () => {
    const input = document.getElementById('cantidad');
    controller.attach(input);

    controller.detach();

    expect(input.getAttribute('inputmode')).toBe('none');
    expect(input.hasAttribute('readonly')).toBe(true);
    expect(controller.activeInput).toBeNull();
    expect(document.body.classList.contains('keyboard-open')).toBe(false);
    expect(document.body.classList.contains('is-keyboard-open')).toBe(false);
    expect(document.body.dataset.tecladoVirtualActivo).toBeUndefined();
    expect(document.documentElement.style.getPropertyValue('--keyboard-height')).toBe('0px');
  });
});

describe('VirtualKeyboardController: marcado proactivo (_sincronizarMarcado)', () => {
  beforeEach(() => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
  });

  test('init() marca de antemano los inputs numéricos ya presentes en el DOM (antes de cualquier foco)', () => {
    document.body.innerHTML = '<input id="cantidad" type="number" value="1"><input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();

    controller.init(true);

    const cantidad = document.getElementById('cantidad');
    const nombre = document.getElementById('nombre');
    expect(cantidad.getAttribute('inputmode')).toBe('none');
    expect(cantidad.hasAttribute('readonly')).toBe(true);
    expect(nombre.hasAttribute('readonly')).toBe(false);
  });

  test('setEnabled(false) retira inputmode/readonly de todos los inputs marcados', () => {
    document.body.innerHTML = '<input id="cantidad" type="number" inputmode="decimal" value="1">';
    const controller = new VirtualKeyboardController();
    controller.init(true);

    controller.setEnabled(false);

    const cantidad = document.getElementById('cantidad');
    expect(cantidad.getAttribute('inputmode')).toBe('decimal');
    expect(cantidad.hasAttribute('readonly')).toBe(false);
  });

  test('un input añadido dinámicamente se marca tras el siguiente microtask (MutationObserver)', async () => {
    document.body.innerHTML = '';
    const controller = new VirtualKeyboardController();
    controller.init(true);

    const nuevo = document.createElement('input');
    nuevo.type = 'number';
    document.body.appendChild(nuevo);

    await Promise.resolve();
    await Promise.resolve();

    expect(nuevo.getAttribute('inputmode')).toBe('none');
    expect(nuevo.hasAttribute('readonly')).toBe(true);
  });
});

describe('VirtualKeyboardController.insertChar()/backspace()', () => {
  let controller;
  let input;

  beforeEach(() => {
    document.body.innerHTML = '<input id="cantidad" type="number" value="12">';
    input = document.getElementById('cantidad');
    controller = new VirtualKeyboardController();
    controller.attach(input);
  });

  // Los inputs type="number" no soportan selectionStart/selectionEnd
  // (siempre null) ni setSelectionRange (lanza InvalidStateError), tanto en
  // jsdom como en navegadores reales. insertChar()/backspace() por tanto
  // operan siempre al final del valor para este tipo de campo, como un
  // teclado numérico tipo calculadora.
  test('insertChar() añade el dígito al final y dispara evento input', () => {
    const onInput = jest.fn();
    input.addEventListener('input', onInput);

    controller.insertChar('9');

    expect(input.value).toBe('129');
    expect(onInput).toHaveBeenCalledTimes(1);
  });

  test('backspace() borra el último carácter', () => {
    controller.backspace();

    expect(input.value).toBe('1');
  });

  test('backspace() no falla al llegar a un valor vacío', () => {
    controller.backspace();
    controller.backspace();

    expect(input.value).toBe('');
    expect(() => controller.backspace()).not.toThrow();
    expect(input.value).toBe('');
  });
});

describe('VirtualKeyboardController.commitEnter()', () => {
  test('respeta min/max: no avanza si el valor no es válido', () => {
    document.body.innerHTML = '<form><input id="dias" type="number" min="0" max="100" value="500"></form>';
    const input = document.getElementById('dias');
    const controller = new VirtualKeyboardController();
    controller.attach(input);
    input.reportValidity = jest.fn();

    controller.commitEnter();

    expect(controller.activeInput).toBe(input);
    expect(input.reportValidity).toHaveBeenCalled();
  });

  test('con un valor válido, dispara change y cierra el teclado', () => {
    document.body.innerHTML = '<input id="dias" type="number" min="0" max="100" value="30">';
    const input = document.getElementById('dias');
    const controller = new VirtualKeyboardController();
    controller.attach(input);
    const onChange = jest.fn();
    input.addEventListener('change', onChange);

    controller.commitEnter();

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(controller.activeInput).toBeNull();
  });
});
