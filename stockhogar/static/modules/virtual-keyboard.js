/**
 * TECLADO VIRTUAL PROPIO - Fase 1 (solo layout numérico)
 * Sustituye al teclado nativo de iOS/Android en inputs numéricos
 * (type="number" o inputmode="numeric"/"decimal"), solo en móvil táctil.
 *
 * Los inputs de texto/email/password/tel/search NO se ven afectados en
 * esta fase: siguen usando el teclado nativo del sistema sin cambios.
 */

/** Detección de cuándo debe activarse el teclado custom. */
class VirtualKeyboardDetector {
  /* Solo táctil: puntero grueso, sin hover, y sin puntero fino disponible
     (descarta portátiles/tablets con mouse o trackpad conectado). */
  static isTouchOnly() {
    if (!window.matchMedia) return false;
    const coarse = window.matchMedia('(pointer: coarse)').matches;
    const noHover = window.matchMedia('(hover: none)').matches;
    const anyFine = window.matchMedia('(any-pointer: fine)').matches;
    return coarse && noHover && !anyFine;
  }

  /* No existe API web fiable para detectar un lector de pantalla activo.
     Heurística best-effort: si se detecta navegación por Tab antes de
     cualquier toque, asumimos navegación asistida por teclado físico.
     LIMITACIÓN CONOCIDA: VoiceOver/TalkBack activados por gestos táctiles
     (el caso más común en móvil) NO se detectan con esta señal, ya que
     esos lectores no usan Tab en touch. La mitigación real para ese caso
     es el toggle manual de Ajustes, no esta heurística. */
  static hasScreenReader() {
    return window.__a11y_tabDetectado === true;
  }

  /* Heurística: un keydown real (no generado por el teclado custom) indica
     que hay un teclado físico (USB/Bluetooth) conectado. Se persiste en
     sessionStorage para no reaparecer en el resto de la sesión. */
  static hasPhysicalKeyboard() {
    if (window.__teclado_fisico_detectado === true) return true;
    try {
      return sessionStorage.getItem('stockhogar-teclado-fisico-detectado') === '1';
    } catch (error) {
      return false;
    }
  }

  static shouldUseCustomKeyboard(preferenciaUsuario) {
    if (!preferenciaUsuario) return false;
    if (!VirtualKeyboardDetector.isTouchOnly()) return false;
    if (VirtualKeyboardDetector.hasScreenReader()) return false;
    if (VirtualKeyboardDetector.hasPhysicalKeyboard()) return false;
    return true;
  }
}

/** Decide qué layout mostrar según el input enfocado. */
class VirtualKeyboardLayout {
  static esInputNumerico(el) {
    if (!(el instanceof HTMLElement)) return false;
    const inputmode = (el.getAttribute('inputmode') || '').toLowerCase();
    const type = (el.getAttribute('type') || el.type || 'text').toLowerCase();
    if (inputmode === 'numeric' || inputmode === 'decimal') return true;
    return type === 'number';
  }
}

/** Controlador del teclado virtual: DOM, foco, inserción de caracteres. */
class VirtualKeyboardController {
  constructor() {
    this.enabled = false;
    this.activeInput = null;
    this.element = null;
    this._onDocFocusIn = this._onDocFocusIn.bind(this);
    this._onDocFocusOut = this._onDocFocusOut.bind(this);
    this._onDocKeyDown = this._onDocKeyDown.bind(this);
    this._onDocTouchStart = this._onDocTouchStart.bind(this);
  }

  init(preferenciaInicial) {
    this.enabled = preferenciaInicial !== false;
    this._crearDom();
    document.addEventListener('focusin', this._onDocFocusIn, true);
    document.addEventListener('focusout', this._onDocFocusOut, true);
    document.addEventListener('keydown', this._onDocKeyDown, true);
    document.addEventListener('touchstart', this._onDocTouchStart, { capture: true, once: true });
  }

  setEnabled(activo) {
    this.enabled = !!activo;
    if (!this.enabled && this.activeInput) {
      this.detach();
    }
  }

