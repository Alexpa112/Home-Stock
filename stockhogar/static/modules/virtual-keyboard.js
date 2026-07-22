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
    if (!(el instanceof HTMLElement) || el.tagName !== 'INPUT') return false;
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
    // Inputs a los que ya se les ha puesto inputmode="none"/readonly. La
    // marca se aplica de forma PROACTIVA (ver _sincronizarMarcado), no en
    // el propio focusin: iOS decide si mostrar su teclado nativo en el
    // instante en que empieza el foco, usando el inputmode/readonly que el
    // campo YA tenía en ese momento. Cambiar esos atributos dentro del
    // propio handler de focus llega demasiado tarde y Safari llega a
    // mostrar el teclado nativo de todos modos (bug real detectado en un
    // iPhone real, no solo un matiz teórico).
    this.marcados = new Set();
    this._observer = null;
    this._sincronizarMarcadoDiferido = this._sincronizarMarcadoDiferido.bind(this);
    this._onDocFocusIn = this._onDocFocusIn.bind(this);
    this._onDocFocusOut = this._onDocFocusOut.bind(this);
    this._onDocKeyDown = this._onDocKeyDown.bind(this);
  }

  init(preferenciaInicial) {
    this.enabled = preferenciaInicial !== false;
    this._crearDom();
    document.addEventListener('focusin', this._onDocFocusIn, true);
    document.addEventListener('focusout', this._onDocFocusOut, true);
    document.addEventListener('keydown', this._onDocKeyDown, true);

    this._sincronizarMarcado();

    // Los formularios de ticket/lista generan filas de <input> nuevas en
    // caliente (app.js, form-builder.js); hay que marcarlas también en
    // cuanto aparecen, antes de que el usuario pueda tocarlas.
    this._observer = new MutationObserver(this._sincronizarMarcadoDiferido);
    this._observer.observe(document.body, { childList: true, subtree: true });
  }

  setEnabled(activo) {
    this.enabled = !!activo;
    if (this.activeInput) this._ocultarPanel();
    this._sincronizarMarcado();
  }

  _sincronizarMarcadoDiferido() {
    // Varias mutaciones del DOM pueden llegar en el mismo tick; una sola
    // pasada basta.
    if (this._sincPendiente) return;
    this._sincPendiente = true;
    Promise.resolve().then(() => {
      this._sincPendiente = false;
      this._sincronizarMarcado();
    });
  }

  /* Aplica o retira inputmode="none"/readonly según corresponda AHORA
     (preferencia + tipo de dispositivo + heurísticas de accesibilidad),
     de forma proactiva y no solo en el momento del foco. */
  _sincronizarMarcado() {
    const activar = VirtualKeyboardDetector.shouldUseCustomKeyboard(this.enabled);
    if (activar) {
      document.querySelectorAll('input').forEach((el) => {
        if (this.marcados.has(el)) return;
        if (VirtualKeyboardLayout.esInputNumerico(el)) this._marcar(el);
      });
    } else {
      Array.from(this.marcados).forEach((el) => this._desmarcar(el));
    }
  }

  _marcar(el) {
    if (this.marcados.has(el)) return;
    el.dataset.tecladoInputmodeOriginal = el.getAttribute('inputmode') || '';
    el.dataset.tecladoReadonlyOriginal = el.hasAttribute('readonly') ? '1' : '0';
    el.setAttribute('inputmode', 'none');
    el.setAttribute('readonly', 'readonly');
    this.marcados.add(el);
  }

  _desmarcar(el) {
    if (!this.marcados.has(el)) return;
    if (el.dataset.tecladoInputmodeOriginal) {
      el.setAttribute('inputmode', el.dataset.tecladoInputmodeOriginal);
    } else {
      el.removeAttribute('inputmode');
    }
    if (el.dataset.tecladoReadonlyOriginal !== '1') {
      el.removeAttribute('readonly');
    }
    delete el.dataset.tecladoInputmodeOriginal;
    delete el.dataset.tecladoReadonlyOriginal;
    this.marcados.delete(el);
    if (this.activeInput === el) this._ocultarPanel();
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
        btn.tabIndex = -1;
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

    // En iOS Safari, preventDefault() en 'pointerdown' no siempre basta para
    // impedir que el input pierda el foco al tocar una tecla del panel (bug
    // real detectado en un iPhone: el teclado se cerraba al pulsar una
    // tecla). El evento cuyo preventDefault() SÍ bloquea de forma fiable el
    // cambio de foco en WebKit es 'touchstart', así que se añade aquí como
    // defensa principal; 'pointerdown' se mantiene para procesar la pulsación
    // en sí (funciona igual con touch, mouse y trackpad).
    el.addEventListener('touchstart', (e) => {
      if (e.target.closest('button[data-tecla]')) e.preventDefault();
    }, { passive: false });

    el.addEventListener('pointerdown', (e) => {
      const btn = e.target.closest('button[data-tecla]');
      if (!btn) return;
      e.preventDefault();
      // Segunda defensa: mientras se procesa el toque, ignorar cualquier
      // blur del input activo (ver _onDocFocusOut) aunque el navegador
      // mueva el foco pese al preventDefault de arriba.
      this._interactuandoConPanel = true;
      this._manejarTecla(btn.dataset.tecla);
      window.setTimeout(() => { this._interactuandoConPanel = false; }, 50);
    });

    document.body.appendChild(el);
    this.element = el;
  }

  _onDocFocusIn(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    // Solo actuamos sobre inputs que YA estaban marcados de antemano
    // (ver _sincronizarMarcado); si no lo estaba, es que el teclado nativo
    // ya se está mostrando y no hay nada que hacer en este foco.
    if (!this.marcados.has(target)) return;
    if (target.disabled) return;
    this.attach(target);
  }

  _onDocFocusOut(event) {
    const target = event.target;
    if (target !== this.activeInput) return;
    // Si el blur lo ha provocado tocar una tecla del panel, no cerramos:
    // preventDefault() en touchstart/pointerdown ya debería evitarlo, pero
    // esta bandera es la red de seguridad para WebKit (ver _crearDom).
    if (this._interactuandoConPanel) return;
    window.setTimeout(() => {
      if (this._interactuandoConPanel) return;
      if (document.activeElement !== this.activeInput) {
        this._ocultarPanel();
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
    // Teclado físico real detectado: dejar de suprimir el teclado nativo
    // en todos los inputs y ocultar el panel si estaba abierto.
    this._sincronizarMarcado();
  }

  /* Muestra el panel del teclado para un input ya marcado (inputmode="none"
     + readonly ya aplicados de antemano por _sincronizarMarcado). */
  attach(inputEl) {
    if (this.activeInput === inputEl) return;
    if (this.activeInput) this._ocultarPanel();
    if (!this.element) this._crearDom();
    this._marcar(inputEl); // red de seguridad si se llama sin pasar por _sincronizarMarcado (tests, uso directo)

    this.activeInput = inputEl;
    this.element.hidden = false;

    this._reportarAltura();
    document.body.dataset.tecladoVirtualActivo = '1';

    // El panel puede encoger el modal/contenedor que se esté mostrando
    // (ver responsive.css, --keyboard-offset); si el input estaba cerca
    // del final de un formulario largo con scroll (p.ej. revisión de
    // ticket), puede quedar oculto bajo el nuevo borde inferior. Se
    // difiere al siguiente frame para que el reflow del max-height ya
    // se haya aplicado antes de calcular qué hace falta desplazar.
    window.requestAnimationFrame(() => {
      if (this.activeInput === inputEl) {
        inputEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    });
  }

  /* Oculta el panel y limpia el estado de "teclado abierto", pero NO
     restaura inputmode/readonly del input: mientras la función siga
     activada para este dispositivo, el campo debe seguir suprimiendo el
     teclado nativo aunque se cambie de campo o se cierre el modal. Esos
     atributos solo se retiran en _desmarcar() (toggle de Ajustes, o
     detección de teclado físico/lector de pantalla). */
  _ocultarPanel() {
    if (!this.activeInput) return;
    this.activeInput = null;
    if (this.element) this.element.hidden = true;

    document.body.classList.remove('keyboard-open', 'is-keyboard-open');
    document.documentElement.style.setProperty('--keyboard-offset', '0px');
    document.documentElement.style.setProperty('--keyboard-height', '0px');
    delete document.body.dataset.tecladoVirtualActivo;

    if (typeof window.ajustarViewportMovil === 'function') {
      window.ajustarViewportMovil();
    }
  }

  /* Alias público: mismo comportamiento que _ocultarPanel(), usado por
     código externo (p.ej. al desactivar la preferencia desde Ajustes). */
  detach() {
    this._ocultarPanel();
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
    // temporalmente el readonly (permanece marcado como gestionado; solo
    // se retira el atributo un instante para poder validar).
    const teniaReadonlyPropio = el.hasAttribute('readonly');
    if (teniaReadonlyPropio) el.removeAttribute('readonly');
    const esValido = typeof el.checkValidity !== 'function' || el.checkValidity();
    if (!esValido) {
      el.reportValidity?.();
      if (teniaReadonlyPropio) el.setAttribute('readonly', 'readonly');
      return;
    }
    if (teniaReadonlyPropio) el.setAttribute('readonly', 'readonly');
    el.dispatchEvent(new Event('change', { bubbles: true }));
    this._ocultarPanel();
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
