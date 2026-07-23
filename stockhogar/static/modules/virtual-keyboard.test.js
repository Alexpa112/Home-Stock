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
  // El toggle manual de Ajustes manda sobre cualquier heurística automática:
  // ni el tipo de puntero, ni la detección de lector de pantalla, ni la de
  // teclado físico deben poder anular la preferencia explícita del usuario.
  test('false si la preferencia de usuario está desactivada', () => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(false)).toBe(false);
  });

  test('true si la preferencia está activada aunque se detectó navegación por Tab', () => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
    window.__a11y_tabDetectado = true;
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(true)).toBe(true);
  });

  test('true si la preferencia está activada aunque se detectó teclado físico', () => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
    window.__teclado_fisico_detectado = true;
    expect(VirtualKeyboardDetector.shouldUseCustomKeyboard(true)).toBe(true);
  });

  test('true si la preferencia está activada aunque el dispositivo reporte puntero fino (no touch-only)', () => {
    mockMatchMedia({
      '(pointer: coarse)': false,
      '(hover: none)': false,
      '(any-pointer: fine)': true,
    });
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

describe('VirtualKeyboardLayout.esInputTexto()/tipoLayout() (fase 2)', () => {
  test.each(['text', 'email', 'password', 'tel', 'search'])('type="%s" es texto', (type) => {
    document.body.innerHTML = `<input type="${type}">`;
    const el = document.querySelector('input');
    expect(VirtualKeyboardLayout.esInputTexto(el)).toBe(true);
    expect(VirtualKeyboardLayout.tipoLayout(el)).toBe('texto');
  });

  test.each(['color', 'file', 'hidden', 'date'])('type="%s" no es texto ni numérico (tipoLayout null)', (type) => {
    document.body.innerHTML = `<input type="${type}">`;
    const el = document.querySelector('input');
    expect(VirtualKeyboardLayout.esInputTexto(el)).toBe(false);
    expect(VirtualKeyboardLayout.tipoLayout(el)).toBeNull();
  });

  test('type="number" es numérico, no texto', () => {
    document.body.innerHTML = '<input type="number">';
    const el = document.querySelector('input');
    expect(VirtualKeyboardLayout.esInputTexto(el)).toBe(false);
    expect(VirtualKeyboardLayout.tipoLayout(el)).toBe('numerico');
  });

  test('un <select> nunca es candidato', () => {
    document.body.innerHTML = '<select><option>a</option></select>';
    const el = document.querySelector('select');
    expect(VirtualKeyboardLayout.tipoLayout(el)).toBeNull();
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

  test('init() marca de antemano los inputs numéricos y de texto ya presentes en el DOM (antes de cualquier foco)', () => {
    document.body.innerHTML = '<input id="cantidad" type="number" value="1"><input id="nombre" type="text"><input id="color" type="color">';
    const controller = new VirtualKeyboardController();

    controller.init(true);

    const cantidad = document.getElementById('cantidad');
    const nombre = document.getElementById('nombre');
    const color = document.getElementById('color');
    expect(cantidad.getAttribute('inputmode')).toBe('none');
    expect(cantidad.hasAttribute('readonly')).toBe(true);
    // Fase 2: los inputs de texto también se gestionan (antes se excluían).
    expect(nombre.getAttribute('inputmode')).toBe('none');
    expect(nombre.hasAttribute('readonly')).toBe(true);
    // type="color" nunca es candidato.
    expect(color.hasAttribute('readonly')).toBe(false);
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

  test('una mutación del DOM sin ningún <input> nuevo no dispara un re-escaneo del documento', async () => {
    document.body.innerHTML = '';
    const controller = new VirtualKeyboardController();
    controller.init(true);

    const spyQuerySelectorAll = jest.spyOn(document, 'querySelectorAll');
    spyQuerySelectorAll.mockClear();

    const divSinInputs = document.createElement('div');
    divSinInputs.innerHTML = '<span>tile de la lista de la compra</span>';
    document.body.appendChild(divSinInputs);

    await Promise.resolve();
    await Promise.resolve();

    expect(spyQuerySelectorAll).not.toHaveBeenCalledWith('input');
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

describe('VirtualKeyboardController: el panel no se cierra por blur transitorio al escribir', () => {
  // Bug real reportado en un iPhone (fase 2, primera versión): el teclado se
  // cerraba en mitad de la escritura. Causa: se cerraba en 'focusout' con un
  // setTimeout comprobando si el foco se había ido, y WebKit puede disparar
  // blur/focus de forma transitoria al reflowar el layout tras cada
  // pulsación, sin que el usuario haya tocado nada fuera del campo. Ahora
  // solo se cierra cuando el foco aterriza de verdad en OTRO elemento.
  beforeEach(() => {
    mockMatchMedia({
      '(pointer: coarse)': true,
      '(hover: none)': true,
      '(any-pointer: fine)': false,
    });
  });

  test('un focusout aislado (sin que el foco aterrice en otro sitio) no cierra el panel', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    const input = document.getElementById('nombre');
    controller.attach(input);

    input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));

    expect(controller.activeInput).toBe(input);
    expect(controller.element.hidden).toBe(false);
  });

  test('escribir varias letras seguidas mantiene el panel abierto', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    const input = document.getElementById('nombre');
    controller.attach(input);

    ['h', 'o', 'l', 'a'].forEach((letra) => controller._manejarTecla(letra));

    expect(input.value).toBe('hola');
    expect(controller.activeInput).toBe(input);
    expect(controller.element.hidden).toBe(false);
  });

  test('el panel SÍ se cierra cuando el foco aterriza de verdad en otro input no gestionado', () => {
    document.body.innerHTML = '<input id="nombre" type="text"><input id="otro" type="checkbox">';
    const controller = new VirtualKeyboardController();
    controller.init(true); // necesario: el listener de focusin vive en document, no en el input
    const input = document.getElementById('nombre');
    const otro = document.getElementById('otro');
    controller.attach(input);

    otro.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));

    expect(controller.activeInput).toBeNull();
    expect(controller.element.hidden).toBe(true);
  });

  test('tocar fuera del teclado y del input activo lo cierra, aunque lo tocado no sea enfocable', () => {
    document.body.innerHTML = '<input id="nombre" type="text"><div id="tarjeta">una tarjeta cualquiera</div>';
    const controller = new VirtualKeyboardController();
    controller.init(true);
    const input = document.getElementById('nombre');
    input.focus();
    controller.attach(input);

    document.getElementById('tarjeta').dispatchEvent(new Event('pointerdown', { bubbles: true }));

    expect(controller.activeInput).toBeNull();
    expect(controller.element.hidden).toBe(true);
    expect(document.activeElement).not.toBe(input);
  });

  test('tocar una tecla del propio panel NO cierra el teclado (pointerdown dentro del panel)', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.init(true);
    controller.attach(document.getElementById('nombre'));

    const botonQ = controller.element.querySelector('button[data-tecla="q"]');
    botonQ.dispatchEvent(new Event('pointerdown', { bubbles: true }));

    expect(controller.activeInput).not.toBeNull();
    expect(controller.element.hidden).toBe(false);
  });

  test('perder la atención de la pestaña (window blur) cierra el panel', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.init(true);
    controller.attach(document.getElementById('nombre'));

    window.dispatchEvent(new Event('blur'));

    expect(controller.activeInput).toBeNull();
  });
});

describe('VirtualKeyboardController fase 2: panel alfanumérico', () => {
  function tecla(controller, valor) {
    return controller.element.querySelector(`button[data-tecla="${valor}"]`);
  }

  test('attach() con input de texto muestra el sub-panel alfa y oculta el numérico', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.attach(document.getElementById('nombre'));

    expect(controller.panelAlfa.hidden).toBe(false);
    expect(controller.panelNumerico.hidden).toBe(true);
    expect(controller.element.getAttribute('aria-label')).toBe('Teclado alfanumérico');
  });

  test('attach() con input numérico muestra el sub-panel numérico y oculta el alfa', () => {
    document.body.innerHTML = '<input id="cantidad" type="number">';
    const controller = new VirtualKeyboardController();
    controller.attach(document.getElementById('cantidad'));

    expect(controller.panelNumerico.hidden).toBe(false);
    expect(controller.panelAlfa.hidden).toBe(true);
    expect(controller.element.getAttribute('aria-label')).toBe('Teclado numérico');
  });

  test('la tecla ⇧ alterna mayúsculas sin recrear el DOM (mismo nodo antes/después)', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    const input = document.getElementById('nombre');
    controller.attach(input);

    const botonQ = tecla(controller, 'q');
    expect(botonQ.textContent).toBe('q');

    controller._manejarTecla('⇧');

    const botonMayus = tecla(controller, 'Q');
    expect(botonMayus).toBe(botonQ); // mismo nodo, solo cambió textContent/dataset

    controller._manejarTecla('Q'); // pulsar la Q ya en mayúscula inserta 'Q' y autodesactiva shift
    expect(input.value).toBe('Q');

    controller._manejarTecla('a');
    expect(input.value).toBe('Qa');
    expect(tecla(controller, 'q')).not.toBeNull(); // el shift ya se autodesactivó: volvió a minúscula
  });

  test('la tecla 123/ABC alterna la capa de letras y la de símbolos/acentos', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.attach(document.getElementById('nombre'));

    expect(controller._grupoLetras.hidden).toBe(false);
    expect(controller._grupoSimbolos.hidden).toBe(true);

    controller._manejarTecla('123');

    expect(controller._grupoLetras.hidden).toBe(true);
    expect(controller._grupoSimbolos.hidden).toBe(false);
    expect(tecla(controller, 'ABC')).not.toBeNull();

    controller._manejarTecla('ABC');

    expect(controller._grupoLetras.hidden).toBe(false);
    expect(controller._grupoSimbolos.hidden).toBe(true);
  });

  test('los dígitos viven en la capa de símbolos: no se ven hasta pulsar 123', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.attach(document.getElementById('nombre'));

    // querySelector busca en todo el panel, incluido el numérico (que tiene
    // sus propias teclas '1'..'9'): hay que acotar al grupo de símbolos del
    // panel alfa para comprobar el dígito que nos interesa.
    const digitoUno = () => controller._grupoSimbolos.querySelector('button[data-tecla="1"]');

    // Antes de pulsar 123, el dígito vive en _grupoSimbolos pero no es
    // visible (el grupo entero está hidden).
    expect(digitoUno()).not.toBeNull();
    expect(digitoUno().closest('[hidden]')).not.toBeNull();

    controller._manejarTecla('123');

    expect(controller._grupoSimbolos.hidden).toBe(false);
    expect(digitoUno().closest('[hidden]')).toBeNull();

    controller._manejarTecla('1');
    expect(document.getElementById('nombre').value).toBe('1');
  });

  test('la tecla 👁 solo aparece para type="password" y alterna la visibilidad', () => {
    document.body.innerHTML = '<input id="pass" type="password"><input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();

    controller.attach(document.getElementById('nombre'));
    expect(controller._btnPassword.hidden).toBe(true);

    const passwordInput = document.getElementById('pass');
    controller.attach(passwordInput);
    expect(controller._btnPassword.hidden).toBe(false);
    expect(passwordInput.type).toBe('password');

    controller._manejarTecla('👁');
    expect(passwordInput.type).toBe('text');

    controller._manejarTecla('🙈');
    expect(passwordInput.type).toBe('password');
  });

  test('insertChar() en type="text" respeta selectionStart/selectionEnd reales', () => {
    document.body.innerHTML = '<input id="nombre" type="text" value="ab">';
    const controller = new VirtualKeyboardController();
    const input = document.getElementById('nombre');
    controller.attach(input);
    input.setSelectionRange(1, 1); // cursor entre 'a' y 'b'

    controller.insertChar('X');

    expect(input.value).toBe('aXb');
    expect(input.selectionStart).toBe(2);
  });

  test('irAlSiguienteCampo(): con varios inputs en el mismo form, Intro avanza al siguiente', () => {
    document.body.innerHTML = `
      <form>
        <input id="uno" type="text">
        <input id="dos" type="text">
      </form>`;
    const controller = new VirtualKeyboardController();
    const uno = document.getElementById('uno');
    const dos = document.getElementById('dos');
    controller.attach(uno);
    controller._marcar(dos, 'texto');

    controller.irAlSiguienteCampo();

    expect(document.activeElement).toBe(dos);
  });

  test('irAlSiguienteCampo(): en el último campo, dispara change y cierra el panel sin validar', () => {
    document.body.innerHTML = '<input id="unico" type="text" required>';
    const controller = new VirtualKeyboardController();
    const input = document.getElementById('unico');
    controller.attach(input);
    const onChange = jest.fn();
    input.addEventListener('change', onChange);

    controller.irAlSiguienteCampo();

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(controller.activeInput).toBeNull();
  });

  test('Intro en un input de texto llama a irAlSiguienteCampo(), no a commitEnter()', () => {
    document.body.innerHTML = '<input id="nombre" type="text">';
    const controller = new VirtualKeyboardController();
    controller.attach(document.getElementById('nombre'));
    const spyIr = jest.spyOn(controller, 'irAlSiguienteCampo');
    const spyCommit = jest.spyOn(controller, 'commitEnter');

    controller._manejarTecla('Intro');

    expect(spyIr).toHaveBeenCalledTimes(1);
    expect(spyCommit).not.toHaveBeenCalled();
  });
});
