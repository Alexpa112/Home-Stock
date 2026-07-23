/**
 * TECLADO VIRTUAL PROPIO
 * Sustituye al teclado nativo de iOS/Android, solo en móvil táctil:
 * - Fase 1: inputs numéricos (type="number" o inputmode="numeric"/"decimal").
 * - Fase 2: inputs de texto libre (text/email/password/tel/search), con
 *   layout QWERTY español, mayúsculas, capa de símbolos/acentos y mostrar/
 *   ocultar contraseña.
 *
 * El renderizado de las teclas usa la librería simple-keyboard (vendorizada
 * en static/vendor/simple-keyboard, sin CDN, para mantener la app offline):
 * es robusta, gestiona el toque de forma nativa (pointerdown/pointerup) sin
 * el retraso de "click" y no requiere reinventar la geometría de un teclado.
 * Toda la lógica de CUÁNDO/DÓNDE mostrarlo, qué input está activo, el marcado
 * proactivo de inputmode/readonly y la inserción de caracteres en el input
 * real sigue siendo propia (ver comentarios en cada método): esa es la parte
 * con quirks reales de iOS ya cazados uno a uno, y no depende del motor de
 * renderizado de las teclas.
 */

const SimpleKeyboardCtor = (typeof require === 'function')
  ? require('simple-keyboard').default
  : window.SimpleKeyboard && window.SimpleKeyboard.default;

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
     esos lectores no usan Tab en touch. Ya no se usa para desactivar el
     teclado propio (ver shouldUseCustomKeyboard): el toggle manual de
     Ajustes es la única mitigación real para ese caso. */
  static hasScreenReader() {
    return window.__a11y_tabDetectado === true;
  }

  /* Heurística: un keydown real (no generado por el teclado custom) indica
     que hay un teclado físico (USB/Bluetooth) conectado. Se persiste en
     sessionStorage para no reaparecer en el resto de la sesión. Ya no se usa
     para desactivar el teclado propio (ver shouldUseCustomKeyboard). */
  static hasPhysicalKeyboard() {
    if (window.__teclado_fisico_detectado === true) return true;
    try {
      return sessionStorage.getItem('stockhogar-teclado-fisico-detectado') === '1';
    } catch (error) {
      return false;
    }
  }

  /* El toggle manual de Ajustes manda sobre cualquier heurística automática
     (isTouchOnly/hasScreenReader/hasPhysicalKeyboard): si el dispositivo
     reporta un puntero fino falso (p.ej. soporte de lápiz) o una detección
     de teclado físico incorrecta, el usuario debe poder forzar el
     comportamiento eligiéndolo explícitamente en Ajustes. */
  static shouldUseCustomKeyboard(preferenciaUsuario) {
    return !!preferenciaUsuario;
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

  /* Texto libre: nombre, email, contraseña, teléfono, búsqueda. Se excluyen
     explícitamente color/file/hidden/date y cualquier no-<input> (select,
     textarea...), que no gestiona este teclado. */
  static esInputTexto(el) {
    if (!(el instanceof HTMLElement) || el.tagName !== 'INPUT') return false;
    if (VirtualKeyboardLayout.esInputNumerico(el)) return false;
    const type = (el.getAttribute('type') || el.type || 'text').toLowerCase();
    return ['text', 'email', 'password', 'tel', 'search'].includes(type);
  }

  /** 'numerico' | 'texto' | null (el input no lo gestiona este teclado). */
  static tipoLayout(el) {
    if (VirtualKeyboardLayout.esInputNumerico(el)) return 'numerico';
    if (VirtualKeyboardLayout.esInputTexto(el)) return 'texto';
    return null;
  }
}

// Layout numérico (simple-keyboard). Una sola capa.
const LAYOUT_NUMERICO = {
  default: [
    '1 2 3',
    '4 5 6',
    '7 8 9',
    ', 0 {bksp}',
    '{enter}',
  ],
};

