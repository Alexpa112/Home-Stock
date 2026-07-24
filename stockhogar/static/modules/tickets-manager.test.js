const { TicketsManager } = require('./tickets-manager.js');

const FIXTURE = `
  <button id="btnEscanearTicket"></button>
  <div id="modalTicket" class="modal-fondo" hidden>
    <div class="modal"></div>
  </div>
  <div id="ticketPasoFoto"></div>
  <div id="ticketCargando" hidden></div>
  <div id="ticketPasoRevision" hidden></div>
  <input id="ticketArchivo" type="file">
  <div id="ticketDropzone"></div>
  <div id="ticketPreviewWrap" hidden></div>
  <img id="ticketPreview" src="">
  <button id="btnCambiarFotoTicket"></button>
  <button id="btnVolverFotoTicket" hidden></button>
  <span id="ticketDot1"></span>
  <span id="ticketDot2"></span>
  <div id="ticketResumen"></div>
  <button id="btnAnalizarTicket"></button>
  <button id="btnCancelarTicket"></button>
  <button id="btnAnadirLineaTicket"></button>
  <button id="btnConfirmarTicket" hidden></button>
  <ul id="ticketItems"></ul>
  <div id="ticketAdvertencias"></div>
`;

function montarFixture() {
  document.body.innerHTML = FIXTURE;
}

function crearManager(opciones = {}) {
  return new TicketsManager({
    fetchImpl: jest.fn(),
    toast: { error: jest.fn() },
    escapeHtml: (texto) => String(texto)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;'),
    renderIcon: (icono) => `<svg data-icon="${icono || ''}"></svg>`,
    populateCategorySelect: (select, seleccionada) => {
      select.innerHTML = '<option value="Otros">Otros</option><option value="Panadería">Panadería</option>';
      if (seleccionada) select.value = seleccionada;
    },
    getProducts: () => [{ id: 7, nombre: 'Leche', cantidad: 3, unidad: 'ud' }],
    onConfirmed: jest.fn().mockResolvedValue(undefined),
    habilitarBottomSheet: jest.fn(),
    ...opciones,
  });
}

beforeEach(() => {
  montarFixture();
  jest.clearAllMocks();
});

afterEach(() => {
  document.body.innerHTML = '';
});

describe('TicketsManager', () => {
  test('open() reinicia el modal y vuelve al paso foto', () => {
    const manager = crearManager();
    manager.ticketItemsEl.innerHTML = '<li>viejo</li>';
    manager.ticketAdvertenciasEl.innerHTML = '<p>alerta</p>';
    manager.ticketAdvertenciasEl.hidden = false;
    manager.ticketPasoRevision.hidden = false;

    manager.open();

    expect(manager.modalFondo.hidden).toBe(false);
    expect(manager.ticketItemsEl.innerHTML).toBe('');
    expect(manager.ticketAdvertenciasEl.hidden).toBe(true);
    expect(manager.ticketPasoFoto.hidden).toBe(false);
    expect(manager.ticketPasoRevision.hidden).toBe(true);
    expect(manager.btnConfirmarTicket.hidden).toBe(true);
  });

  test('crearFilaTicket() oculta la categoría cuando se vincula a un producto existente', () => {
    const manager = crearManager();
    const fila = manager.crearFilaTicket({ nombre: 'Leche', cantidad: 1, unidad: 'ud', confianza_match: 0.9 });
    const selectVincular = fila.querySelector('[name="vincular"]');
    const campoCategoria = fila.querySelector('[data-campo-categoria]');

    expect(selectVincular.value).toBe('7');
    expect(campoCategoria.hidden).toBe(true);

    selectVincular.value = 'nuevo';
    selectVincular.dispatchEvent(new Event('change'));
    expect(campoCategoria.hidden).toBe(false);
  });

  test('analizarTicket() rellena la revisión y muestra advertencias', async () => {
    const fetchImpl = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          { nombre: 'Leche', cantidad: 2, unidad: 'ud', confianza_match: 0.92 },
          { nombre: 'Pan', cantidad: 1, unidad: 'ud', confianza_match: 0.35 },
        ],
        advertencias: [{ mensaje: 'Revisa Pan' }],
      }),
    });
    const manager = crearManager({ fetchImpl });
    const archivo = new File(['ticket'], 'ticket.jpg', { type: 'image/jpeg' });
    Object.defineProperty(manager.ticketArchivo, 'files', {
      configurable: true,
      value: [archivo],
    });

    await manager.analizarTicket();

    expect(fetchImpl).toHaveBeenCalledWith('/api/tickets/analizar', expect.objectContaining({ method: 'POST' }));
    expect(manager.ticketPasoRevision.hidden).toBe(false);
    expect(manager.ticketItemsEl.querySelectorAll('.ticket-item')).toHaveLength(2);
    expect(manager.ticketResumenEl.textContent).toContain('2 artículos detectados');
    expect(manager.ticketAdvertenciasEl.hidden).toBe(false);
    expect(manager.ticketAdvertenciasEl.textContent).toContain('Revisa Pan');
  });

  test('confirmarTicket() envía items normalizados y refresca datos', async () => {
    const fetchImpl = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    const onConfirmed = jest.fn().mockResolvedValue(undefined);
    const manager = crearManager({ fetchImpl, onConfirmed });

    const nuevaFila = manager.crearFilaTicket({ nombre: 'Pan', cantidad: 2, unidad: 'ud', confianza_match: null });
    nuevaFila.querySelector('[name="categoria"]').value = 'Panadería';
    manager.ticketItemsEl.appendChild(nuevaFila);

    const existente = manager.crearFilaTicket({ nombre: 'Leche', cantidad: 1, unidad: 'ud', confianza_match: 0.95 });
    manager.ticketItemsEl.appendChild(existente);

    await manager.confirmarTicket();

    expect(fetchImpl).toHaveBeenCalledWith('/api/tickets/confirmar', expect.objectContaining({ method: 'POST' }));
    const payload = JSON.parse(fetchImpl.mock.calls[0][1].body);
    expect(payload).toEqual({
      items: [
        { nombre: 'Pan', cantidad: 2, unidad: 'ud', categoria: 'Panadería' },
        { nombre: 'Leche', cantidad: 1, unidad: 'ud', producto_id: 7 },
      ],
    });
    expect(onConfirmed).toHaveBeenCalledTimes(1);
    expect(manager.modalFondo.hidden).toBe(true);
  });
});
