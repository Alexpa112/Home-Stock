/**
 * HELPERS - Funciones utilitarias globales
 * Responsabilidad: Utils para todo el proyecto
 */

// ===== VALIDACIÓN =====
function normalizarTexto(texto) {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim();
}

// ===== COLORES =====
function ajustarColor(hex, delta) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.max(0, Math.min(255, (num >> 16) + delta));
  const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + delta));
  const b = Math.max(0, Math.min(255, (num & 0x0000FF) + delta));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

// ===== DOM GESTURES =====
function agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, duracion = 480) {
  let timeoutId;

  function empezar() {
    timeoutId = setTimeout(() => {
      alPulsarLargo?.();
    }, duracion);
  }

  function cancelar() {
    clearTimeout(timeoutId);
  }

  function terminar() {
    if (timeoutId) {
      clearTimeout(timeoutId);
      alPulsarCorto?.();
    }
  }

  elemento.addEventListener('mousedown', empezar);
  elemento.addEventListener('touchstart', empezar);
  elemento.addEventListener('mouseup', terminar);
  elemento.addEventListener('touchend', terminar);
  elemento.addEventListener('mouseleave', cancelar);
  elemento.addEventListener('touchcancel', cancelar);
}

// ===== MODAL STATE =====
function sincronizarEstadoModal() {
  const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some(
    (modal) => !modal.hidden
  );
  document.body.classList.toggle('modal-open', hayModalAbierto);
  document.documentElement.classList.toggle('modal-open', hayModalAbierto);
}

// Observer para cambios en modales
const observerModales = new MutationObserver(() => {
  sincronizarEstadoModal();
});

// Iniciar observer cuando DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const modales = document.querySelectorAll('.modal-fondo');
    modales.forEach(modal => {
      observerModales.observe(modal, { attributes: true, attributeFilter: ['hidden'] });
    });
  });
} else {
  const modales = document.querySelectorAll('.modal-fondo');
  modales.forEach(modal => {
    observerModales.observe(modal, { attributes: true, attributeFilter: ['hidden'] });
  });
}

// ===== VIEWPORT MÓVIL =====
function ajustarViewportMovil() {
  const handleViewportChange = () => {
    document.body.classList.remove('is-keyboard-open');

    const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some(
      (modal) => !modal.hidden
    );

    const offsetEfectivo = window.innerHeight - document.documentElement.clientHeight;
    document.body.classList.toggle('is-keyboard-open', offsetEfectivo > 0 && !hayModalAbierto);
  };

  window.addEventListener('resize', handleViewportChange);
  window.addEventListener('orientationchange', handleViewportChange);
}

// ===== CIERRE SEGURO DE MODALES =====
function habilitarCierreSeguro(fondo, alCerrar) {
  fondo?.addEventListener('click', (e) => {
    if (e.target === fondo) {
      alCerrar?.();
    }
  });
}

// ===== DRAG DOWN PARA CERRAR =====
function habilitarDragDown(modal, alCerrar) {
  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  modal?.addEventListener('touchstart', (e) => {
    startY = e.touches[0].clientY;
    currentY = startY;
    isDragging = true;
  });

  modal?.addEventListener('touchmove', (e) => {
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
    const diff = currentY - startY;
    if (diff > 0) {
      modal.style.transform = `translateY(${diff}px)`;
    }
  });

  modal?.addEventListener('touchend', () => {
    if (!isDragging) return;
    const diff = currentY - startY;
    isDragging = false;

    if (diff > 80) {
      modal.style.transform = '';
      alCerrar?.();
    } else {
      modal.style.transform = '';
    }
  });
}

// Exportar para uso global
window.normalizarTexto = normalizarTexto;
window.ajustarColor = ajustarColor;
window.agregarPulsacion = agregarPulsacion;
window.sincronizarEstadoModal = sincronizarEstadoModal;
window.ajustarViewportMovil = ajustarViewportMovil;
window.habilitarCierreSeguro = habilitarCierreSeguro;
window.habilitarDragDown = habilitarDragDown;
