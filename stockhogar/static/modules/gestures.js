/**
 * Gestos táctiles/ratón unificados: pulsación corta vs. mantener pulsado.
 * Extraído de app.js para poder testearlo de forma aislada (ver
 * gestures.test.js).
 */

// Pulsacion corta vs. mantener pulsado, unificando raton y tactil.
const UMBRAL_MOVIMIENTO_CANCELA_PULSACION = 10; // px

function agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, duracion = 480) {
  let temporizador = null;
  let fueLarga = false;
  let inicioX = 0;
  let inicioY = 0;
  let ultimoPointerType = null;

  function empezar(e) {
    fueLarga = false;
    inicioX = e.clientX;
    inicioY = e.clientY;
    ultimoPointerType = e.pointerType;
    temporizador = setTimeout(() => {
      fueLarga = true;
      if (navigator.vibrate) navigator.vibrate(15);
      alPulsarLargo();
    }, duracion);
  }
  function cancelar() {
    clearTimeout(temporizador);
  }
  function mover(e) {
    const distancia = Math.hypot(e.clientX - inicioX, e.clientY - inicioY);
    if (distancia > UMBRAL_MOVIMIENTO_CANCELA_PULSACION) cancelar();
  }
  function terminar() {
    clearTimeout(temporizador);
    if (!fueLarga) alPulsarCorto();
  }

  elemento.addEventListener("pointerdown", empezar);
  elemento.addEventListener("pointermove", mover);
  elemento.addEventListener("pointerup", terminar);
  elemento.addEventListener("pointerleave", cancelar);
  elemento.addEventListener("pointercancel", cancelar);
  // Solo se previene el menu contextual nativo para el long-press tactil/pen
  // (copiar/compartir de iOS/Android); en desktop con raton, el clic derecho
  // debe seguir abriendo el menu contextual normal del navegador.
  elemento.addEventListener("contextmenu", (e) => {
    if (ultimoPointerType === "touch" || ultimoPointerType === "pen") {
      e.preventDefault();
    }
  });
}

if (typeof module === 'undefined') {
  window.Gestures = {
    agregarPulsacion,
    UMBRAL_MOVIMIENTO_CANCELA_PULSACION,
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    agregarPulsacion,
    UMBRAL_MOVIMIENTO_CANCELA_PULSACION,
  };
}