  _crearDom() {
    if (this.element) return;
    const el = document.createElement('div');
    el.id = 'tecladoVirtualNumerico';
    el.className = 'teclado-virtual';
    el.hidden = true;
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'Teclado numérico');

    const filas = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      [',', '0', '⌫'],
    ];

    filas.forEach((fila) => {
      const filaEl = document.createElement('div');
      filaEl.className = 'teclado-virtual-fila';
      fila.forEach((tecla) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'teclado-virtual-tecla';
        if (tecla === '⌫') btn.classList.add('teclado-virtual-tecla--borrar');
        btn.textContent = tecla;
        btn.dataset.tecla = tecla;
        filaEl.appendChild(btn);
      });
      el.appendChild(filaEl);
    });

    const filaAcciones = document.createElement('div');
    filaAcciones.className = 'teclado-virtual-fila';
    const btnIntro = document.createElement('button');
    btnIntro.type = 'button';
    btnIntro.className = 'teclado-virtual-tecla teclado-virtual-tecla--intro';
    btnIntro.textContent = 'Intro';
    btnIntro.dataset.tecla = 'Intro';
    filaAcciones.appendChild(btnIntro);
    el.appendChild(filaAcciones);

    el.addEventListener('pointerdown', (e) => {
      const btn = e.target.closest('button[data-tecla]');
      if (!btn) return;
      e.preventDefault();
      this._manejarTecla(btn.dataset.tecla);
    });

    document.body.appendChild(el);
    this.element = el;
  }

  _onDocFocusIn(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (!this.enabled) return;
    if (!VirtualKeyboardLayout.esInputNumerico(target)) return;
    if (target.disabled) return;
    if (!VirtualKeyboardDetector.shouldUseCustomKeyboard(this.enabled)) return;
    if (target.dataset.tecladoGestionado === '1') return;
    this.attach(target);
  }

  _onDocFocusOut(event) {
    const target = event.target;
    if (target !== this.activeInput) return;
    // Si el nuevo foco es una tecla del teclado virtual, no lo cerramos:
    // el pointerdown de la tecla ya llama a preventDefault(), así que en
    // la práctica esto solo dispara al perder el foco de verdad.
    window.setTimeout(() => {
      if (document.activeElement !== this.activeInput) {
        this.detach();
      }
    }, 0);
  }

  _onDocKeyDown(event) {
    if (this._tecladoCustomOrigina) return;
    window.__teclado_fisico_detectado = true;
    try {
      sessionStorage.setItem('stockhogar-teclado-fisico-detectado', '1');
    } catch (error) {
      // sessionStorage no disponible (modo privado); no es bloqueante.
    }
    if (this.activeInput) this.detach();
  }

  _onDocTouchStart() {
    // Primer toque sin Tab previo: no era navegación por teclado físico.
    // No hace falta hacer nada; la señal de hasScreenReader() solo se activa
    // si Tab llega ANTES que este touchstart (ver listener de Tab abajo).
  }

  attach(inputEl) {
    if (this.activeInput === inputEl) return;
    if (this.activeInput) this.detach();
    if (!this.element) this._crearDom();

    inputEl.dataset.tecladoGestionado = '1';
    inputEl.dataset.tecladoInputmodeOriginal = inputEl.getAttribute('inputmode') || '';
    inputEl.dataset.tecladoReadonlyOriginal = inputEl.hasAttribute('readonly') ? '1' : '0';
    inputEl.setAttribute('inputmode', 'none');
    inputEl.setAttribute('readonly', 'readonly');

    this.activeInput = inputEl;
    this.element.hidden = false;

    this._reportarAltura();
    document.body.dataset.tecladoVirtualActivo = '1';
  }

  detach() {
    if (!this.activeInput) return;
    const inputEl = this.activeInput;

    if (inputEl.dataset.tecladoInputmodeOriginal) {
      inputEl.setAttribute('inputmode', inputEl.dataset.tecladoInputmodeOriginal);
    } else {
      inputEl.removeAttribute('inputmode');
    }
    if (inputEl.dataset.tecladoReadonlyOriginal !== '1') {
      inputEl.removeAttribute('readonly');
    }
    delete inputEl.dataset.tecladoGestionado;
    delete inputEl.dataset.tecladoInputmodeOriginal;
    delete inputEl.dataset.tecladoReadonlyOriginal;

    this.activeInput = null;
    this.element.hidden = true;

    document.body.classList.remove('keyboard-open', 'is-keyboard-open');
    document.documentElement.style.setProperty('--keyboard-offset', '0px');
    document.documentElement.style.setProperty('--keyboard-height', '0px');
    delete document.body.dataset.tecladoVirtualActivo;

    if (typeof window.ajustarViewportMovil === 'function') {
      window.ajustarViewportMovil();
    }
  }

  _reportarAltura() {
    const alto = this.element.getBoundingClientRect().height;
    document.documentElement.style.setProperty('--keyboard-height', `${alto}px`);
    document.documentElement.style.setProperty('--keyboard-offset', `${alto}px`);
    document.body.classList.add('keyboard-open');
    const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some((modal) => !modal.hidden);
    document.body.classList.toggle('is-keyboard-open', !hayModalAbierto);
  }

  _manejarTecla(tecla) {
    if (!this.activeInput) return;
    this._tecladoCustomOrigina = true;
    if (tecla === '⌫') {
      this.backspace();
    } else if (tecla === 'Intro') {
      this.commitEnter();
    } else {
      this.insertChar(tecla);
    }
    window.setTimeout(() => { this._tecladoCustomOrigina = false; }, 0);
  }

  insertChar(ch) {
    const el = this.activeInput;
    if (!el) return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const valorPrevio = el.value;
    const nuevoValor = valorPrevio.slice(0, start) + ch + valorPrevio.slice(end);
    el.value = nuevoValor;
    const nuevaPosicion = start + ch.length;
    // En inputs type="number" (los únicos gestionados en esta fase),
    // setSelectionRange() no está soportado y lanza InvalidStateError
    // tanto en navegadores reales como en jsdom: la posición del cursor no
    // aplica a este tipo de campo, así que se ignora el error.
    try {
      el.setSelectionRange(nuevaPosicion, nuevaPosicion);
    } catch (error) {
      // Selección no soportada para este tipo de input; no es un fallo.
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }

  backspace() {
    const el = this.activeInput;
    if (!el) return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const valorPrevio = el.value;
    let nuevoValor;
    let nuevaPosicion;
    if (start !== end) {
      nuevoValor = valorPrevio.slice(0, start) + valorPrevio.slice(end);
      nuevaPosicion = start;
    } else if (start > 0) {
      nuevoValor = valorPrevio.slice(0, start - 1) + valorPrevio.slice(start);
      nuevaPosicion = start - 1;
    } else {
      return;
    }
    el.value = nuevoValor;
    try {
      el.setSelectionRange(nuevaPosicion, nuevaPosicion);
    } catch (error) {
      // Selección no soportada para este tipo de input; no es un fallo.
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }

  commitEnter() {
    const el = this.activeInput;
    if (!el) return;
    // Un input readonly queda "barred from constraint validation" según el
    // spec HTML: checkValidity() devolvería siempre true si no se quita
    // temporalmente el readonly que le pusimos nosotros en attach().
    const teniaReadonlyPropio = el.hasAttribute('readonly');
    if (teniaReadonlyPropio) el.removeAttribute('readonly');
    const esValido = typeof el.checkValidity !== 'function' || el.checkValidity();
    if (!esValido) {
      el.reportValidity?.();
      if (teniaReadonlyPropio) el.setAttribute('readonly', 'readonly');
      return;
    }
    el.dispatchEvent(new Event('change', { bubbles: true }));
    this.detach();
    el.blur();
  }
}

// Detección de navegación por Tab (heurística de lector de pantalla),
// instalada una sola vez a nivel global.
document.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') window.__a11y_tabDetectado = true;
}, { capture: true, once: true });

if (typeof module === 'undefined') {
  window.VirtualKeyboard = {
    VirtualKeyboardDetector,
    VirtualKeyboardLayout,
    VirtualKeyboardController,
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    VirtualKeyboardDetector,
    VirtualKeyboardLayout,
    VirtualKeyboardController,
  };
}
