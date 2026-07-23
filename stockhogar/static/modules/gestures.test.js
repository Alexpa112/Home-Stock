/**
 * Tests para agregarPulsacion(): pulsación corta (tap) vs. mantener pulsado
 * (long-press), y su interacción con el scroll táctil.
 *
 * Cubre la regresión detectada en auditoría: el long-press se disparaba
 * durante el scroll porque el temporizador solo se cancelaba en
 * pointerleave/pointercancel, no en pointermove.
 */
const { agregarPulsacion, UMBRAL_MOVIMIENTO_CANCELA_PULSACION } = require('./gestures.js');

afterEach(() => {
  document.body.innerHTML = '';
  jest.useRealTimers();
});

// jsdom no implementa PointerEvent; un Event con clientX/clientY asignados a
// mano es indistinguible para agregarPulsacion(), que solo lee esas props.
function dispararPointer(elemento, tipo, x, y) {
  const evento = new Event(tipo, { bubbles: true });
  evento.clientX = x;
  evento.clientY = y;
  elemento.dispatchEvent(evento);
}

describe('agregarPulsacion()', () => {
  let elemento;
  let alPulsarCorto;
  let alPulsarLargo;

  beforeEach(() => {
    elemento = document.createElement('div');
    document.body.appendChild(elemento);
    alPulsarCorto = jest.fn();
    alPulsarLargo = jest.fn();
  });

  test('una pulsación corta (pointerdown + pointerup rápido) llama a alPulsarCorto, no a alPulsarLargo', () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 480);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    dispararPointer(elemento, 'pointerup', 100, 100);

    expect(alPulsarCorto).toHaveBeenCalledTimes(1);
    expect(alPulsarLargo).not.toHaveBeenCalled();
  });

  test('mantener pulsado sin soltar durante la duración configurada llama a alPulsarLargo, no a alPulsarCorto', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    await new Promise((r) => setTimeout(r, 100));

    expect(alPulsarLargo).toHaveBeenCalledTimes(1);
    expect(alPulsarCorto).not.toHaveBeenCalled();
  });

  test('un desplazamiento (scroll) por encima del umbral cancela el long-press', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    dispararPointer(elemento, 'pointermove', 100, 100 + UMBRAL_MOVIMIENTO_CANCELA_PULSACION + 5);
    await new Promise((r) => setTimeout(r, 100));

    expect(alPulsarLargo).not.toHaveBeenCalled();
    expect(alPulsarCorto).not.toHaveBeenCalled();
  });

  test('un desplazamiento por debajo del umbral NO cancela el long-press (tolerancia a temblor del dedo)', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    dispararPointer(elemento, 'pointermove', 100, 100 + UMBRAL_MOVIMIENTO_CANCELA_PULSACION - 2);
    await new Promise((r) => setTimeout(r, 100));

    expect(alPulsarLargo).toHaveBeenCalledTimes(1);
  });

  test('pointerleave cancela el long-press (el dedo sale del elemento)', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    dispararPointer(elemento, 'pointerleave', 100, 100);
    await new Promise((r) => setTimeout(r, 100));

    expect(alPulsarLargo).not.toHaveBeenCalled();
    expect(alPulsarCorto).not.toHaveBeenCalled();
  });

  test('pointercancel cancela el long-press', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    dispararPointer(elemento, 'pointercancel', 100, 100);
    await new Promise((r) => setTimeout(r, 100));

    expect(alPulsarLargo).not.toHaveBeenCalled();
  });

  test('tras un long-press, soltar el puntero no dispara también alPulsarCorto', async () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 50);

    dispararPointer(elemento, 'pointerdown', 100, 100);
    await new Promise((r) => setTimeout(r, 100));
    dispararPointer(elemento, 'pointerup', 100, 100);

    expect(alPulsarLargo).toHaveBeenCalledTimes(1);
    expect(alPulsarCorto).not.toHaveBeenCalled();
  });

  test('contextmenu (menú nativo de long-press) se previene', () => {
    agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, 480);
    const evento = new Event('contextmenu', { bubbles: true, cancelable: true });
    elemento.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(true);
  });
});
