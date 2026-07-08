/**
 * UIManager - Gestión de temas, modales y visualización
 * Patrón: Manager singleton
 * Responsabilidad: Tema, estado de modales, visualización
 */
class UIManager {
  constructor(domManager) {
    this.dom = domManager;

    this.tema = this.obtenerTemaGuardado();
    this.modalesAbiertos = new Set();
    this.listeners = new Set();

    this.inicializar();
  }

  // ===== INICIALIZACIÓN =====
  inicializar() {
    this.aplicarTema(this.tema);
    this.establecerObservadorModales();
    this.establecerObservadorViewport();
  }

  // ===== GESTIÓN DE TEMA =====
  obtenerTemaGuardado() {
    return localStorage.getItem('stockhogar-tema') || this.obtenerTemaSistema();
  }

  obtenerTemaSistema() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  obtenerTemaActual() {
    return document.documentElement.dataset.theme || this.obtenerTemaSistema();
  }

  toggleTema() {
    const nuevoTema = this.obtenerTemaActual() === 'dark' ? 'light' : 'dark';
    this.aplicarTema(nuevoTema);
  }

  aplicarTema(tema) {
    this.tema = tema;
    document.documentElement.dataset.theme = tema;
    localStorage.setItem('stockhogar-tema', tema);
    this.actualizarBotonTema();
    this.notificar('tema-cambiado', tema);
  }

  actualizarBotonTema() {
    const btnTema = this.dom.btnTema;
    if (btnTema) {
      btnTema.textContent = this.obtenerTemaActual() === 'dark' ? '☀️' : '🌙';
    }
  }

  // ===== GESTIÓN DE MODALES =====
  abrirModal(id) {
    const modal = this.dom.get(id);
    if (!modal) {
      console.warn(`Modal ${id} no encontrado`);
      return;
    }
    modal.hidden = false;
    this.modalesAbiertos.add(id);
    this.sincronizarEstadoModal();
    this.notificar('modal-abierto', id);
  }

  cerrarModal(id) {
    const modal = this.dom.get(id);
    if (!modal) {
      console.warn(`Modal ${id} no encontrado`);
      return;
    }
    modal.hidden = true;
    this.modalesAbiertos.delete(id);
    this.sincronizarEstadoModal();
    this.notificar('modal-cerrado', id);
  }

  cerrarTodosModales() {
    this.modalesAbiertos.forEach(id => this.cerrarModal(id));
  }

  sincronizarEstadoModal() {
    const hayModalesAbiertos = this.modalesAbiertos.size > 0;
    document.body.classList.toggle('modal-open', hayModalesAbiertos);
    document.documentElement.classList.toggle('modal-open', hayModalesAbiertos);
  }

  // ===== OBSERVADORES =====
  establecerObservadorModales() {
    const observer = new MutationObserver(() => {
      this.sincronizarEstadoModal();
    });
    observer.observe(document.documentElement, {
      subtree: true,
      attributes: true,
      attributeFilter: ['hidden'],
    });
  }

  establecerObservadorViewport() {
    if (!window.visualViewport) return;

    const ajustar = () => this.ajustarViewportMovil();
    window.visualViewport.addEventListener('resize', ajustar);
    window.visualViewport.addEventListener('scroll', ajustar);
    window.addEventListener('resize', ajustar);
    window.addEventListener('orientationchange', ajustar);
    document.addEventListener('focusin', (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.matches('input, select, textarea')) {
        window.setTimeout(() => {
          if (document.activeElement === target) {
            this.ajustarViewportMovil();
            target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
          }
        }, 120);
      }
    });
  }

  ajustarViewportMovil() {
    if (!window.visualViewport) {
      document.documentElement.style.setProperty('--keyboard-offset', '0px');
      document.body.classList.remove('is-keyboard-open');
      return;
    }

    const viewport = window.visualViewport;
    const offset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
    const offsetEfectivo = offset > 32 ? offset : 0;
    const hayModalesAbiertos = this.modalesAbiertos.size > 0;

    document.documentElement.style.setProperty('--keyboard-offset', `${offsetEfectivo}px`);
    document.body.classList.toggle('is-keyboard-open', offsetEfectivo > 0 && !hayModalesAbiertos);
    this.sincronizarEstadoModal();

    if (offsetEfectivo > 0 && !hayModalesAbiertos &&
        document.activeElement instanceof HTMLElement &&
        document.activeElement !== document.body) {
      window.requestAnimationFrame(() => {
        document.activeElement.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
      });
    }
  }

  // ===== RENDERIZADO =====
  render() {
    // UIManager no necesita renderizar mucho,
    // pero los métodos anteriores ya manejan la visualización
    // Esta función es un placeholder para consistencia con otros managers
    this.actualizarBotonTema();
    this.sincronizarEstadoModal();
  }

  // Helpers
  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  // ===== EVENT EMITTER =====
  suscribir(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notificar(evento, datos) {
    this.listeners.forEach(listener => {
      try {
        listener(evento, datos);
      } catch (error) {
        console.error(`Error en listener para ${evento}:`, error);
      }
    });
  }
}

// Crear instancia global
window.uiManager = new UIManager(window.DOM);
