/**
 * TECLADO VIRTUAL PROPIO
 * Sustituye al teclado nativo de iOS/Android, solo en móvil táctil:
 * - Fase 1: inputs numéricos (type="number" o inputmode="numeric"/"decimal").
 * - Fase 2: inputs de texto libre (text/email/password/tel/search), con
 *   layout QWERTY español, mayúsculas, capa de símbolos/acentos y mostrar/
 *   ocultar contraseña.
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
    this._modo = 'letras'; // 'letras' | 'simbolos' (capa del panel alfanumérico)
    this._shiftActivo = false;
    this._observer = null;
    this._sincronizarMarcadoDiferido = this._sincronizarMarcadoDiferido.bind(this);
    this._onDocFocusIn = this._onDocFocusIn.bind(this);
    this._onDocKeyDown = this._onDocKeyDown.bind(this);
    this._onVentanaPierdeFoco = this._onVentanaPierdeFoco.bind(this);
    this._onCambioVisibilidad = this._onCambioVisibilidad.bind(this);
    this._onDocPointerDownFuera = this._onDocPointerDownFuera.bind(this);
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

  _crearFila(contenedor, teclas, { crearBoton } = {}) {
    const filaEl = document.createElement('div');
    filaEl.className = 'teclado-virtual-fila';
    teclas.forEach((tecla) => {
      const btn = (crearBoton && crearBoton(tecla)) || this._crearBotonSimple(tecla);
      filaEl.appendChild(btn);
    });
    contenedor.appendChild(filaEl);
    return filaEl;
  }

  _crearBotonSimple(tecla) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.tabIndex = -1;
    btn.className = 'teclado-virtual-tecla';
    if (tecla === '⌫') btn.classList.add('teclado-virtual-tecla--borrar');
    btn.textContent = tecla;
    btn.dataset.tecla = tecla;
    return btn;
  }

  _crearBotonLetra(min) {
    const btn = this._crearBotonSimple(min);
    btn.dataset.letraMin = min;
    btn.dataset.letraMay = min.toUpperCase();
    return btn;
  }

  _crearPanelNumerico() {
    const panel = document.createElement('div');
    panel.className = 'teclado-virtual-panel';

    const filas = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      [',', '0', '⌫'],
    ];
    filas.forEach((fila) => this._crearFila(panel, fila));

    const filaAcciones = document.createElement('div');
    filaAcciones.className = 'teclado-virtual-fila';
    const btnIntro = document.createElement('button');
    btnIntro.type = 'button';
    btnIntro.tabIndex = -1;
    btnIntro.className = 'teclado-virtual-tecla teclado-virtual-tecla--intro';
    btnIntro.textContent = 'Intro';
    btnIntro.dataset.tecla = 'Intro';
    filaAcciones.appendChild(btnIntro);
    panel.appendChild(filaAcciones);

    return panel;
  }

  _crearPanelAlfa() {
    const panel = document.createElement('div');
    panel.className = 'teclado-virtual-panel';

    // Capa "letras": 3 filas QWERTY español (con ñ).
    this._grupoLetras = document.createElement('div');
    this._grupoLetras.className = 'teclado-virtual-grupo';
    ['qwertyuiop', 'asdfghjklñ', 'zxcvbnm'].forEach((fila) => {
      this._crearFila(this._grupoLetras, fila.split(''), {
        crearBoton: (letra) => this._crearBotonLetra(letra),
      });
    });
    panel.appendChild(this._grupoLetras);

    // Capa "símbolos": dígitos + acentos y puntuación menos frecuente. Antes
    // los dígitos eran una fila aparte, siempre visible incluso en la capa
    // de letras; ahora viven aquí, ocultos hasta que se pulsa 123, igual que
    // el resto de esta capa. Sin teclas muertas (mucho más simple de
    // implementar) — cada tecla inserta ya el carácter final, suficiente
    // para nombres de producto en español.
    this._grupoSimbolos = document.createElement('div');
    this._grupoSimbolos.className = 'teclado-virtual-grupo';
    this._grupoSimbolos.hidden = true;
    this._crearFila(this._grupoSimbolos, ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']);
    this._crearFila(this._grupoSimbolos, ['¿', '¡', '/', ':', ';', '(', ')']);
    this._crearFila(this._grupoSimbolos, ['á', 'é', 'í', 'ó', 'ú']);
    panel.appendChild(this._grupoSimbolos);

    // Fila de símbolos comunes + mayúsculas + borrar, siempre visible en
    // ambas capas (independiente del toggle 123/ABC).
    this._crearFila(panel, ['⇧', '@', '.', ',', '-', '_', '⌫'], {
      crearBoton: (tecla) => {
        if (tecla === '⇧') {
          this._btnShift = this._crearBotonSimple(tecla);
          this._btnShift.classList.add('teclado-virtual-tecla--mayus');
          return this._btnShift;
        }
        return this._crearBotonSimple(tecla);
      },
    });

    // Fila inferior: 123/ABC, mostrar/ocultar contraseña (oculto por
    // defecto), espaciadora e Intro.
    const filaInferior = document.createElement('div');
    filaInferior.className = 'teclado-virtual-fila';

    this._btnModo = document.createElement('button');
    this._btnModo.type = 'button';
    this._btnModo.tabIndex = -1;
    this._btnModo.className = 'teclado-virtual-tecla teclado-virtual-tecla--alterna';
    this._btnModo.textContent = '123';
    this._btnModo.dataset.tecla = '123';
    filaInferior.appendChild(this._btnModo);

    this._btnPassword = document.createElement('button');
    this._btnPassword.type = 'button';
    this._btnPassword.tabIndex = -1;
    this._btnPassword.className = 'teclado-virtual-tecla';
    this._btnPassword.textContent = '👁';
    this._btnPassword.dataset.tecla = '👁';
    this._btnPassword.hidden = true;
    filaInferior.appendChild(this._btnPassword);

    const btnEspacio = document.createElement('button');
    btnEspacio.type = 'button';
    btnEspacio.tabIndex = -1;
    btnEspacio.className = 'teclado-virtual-tecla teclado-virtual-tecla--espacio';
    btnEspacio.textContent = '␣';
    btnEspacio.dataset.tecla = ' ';
    filaInferior.appendChild(btnEspacio);

    const btnIntro = document.createElement('button');
    btnIntro.type = 'button';
    btnIntro.tabIndex = -1;
    btnIntro.className = 'teclado-virtual-tecla teclado-virtual-tecla--intro';
    btnIntro.textContent = 'Intro';
    btnIntro.dataset.tecla = 'Intro';
    filaInferior.appendChild(btnIntro);

    panel.appendChild(filaInferior);

    return panel;
  }

  _crearDom() {
    if (this.element) return;
    const el = document.createElement('div');
    el.id = 'tecladoVirtual';
    el.className = 'teclado-virtual';
    el.hidden = true;
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'Teclado numérico');

    this.panelNumerico = this._crearPanelNumerico();
    this.panelAlfa = this._crearPanelAlfa();
    this.panelAlfa.hidden = true;
    el.appendChild(this.panelNumerico);
    el.appendChild(this.panelAlfa);

    // preventDefault() en 'touchstart'/'pointerdown' evita que tocar una
    // tecla dispare el comportamiento por defecto del navegador sobre ella
    // (incluido el intento de robar el foco a un <button>, aunque tenga
    // tabIndex=-1). No es la defensa principal contra la pérdida de foco
    // -esa vive ahora en _onDocFocusIn(), ver más abajo-, pero evita
    // parpadeos visuales y el resaltado de "tap" nativo del navegador.
    el.addEventListener('touchstart', (e) => {
      if (e.target.closest('button[data-tecla]')) e.preventDefault();
    }, { passive: false });

    el.addEventListener('pointerdown', (e) => {
      const btn = e.target.closest('button[data-tecla]');
      if (!btn) return;
      e.preventDefault();
      this._manejarTecla(btn.dataset.tecla);
    });

    document.body.appendChild(el);
    this.element = el;
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
    // Foco dentro del propio panel (no debería ocurrir con tabIndex=-1,
    // pero por si acaso): no hacer nada.
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
    this._modo = 'letras';
    this._shiftActivo = false;
    this._actualizarMayusculas();
    this._actualizarModo();

    const esNumerico = this._tipoActivo === 'numerico';
    this.panelNumerico.hidden = !esNumerico;
    this.panelAlfa.hidden = esNumerico;
    this.element.setAttribute('aria-label', esNumerico ? 'Teclado numérico' : 'Teclado alfanumérico');

    const esPassword = this._esPasswordPorInput.get(inputEl) === true;
    if (this._btnPassword) {
      this._btnPassword.hidden = !esPassword;
      if (esPassword) {
        inputEl.type = 'password';
        this._btnPassword.textContent = '👁';
        this._btnPassword.dataset.tecla = '👁';
      }
    }

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
      if (this._tipoActivo === 'numerico') this.commitEnter();
      else this.irAlSiguienteCampo();
    } else if (tecla === '⇧') {
      this._shiftActivo = !this._shiftActivo;
      this._actualizarMayusculas();
    } else if (tecla === '123' || tecla === 'ABC') {
      this._modo = this._modo === 'letras' ? 'simbolos' : 'letras';
      this._actualizarModo();
    } else if (tecla === '👁' || tecla === '🙈') {
      this._alternarVisibilidadPassword();
    } else {
      this.insertChar(tecla);
      // Mayúsculas de un solo toque: se desactiva tras la letra insertada,
      // igual que en los teclados nativos (no es un bloqueo tipo caps-lock).
      if (this._shiftActivo) {
        this._shiftActivo = false;
        this._actualizarMayusculas();
      }
    }
    window.setTimeout(() => { this._tecladoCustomOrigina = false; }, 0);
  }

  /* Actualiza mayúsculas/minúsculas de las teclas de letra sin recrear el
     DOM (solo cambia textContent/dataset.tecla de los botones existentes). */
  _actualizarMayusculas() {
    if (!this.panelAlfa) return;
    this.panelAlfa.querySelectorAll('button[data-letra-min]').forEach((btn) => {
      const valor = this._shiftActivo ? btn.dataset.letraMay : btn.dataset.letraMin;
      btn.textContent = valor;
      btn.dataset.tecla = valor;
    });
    if (this._btnShift) {
      this._btnShift.classList.toggle('teclado-virtual-tecla--activa', this._shiftActivo);
    }
  }

  /* Alterna entre la capa de letras (QWERTY) y la de símbolos/acentos,
     ambas ya construidas en el DOM (solo se hace toggle de hidden). */
  _actualizarModo() {
    if (!this._grupoLetras || !this._grupoSimbolos) return;
    const enSimbolos = this._modo === 'simbolos';
    this._grupoLetras.hidden = enSimbolos;
    this._grupoSimbolos.hidden = !enSimbolos;
    if (this._btnModo) {
      const etiqueta = enSimbolos ? 'ABC' : '123';
      this._btnModo.textContent = etiqueta;
      this._btnModo.dataset.tecla = etiqueta;
    }
  }

  _alternarVisibilidadPassword() {
    const el = this.activeInput;
    if (!el || !this._btnPassword) return;
    const estabaOculta = el.type === 'password';
    el.type = estabaOculta ? 'text' : 'password';
    const icono = estabaOculta ? '🙈' : '👁';
    this._btnPassword.textContent = icono;
    this._btnPassword.dataset.tecla = icono;
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