// Layouts del panel alfanumérico: QWERTY español (con ñ), mayúsculas y una
// capa de símbolos/acentos. {numbers}/{abc} alternan default<->symbols;
// {shift} alterna default<->shift (un solo toque, no caps-lock).
const LAYOUT_ALFA = {
  default: [
    'q w e r t y u i o p',
    'a s d f g h j k l ñ',
    '{shift} z x c v b n m {bksp}',
    '{numbers} {eye} {space} {enter}',
  ],
  shift: [
    'Q W E R T Y U I O P',
    'A S D F G H J K L Ñ',
    '{shift} Z X C V B N M {bksp}',
    '{numbers} {eye} {space} {enter}',
  ],
  symbols: [
    '1 2 3 4 5 6 7 8 9 0',
    '¿ ¡ / : ; ( )',
    'á é í ó ú {bksp}',
    '{abc} {eye} {space} {enter}',
  ],
};

const DISPLAY_ALFA = {
  '{bksp}': '⌫',
  '{enter}': 'Intro',
  '{shift}': '⇧',
  '{numbers}': '123',
  '{abc}': 'ABC',
  '{space}': 'espacio',
  '{eye}': '👁',
};

const DISPLAY_NUMERICO = {
  '{bksp}': '⌫',
  '{enter}': 'Intro',
};

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
    // Tipo de layout ('numerico'|'texto') y si el input era originalmente
    // password, calculados una vez en _marcar() (no se recalculan en cada
    // foco: si se alterna el tipo a 'text' con el botón de mostrar/ocultar
    // contraseña, no debe cambiar de layout).
    this._tipoPorInput = new WeakMap();
    this._esPasswordPorInput = new WeakMap();
    this._tipoActivo = null; // 'numerico' | 'texto', del input actualmente enfocado
    this._layoutNameAlfa = 'default'; // 'default' | 'shift' | 'symbols'
    this._shiftActivo = false;
    this._observer = null;
    this._caretEl = null;
    this._canvasMedida = null;
    this._sincronizarMarcadoDiferido = this._sincronizarMarcadoDiferido.bind(this);
    this._onDocFocusIn = this._onDocFocusIn.bind(this);
    this._onDocKeyDown = this._onDocKeyDown.bind(this);
    this._onVentanaPierdeFoco = this._onVentanaPierdeFoco.bind(this);
    this._onCambioVisibilidad = this._onCambioVisibilidad.bind(this);
    this._onDocPointerDownFuera = this._onDocPointerDownFuera.bind(this);
    this._onDocClickActivo = this._onDocClickActivo.bind(this);
    this._onScrollOResize = this._onScrollOResize.bind(this);
    this._reportarAltura = this._reportarAltura.bind(this);
  }

  init(preferenciaInicial) {
    this.enabled = preferenciaInicial !== false;
    this._crearDom();
    document.addEventListener('focusin', this._onDocFocusIn, true);
    document.addEventListener('keydown', this._onDocKeyDown, true);
    // Tocar fuera del panel y fuera del input activo cierra el teclado, aun
    // cuando lo tocado no sea un elemento enfocable (una tarjeta, el fondo
    // de un modal...): en ese caso no llega ningún focusin que lo cierre por
    // la vía normal (_onDocFocusIn), así que hace falta esta señal aparte.
    // Se usa pointerdown (antes de que el navegador mueva el foco) y no
    // click, para blurrar el input ya en el mismo gesto en vez de un tick
    // después.
    document.addEventListener('pointerdown', this._onDocPointerDownFuera, true);
    // Red de seguridad para cuando la pestaña/app pierde la atención por
    // completo (cambio de app, bloqueo de pantalla...): ahí sí cerramos,
    // porque no habrá ningún focusin posterior que lo haga por nosotros.
    window.addEventListener('blur', this._onVentanaPierdeFoco);
    document.addEventListener('visibilitychange', this._onCambioVisibilidad);
    // El input activo es readonly (ver _marcar): no dibuja caret nativo, así
    // que hay que reposicionar el caret falso cuando el usuario toca dentro
    // del campo para mover el punto de inserción, o cuando el layout cambia.
    document.addEventListener('click', this._onDocClickActivo, true);
    window.addEventListener('resize', this._onScrollOResize);
    document.addEventListener('scroll', this._onScrollOResize, true);

    this._sincronizarMarcado();

    // Los formularios de ticket/lista generan filas de <input> nuevas en
    // caliente (app.js, form-builder.js); hay que marcarlas también en
    // cuanto aparecen, antes de que el usuario pueda tocarlas. La mayoría de
    // mutaciones del documento (re-render de la lista de la compra, tiles de
    // catálogo, etc.) no añaden ningún <input>, así que se filtran aquí para
    // no lanzar un querySelectorAll('input') sobre todo el documento en cada
    // mutación irrelevante.
    this._observer = new MutationObserver((mutaciones) => {
      const hayInputNuevo = mutaciones.some((m) =>
        Array.from(m.addedNodes).some(
          (nodo) =>
            nodo.nodeType === Node.ELEMENT_NODE &&
            (nodo.matches?.('input') || nodo.querySelector?.('input'))
        )
      );
      if (hayInputNuevo) this._sincronizarMarcadoDiferido();
    });
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
        const tipo = VirtualKeyboardLayout.tipoLayout(el);
        if (tipo) this._marcar(el, tipo);
      });
    } else {
      Array.from(this.marcados).forEach((el) => this._desmarcar(el));
    }
  }

  _marcar(el, tipo) {
    if (this.marcados.has(el)) return;
    el.dataset.tecladoInputmodeOriginal = el.getAttribute('inputmode') || '';
    el.dataset.tecladoReadonlyOriginal = el.hasAttribute('readonly') ? '1' : '0';
    el.setAttribute('inputmode', 'none');
    el.setAttribute('readonly', 'readonly');
    this.marcados.add(el);
    this._tipoPorInput.set(el, tipo || VirtualKeyboardLayout.tipoLayout(el) || 'numerico');
    this._esPasswordPorInput.set(el, (el.getAttribute('type') || '').toLowerCase() === 'password');
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

  /* Construye una instancia de simple-keyboard sobre un contenedor propio.
     onRender se dispara tras cada pulsación/cambio de layout: se aprovecha
     para volver a medir la altura real del panel (ver _reportarAltura), en
     vez de fiarnos de una única medición al abrir, que es lo que dejaba el
     offset de las modales desincronizado cuando el panel cambiaba de capa
     (p.ej. al pasar de letras a símbolos, con distinto número de filas). */
  _crearTeclado(contenedorEl, { layout, display }) {
    return new SimpleKeyboardCtor(contenedorEl, {
      layout,
      layoutName: 'default',
      display,
      mergeDisplay: true,
      physicalKeyboardHighlight: false,
      preventMouseDownDefault: true,
      disableCaretPositioning: true,
      // No se fuerza useTouchEvents/useMouseEvents: simple-keyboard usa
      // Pointer Events por defecto cuando el navegador los soporta (todos los
      // navegadores objetivo), que unifican ratón y táctil con la menor
      // latencia posible (pointerdown/pointerup, sin el retraso de ~300ms de
      // 'click' ni la duplicidad touch+mouse de forzar solo eventos táctiles).
      buttonTheme: [
        { class: 'teclado-virtual-tecla--borrar', buttons: '{bksp}' },
        { class: 'teclado-virtual-tecla--mayus', buttons: '{shift}' },
        { class: 'teclado-virtual-tecla--alterna', buttons: '{numbers} {abc}' },
        { class: 'teclado-virtual-tecla--intro', buttons: '{enter}' },
        { class: 'teclado-virtual-tecla--espacio', buttons: '{space}' },
        { class: 'teclado-virtual-tecla--ojo', buttons: '{eye}' },
      ],
      onKeyPress: (boton) => this._manejarTecla(boton),
      onRender: () => {
        if (this.activeInput) this._reportarAltura();
      },
    });
  }

  _crearDom() {
    if (this.element) return;
    const el = document.createElement('div');
    el.id = 'tecladoVirtual';
    el.className = 'teclado-virtual';
    el.hidden = true;
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'Teclado numérico');

    this.contNumerico = document.createElement('div');
    this.contNumerico.className = 'teclado-virtual-panel';
    this.contAlfa = document.createElement('div');
    this.contAlfa.className = 'teclado-virtual-panel';
    this.contAlfa.hidden = true;
    el.appendChild(this.contNumerico);
    el.appendChild(this.contAlfa);

    document.body.appendChild(el);
    this.element = el;

    this.tecladoNumerico = this._crearTeclado(this.contNumerico, {
      layout: LAYOUT_NUMERICO,
      display: DISPLAY_NUMERICO,
    });
    this.tecladoAlfa = this._crearTeclado(this.contAlfa, {
      layout: LAYOUT_ALFA,
      display: DISPLAY_ALFA,
    });

    // Botón de mostrar/ocultar contraseña: oculto salvo que el input activo
    // sea de tipo password (ver attach()).
    this.contAlfa.classList.add('teclado-virtual--sin-password');
  }

  /* Única fuente de verdad de cuándo abrir/cerrar el panel: se basa solo en
     hacia DÓNDE se mueve el foco real, nunca en un evento de blur aislado.
     Diseño anterior (fase 2 inicial): cerrábamos en focusout con un
     setTimeout(0) que comprobaba si el foco se había ido; en un iPhone
     real esto cerraba el teclado en mitad de la escritura, porque WebKit
     puede disparar blur/focus de forma transitoria (p.ej. al reflowar el
     layout tras cada pulsación) sin que el usuario haya tocado nada fuera
     del campo. Ahora solo cerramos cuando el foco aterriza de verdad en
     OTRO elemento distinto del campo activo y fuera del propio panel; si
     el foco no aterriza en ningún sitio reconocible (p. ej. un blur
     transitorio de WebKit), el panel simplemente se queda como estaba. */
  _onDocFocusIn(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    // Foco dentro del propio panel (no debería ocurrir, pero por si acaso):
    // no hacer nada.
    if (this.element && this.element.contains(target)) return;
    if (this.marcados.has(target) && !target.disabled) {
      this.attach(target);
      return;
    }
    // El foco ha ido a un elemento real que no gestiona este teclado
    // (otro campo, un botón...): eso sí es un cierre legítimo.
    if (this.activeInput && target !== this.activeInput) {
      this._ocultarPanel();
    }
  }

  _onVentanaPierdeFoco() {
    if (this.activeInput) this._ocultarPanel();
  }

  /* Cierra el teclado al tocar fuera de él y fuera del input activo, aunque
     lo tocado no sea focuseable (una tarjeta, el fondo de un modal...). El
     teclado solo debe estar visible mientras el usuario está realmente
     posicionado en un input gestionado por él. */
  _onDocPointerDownFuera(event) {
    if (!this.activeInput) return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (this.element && this.element.contains(target)) return;
    if (target === this.activeInput) return;
    this.activeInput.blur();
    this._ocultarPanel();
  }

  _onCambioVisibilidad() {
    if (document.hidden && this.activeInput) this._ocultarPanel();
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

  /* Reposiciona el caret falso cuando el usuario toca dentro del campo
     activo (el input es readonly y no dibuja caret nativo, ver _marcar). */
  _onDocClickActivo(event) {
    if (!this.activeInput) return;
    if (event.target !== this.activeInput) return;
    this._colocarCaretFalso();
  }

  _onScrollOResize() {
    if (this.activeInput) this._reportarAltura();
  }

  /* Muestra el panel del teclado para un input ya marcado (inputmode="none"
     + readonly ya aplicados de antemano por _sincronizarMarcado). */
  attach(inputEl) {
    if (this.activeInput === inputEl) return;
    if (this.activeInput) this._ocultarPanel();
    if (!this.element) this._crearDom();
    this._marcar(inputEl); // red de seguridad si se llama sin pasar por _sincronizarMarcado (tests, uso directo)

    this.activeInput = inputEl;
    this._tipoActivo = this._tipoPorInput.get(inputEl) || 'numerico';

    // Reset del estado del panel alfanumérico en cada apertura: siempre
    // empieza en minúsculas y en la capa de letras.
    this._layoutNameAlfa = 'default';
    this._shiftActivo = false;
    this.tecladoAlfa?.setOptions({ layoutName: 'default' });

    const esNumerico = this._tipoActivo === 'numerico';
    this.contNumerico.hidden = !esNumerico;
    this.contAlfa.hidden = esNumerico;
    this.element.setAttribute('aria-label', esNumerico ? 'Teclado numérico' : 'Teclado alfanumérico');

    const esPassword = this._esPasswordPorInput.get(inputEl) === true;
    this.contAlfa.classList.toggle('teclado-virtual--sin-password', !esPassword);
    if (esPassword) {
      inputEl.type = 'password';
      this.tecladoAlfa?.setOptions({ display: { ...DISPLAY_ALFA, '{eye}': '👁' } });
    }

    this.element.hidden = false;

    this._reportarAltura();
    document.body.dataset.tecladoVirtualActivo = '1';
    this._colocarCaretFalso();

    // El panel puede encoger el modal/contenedor que se esté mostrando
    // (ver responsive.css, --keyboard-offset); si el input estaba cerca
    // del final de un formulario largo con scroll (p.ej. revisión de
    // ticket), puede quedar oculto bajo el nuevo borde inferior. Se
    // difiere al siguiente frame para que el reflow del max-height ya
    // se haya aplicado antes de calcular qué hace falta desplazar.
    window.requestAnimationFrame(() => {
      this._reportarAltura();
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
    this._ocultarCaretFalso();

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

  /* Mide la altura REAL del panel visible (numérico o alfa) y la vuelca en
     las variables CSS que consume responsive.css/style.css para encoger las
     modales (--keyboard-offset/--keyboard-height) y decidir si la modal
     activa cuenta como "cubierta" (is-keyboard-open). Se llama no solo al
     abrir el panel, sino también en cada re-render de simple-keyboard
     (cambio de capa letras/símbolos/mayúsculas) y en resize/scroll: la
     altura de una capa de 5 filas (símbolos) no es la misma que la de una
     de 4 (letras), y medir una sola vez al abrir dejaba el offset corto o
     largo según qué capa estuviera activa en ese momento, encogiendo mal la
     modal o dejándola tapada por el teclado. */
  _reportarAltura() {
    if (!this.element || this.element.hidden) return;
    const alto = this.element.getBoundingClientRect().height;
    document.documentElement.style.setProperty('--keyboard-height', `${alto}px`);
    document.documentElement.style.setProperty('--keyboard-offset', `${alto}px`);
    document.body.classList.add('keyboard-open');
    const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some((modal) => !modal.hidden);
    document.body.classList.toggle('is-keyboard-open', !hayModalAbierto);
  }

  _manejarTecla(boton) {
    if (!this.activeInput) return;
    this._tecladoCustomOrigina = true;
    switch (boton) {
      case '{bksp}':
        this.backspace();
        break;
      case '{enter}':
        if (this._tipoActivo === 'numerico') this.commitEnter();
        else this.irAlSiguienteCampo();
        break;
      case '{shift}':
        this._shiftActivo = !this._shiftActivo;
        this._layoutNameAlfa = this._shiftActivo ? 'shift' : 'default';
        this.tecladoAlfa?.setOptions({ layoutName: this._layoutNameAlfa });
        break;
      case '{numbers}':
        this._layoutNameAlfa = 'symbols';
        this.tecladoAlfa?.setOptions({ layoutName: 'symbols' });
        break;
      case '{abc}':
        this._shiftActivo = false;
        this._layoutNameAlfa = 'default';
        this.tecladoAlfa?.setOptions({ layoutName: 'default' });
        break;
      case '{eye}':
        this._alternarVisibilidadPassword();
        break;
      case '{space}':
        this.insertChar(' ');
        break;
      default:
        this.insertChar(boton);
        // Mayúsculas de un solo toque: se desactiva tras la letra insertada,
        // igual que en los teclados nativos (no es un bloqueo tipo
        // caps-lock).
        if (this._shiftActivo) {
          this._shiftActivo = false;
          this._layoutNameAlfa = 'default';
          this.tecladoAlfa?.setOptions({ layoutName: 'default' });
        }
        break;
    }
    window.setTimeout(() => { this._tecladoCustomOrigina = false; }, 0);
  }

  _alternarVisibilidadPassword() {
    const el = this.activeInput;
    if (!el) return;
    const estabaOculta = el.type === 'password';
    el.type = estabaOculta ? 'text' : 'password';
    const icono = estabaOculta ? '🙈' : '👁';
    this.tecladoAlfa?.setOptions({ display: { ...DISPLAY_ALFA, '{eye}': icono } });
  }

  /* Equivalente al "Siguiente"/"Ir" de los teclados nativos en campos de
     texto: no valida (a diferencia de commitEnter(), pensado para el
     numérico con min/max) para no dar sorpresas de auto-submit; solo mueve
     el foco al siguiente input gestionado por este teclado dentro del
     mismo formulario, o cierra el panel si era el último. */
  irAlSiguienteCampo() {
    const el = this.activeInput;
    if (!el) return;
    const contenedor = el.form || document;
    const candidatos = Array.from(contenedor.querySelectorAll('input')).filter(
      (i) => this.marcados.has(i) && !i.disabled
    );
    const idx = candidatos.indexOf(el);
    const siguiente = idx >= 0 ? candidatos[idx + 1] : undefined;
    if (siguiente) {
      siguiente.focus();
    } else {
      el.dispatchEvent(new Event('change', { bubbles: true }));
      this._ocultarPanel();
      el.blur();
    }
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
    this._colocarCaretFalso();
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
    this._colocarCaretFalso();
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

  /* Caret falso: el input activo es readonly (ver _marcar) y no dibuja
     caret nativo en ningún navegador aunque su valor se siga modificando
     por JS. Esta barra sustituye visualmente a ese caret, posicionada sobre
     el ancho de texto medido con un <canvas> oculto (misma fuente/tamaño
     que el input real). */
  _colocarCaretFalso() {
    const el = this.activeInput;
    if (!el || typeof el.getBoundingClientRect !== 'function') return;
    if (!this._caretEl) {
      this._caretEl = document.createElement('div');
      this._caretEl.className = 'teclado-virtual-caret-fake';
      this._caretEl.hidden = true;
      document.body.appendChild(this._caretEl);
    }
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      this._ocultarCaretFalso();
      return;
    }
    const pos = el.selectionStart ?? el.value.length;
    const textoHastaCaret = el.value.slice(0, pos);
    const anchoTexto = this._medirAnchoTexto(el, textoHastaCaret);
    const estilos = window.getComputedStyle(el);
    const padL = parseFloat(estilos.paddingLeft) || 0;
    const borderL = parseFloat(estilos.borderLeftWidth) || 0;
    this._caretEl.style.left = `${rect.left + borderL + padL + anchoTexto}px`;
    this._caretEl.style.top = `${rect.top + (parseFloat(estilos.paddingTop) || 0)}px`;
    const altoLinea = parseFloat(estilos.lineHeight);
    this._caretEl.style.height = `${Number.isFinite(altoLinea) ? altoLinea : rect.height * 0.6}px`;
    this._caretEl.hidden = false;
  }

  _ocultarCaretFalso() {
    if (this._caretEl) this._caretEl.hidden = true;
  }

  _medirAnchoTexto(el, texto) {
    if (!this._canvasMedida) this._canvasMedida = document.createElement('canvas');
    const ctx = this._canvasMedida.getContext && this._canvasMedida.getContext('2d');
    if (!ctx) return 0;
    const estilos = window.getComputedStyle(el);
    ctx.font = `${estilos.fontStyle} ${estilos.fontWeight} ${estilos.fontSize} ${estilos.fontFamily}`;
    return ctx.measureText(texto).width;
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
