/**
 * Tests para DrawerListasManager y CrearListaModal
 */

// drawer-listas.js asume que FormModal, ValidatedInput, FormBuilder y Toast
// existen como globales (así se cargan en el navegador vía <script>). En
// tests los inyectamos nosotros antes de requerir el módulo.
const { FormModal, ValidatedInput } = require('./ui-components.js');
const FormBuilder = require('./form-builder.js');

global.FormModal = FormModal;
global.ValidatedInput = ValidatedInput;
global.FormBuilder = FormBuilder;

const { DrawerListasManager, CrearListaModal } = require('./drawer-listas.js');

const FIXTURE = `
  <span id="listaActualNombre">Casa</span>

  <button id="listaActualBtn"></button>
  <button id="btnCambiarLista"></button>

  <div id="modalMisListas" class="modal-fondo" hidden>
    <div class="modal">
      <button id="btnCerrarMisListas"></button>
      <button id="btnEditarMisListas">Editar</button>
      <button id="btnCrearNuevaLista"></button>
      <div id="listaListas"></div>
    </div>
  </div>

  <div id="modalEditarLista" class="modal-fondo" hidden>
    <div class="modal">
      <form id="formEditarLista">
        <input id="editarListaNombre">
        <input id="editarListaColor" type="color">
      </form>
      <button id="btnEliminarLista"></button>
      <button id="btnEditarNombreImagen"></button>
      <button id="btnOrdenando"></button>
      <button id="btnRegion"></button>
      <button id="btnGestionarMiembros"></button>
      <button id="btnSalirLista"></button>
      <div id="colorPreview"></div>
      <div id="previewLista"></div>
    </div>
  </div>

  <div id="modalNombreImagen" style="display:none">
    <div class="modal">
      <input id="inputNombreLista">
      <input id="inputColorLista" type="color">
      <input id="inputIconoLista" type="hidden">
      <span id="iconoSeleccionadoLista"></span>
      <div id="previewColorLista"></div>
      <button id="btnSeleccionarIconoLista"></button>
    </div>
  </div>

  <div id="modalOrdenando" hidden><div class="modal"></div></div>
  <div id="modalRegion" hidden><div class="modal"></div></div>

  <div id="seccionMiembros" style="display:none">
    <div id="listaMiembros"></div>
    <div id="miembrosError" hidden></div>
    <div id="miembrosExito" hidden></div>

    <button id="tabPorUsuario" style=""></button>
    <button id="tabPorEmail" style=""></button>
    <button id="tabPorEnlace" style=""></button>
    <div id="panelUsuario" style=""></div>
    <div id="panelEmail" style=""></div>
    <div id="panelEnlace" style=""></div>

    <input id="buscarUsuario">
    <div id="resultadosBusqueda"></div>
    <form id="formCompartirPorUsuario"></form>
    <select id="nivelPermisoUsuario"><option value="editar">editar</option></select>

    <form id="formCompartirPorEmail"></form>
    <input id="emailDestino">
    <select id="nivelPermisoEmail"><option value="editar">editar</option></select>

    <button id="btnGenerarEnlace"></button>
    <select id="nivelPermisoEnlace"><option value="editar">editar</option></select>
    <button id="btnCopiarEnlace"></button>
    <input id="enlaceInvitacionInput">
    <div id="modalEnlaceInvitacion" style="display:none"></div>

    <button id="btnCompartirWhatsApp"></button>
    <input id="inputTelefonoWhatsApp">
  </div>

  <div id="modalCrearLista" class="modal-fondo" hidden>
    <div class="modal">
      <button id="btnCerrarCrearLista"></button>
      <div class="modal-content">
        <form id="formCrearLista"></form>
      </div>
      <button id="btnCrearListaSubmit" type="button"></button>
    </div>
  </div>
`;

function montarFixture() {
  document.body.innerHTML = FIXTURE;
}

function mockFetchOnce(ok, data, status = ok ? 200 : 400) {
  global.fetch.mockResolvedValueOnce({
    ok,
    status,
    json: async () => data,
  });
}

// El constructor de DrawerListasManager dispara automáticamente cargarListas()
// (fetch real). Por defecto lo sustituimos por un no-op para que el resto de
// tests controlen manager.listas a mano sin condiciones de carrera con fetch;
// los tests que sí quieren probar la carga real restauran el spy.
let cargarListasSpy;

beforeEach(() => {
  montarFixture();
  global.fetch = jest.fn();
  global.Toast = { error: jest.fn(), success: jest.fn(), info: jest.fn() };
  global.confirm = jest.fn(() => true);
  document.execCommand = jest.fn();
  window.open = jest.fn();
  Object.defineProperty(window, 'location', {
    configurable: true,
    writable: true,
    value: { ...window.location, reload: jest.fn() },
  });
  global.location = window.location; // el código fuente usa `location` a secas
  localStorage.clear();
  cargarListasSpy = jest.spyOn(DrawerListasManager.prototype, 'cargarListas').mockResolvedValue(undefined);
});

afterEach(() => {
  cargarListasSpy.mockRestore();
  jest.clearAllMocks();
  jest.useRealTimers();
});

describe('DrawerListasManager', () => {
  describe('cargarListas() (comportamiento real)', () => {
    beforeEach(() => cargarListasSpy.mockRestore());

    test('combina propias y compartidas, e identifica la lista actual por nombre', async () => {
      mockFetchOnce(true, {
        propias: [{ id: 1, nombre: 'Casa', color: '#111' }],
        compartidas: [{ id: 2, nombre: 'Oficina', color: '#222' }],
      });

      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listas).toHaveLength(2);
      expect(manager.listaActualId).toBe(1); // "Casa" coincide con #listaActualNombre
    });

    test('deja listas vacías si la respuesta no es OK', async () => {
      mockFetchOnce(false, {}, 500);

      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listas).toEqual([]);
    });

    test('deja listas vacías si fetch lanza una excepción', async () => {
      global.fetch.mockRejectedValueOnce(new Error('network'));

      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listas).toEqual([]);
    });
  });

  describe('renderizarListas() (comportamiento real)', () => {
    beforeEach(() => cargarListasSpy.mockRestore());

    test('muestra un mensaje si no hay listas', async () => {
      mockFetchOnce(true, { propias: [], compartidas: [] });
      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listaListasEl.textContent).toContain('Sin listas aún');
    });

    test('crea una tarjeta por cada lista', async () => {
      mockFetchOnce(true, {
        propias: [{ id: 1, nombre: 'Casa' }, { id: 2, nombre: 'Oficina' }],
        compartidas: [],
      });
      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listaListasEl.querySelectorAll('.tarjeta-lista')).toHaveLength(2);
    });

    test('escapa el nombre de la lista contra HTML', async () => {
      mockFetchOnce(true, { propias: [{ id: 1, nombre: '<img src=x onerror=alert(1)>' }], compartidas: [] });
      const manager = new DrawerListasManager();
      await manager.cargarListas();

      expect(manager.listaListasEl.querySelector('script, img')).toBeNull();
      expect(manager.listaListasEl.textContent).toContain('<img');
    });
  });

  describe('clic en una tarjeta de lista', () => {
    beforeEach(() => cargarListasSpy.mockRestore());

    async function crearManagerConUnaLista() {
      mockFetchOnce(true, { propias: [{ id: 7, nombre: 'Vacaciones', icono: 'h-sun' }], compartidas: [] });
      const manager = new DrawerListasManager();
      await manager.cargarListas();
      return manager;
    }

    test('en modo normal, cambia de lista', async () => {
      const manager = await crearManagerConUnaLista();
      window.cambiarLista = jest.fn().mockResolvedValue();
      const tarjeta = manager.listaListasEl.querySelector('.tarjeta-lista');

      tarjeta.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();

      expect(window.cambiarLista).toHaveBeenCalledWith(7);
      expect(manager.listaActualId).toBe(7);
    });

    test('en modo edición, abre los ajustes de esa lista en vez de cambiar', async () => {
      const manager = await crearManagerConUnaLista();
      window.cambiarLista = jest.fn();
      manager.modoEdicion = true;
      const tarjeta = manager.listaListasEl.querySelector('.tarjeta-lista');

      tarjeta.dispatchEvent(new MouseEvent('click', { bubbles: true }));

      expect(window.cambiarLista).not.toHaveBeenCalled();
      expect(manager.modalEditar.hidden).toBe(false);
      expect(manager.listaEditandoId).toBe(7);
    });

    test('el botón ⚙️ siempre abre ajustes, incluso en modo normal', async () => {
      const manager = await crearManagerConUnaLista();
      window.cambiarLista = jest.fn();
      const btnEditar = manager.listaListasEl.querySelector('.btn-editar-tarjeta');

      btnEditar.dispatchEvent(new MouseEvent('click', { bubbles: true }));

      expect(window.cambiarLista).not.toHaveBeenCalled();
      expect(manager.listaEditandoId).toBe(7);
    });
  });

  describe('abrirModal() / cerrarModal()', () => {
    test('abrirModal() muestra el modal y recarga las listas', () => {
      const manager = new DrawerListasManager();
      const llamadasPrevias = cargarListasSpy.mock.calls.length;

      manager.abrirModal();

      expect(manager.estaAbierto).toBe(true);
      expect(manager.modal.hidden).toBe(false);
      expect(document.body.classList.contains('modal-open')).toBe(true);
      expect(cargarListasSpy.mock.calls.length).toBeGreaterThan(llamadasPrevias);
    });

    test('abrirModal() no hace nada si ya está abierto', () => {
      const manager = new DrawerListasManager();
      manager.estaAbierto = true;
      const llamadasPrevias = cargarListasSpy.mock.calls.length;

      manager.abrirModal();

      expect(cargarListasSpy.mock.calls.length).toBe(llamadasPrevias);
    });

    test('cerrarModal() oculta el modal', () => {
      const manager = new DrawerListasManager();
      manager.estaAbierto = true;
      manager.modal.hidden = false;
      document.body.classList.add('modal-open');

      manager.cerrarModal();

      expect(manager.estaAbierto).toBe(false);
      expect(manager.modal.hidden).toBe(true);
      expect(document.body.classList.contains('modal-open')).toBe(false);
    });
  });

  describe('toggleModoEdicion()', () => {
    test('activa el modo edición y cambia el botón', () => {
      const manager = new DrawerListasManager();

      manager.toggleModoEdicion();

      expect(manager.modoEdicion).toBe(true);
      expect(manager.listaListasEl.classList.contains('modo-edicion')).toBe(true);
      expect(manager.btnEditarModal.textContent).toBe('✓');
    });

    test('lo desactiva de nuevo al llamarlo otra vez', () => {
      const manager = new DrawerListasManager();

      manager.toggleModoEdicion();
      manager.toggleModoEdicion();

      expect(manager.modoEdicion).toBe(false);
      expect(manager.listaListasEl.classList.contains('modo-edicion')).toBe(false);
      expect(manager.btnEditarModal.textContent).toBe('Editar');
    });
  });

  describe('abrirAjustesLista() / cerrarModalEditar()', () => {
    test('rellena el formulario de edición con los datos de la lista', () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Playa', color: '#abcabc' }];

      manager.abrirAjustesLista(3);

      expect(manager.listaEditandoId).toBe(3);
      expect(manager.inputEditarNombre.value).toBe('Playa');
      expect(manager.inputEditarColor.value).toBe('#abcabc');
      expect(manager.modalEditar.hidden).toBe(false);
    });

    test('no hace nada si la lista no existe', () => {
      const manager = new DrawerListasManager();
      manager.listas = [];

      manager.abrirAjustesLista(999);

      expect(manager.listaEditandoId).toBeNull();
    });

    test('cerrarModalEditar() oculta el modal y limpia el id en edición', () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Playa', color: '#abcabc' }];
      manager.abrirAjustesLista(3);

      manager.cerrarModalEditar();

      expect(manager.modalEditar.hidden).toBe(true);
      expect(manager.listaEditandoId).toBeNull();
    });
  });

  describe('guardarCambiosLista()', () => {
    function fakeSubmitEvent() {
      return { preventDefault: jest.fn() };
    }

    test('avisa si no hay ninguna lista en edición', async () => {
      const manager = new DrawerListasManager();

      await manager.guardarCambiosLista(fakeSubmitEvent());

      expect(global.Toast.error).toHaveBeenCalledWith('Error: No hay lista seleccionada');
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('avisa si el nombre está vacío', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Playa', color: '#abcabc' }];
      manager.abrirAjustesLista(3);
      manager.inputEditarNombre.value = '   ';

      await manager.guardarCambiosLista(fakeSubmitEvent());

      expect(global.Toast.error).toHaveBeenCalledWith('El nombre de la lista es requerido');
    });

    test('guarda los cambios y actualiza la lista en memoria', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Playa', color: '#abcabc' }];
      manager.abrirAjustesLista(3);
      manager.inputEditarNombre.value = 'Playa renombrada';
      manager.inputEditarColor.value = '#000000';
      mockFetchOnce(true, {});

      await manager.guardarCambiosLista(fakeSubmitEvent());

      expect(global.fetch).toHaveBeenCalledWith('/api/listas/3', expect.objectContaining({ method: 'PUT' }));
      expect(manager.listas[0].nombre).toBe('Playa renombrada');
      expect(manager.modalEditar.hidden).toBe(true);
      expect(global.Toast.success).toHaveBeenCalled();
    });

    test('muestra el error del backend si falla', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Playa', color: '#abcabc' }];
      manager.abrirAjustesLista(3);
      manager.inputEditarNombre.value = 'Playa renombrada';
      mockFetchOnce(false, { error: 'Nombre duplicado' });

      await manager.guardarCambiosLista(fakeSubmitEvent());

      expect(global.Toast.error).toHaveBeenCalledWith('Nombre duplicado');
    });
  });

  describe('salirDeLista()', () => {
    test('no hace nada si el usuario cancela la confirmación', async () => {
      global.confirm.mockReturnValueOnce(false);
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;

      await manager.salirDeLista();

      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('sale de la lista, la quita de memoria y no recarga si no era la actual', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Compartida' }];
      manager.listaEditandoId = 3;
      manager.listaActualId = 1;
      mockFetchOnce(true, {});

      await manager.salirDeLista();

      expect(manager.listas).toHaveLength(0);
      expect(global.Toast.success).toHaveBeenCalled();
      expect(window.location.reload).not.toHaveBeenCalled();
    });

    test('recarga la página si la lista de la que se sale era la actual', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 3, nombre: 'Compartida' }];
      manager.listaEditandoId = 3;
      manager.listaActualId = 3;
      mockFetchOnce(true, {});

      await manager.salirDeLista();

      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('cambiarLista()', () => {
    test('delega en window.cambiarLista y sincroniza localStorage', async () => {
      const manager = new DrawerListasManager();
      manager.listas = [{ id: 9, nombre: 'Nueva', icono: 'h-star' }];
      window.cambiarLista = jest.fn().mockResolvedValue();

      await manager.cambiarLista(9);

      expect(window.cambiarLista).toHaveBeenCalledWith(9);
      expect(localStorage.getItem('lista-actual-nombre')).toBe('Nueva');
      expect(localStorage.getItem('lista-actual-icono')).toBe('h-star');
      expect(manager.listaActualId).toBe(9);
    });

    test('no falla si window.cambiarLista no está definida', async () => {
      const manager = new DrawerListasManager();
      delete window.cambiarLista;

      await expect(manager.cambiarLista(9)).resolves.toBeUndefined();
    });
  });

  describe('miembros y permisos', () => {
    test('cargarMiembros() renderiza propietario y miembros', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      mockFetchOnce(true, {
        propietario: { nombre_usuario: 'Ana' },
        miembros: [{ id: 5, nombre_usuario: 'Luis', email: 'luis@test.com', nivel: 'ver' }],
      });

      await manager.cargarMiembros();

      const listaMiembros = document.getElementById('listaMiembros');
      expect(listaMiembros.textContent).toContain('Ana');
      expect(listaMiembros.textContent).toContain('Luis');
      expect(listaMiembros.querySelectorAll('.selectNivelPermiso')).toHaveLength(1);
    });

    test('actualizarPermiso() envía PATCH con el nuevo nivel', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      mockFetchOnce(true, {});
      const evento = { target: { dataset: { usuarioId: '5' }, value: 'editar' } };

      await manager.actualizarPermiso(evento);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/listas/3/permisos/5',
        expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ nivel: 'editar' }) })
      );
      expect(document.getElementById('miembrosExito').textContent).toBe('Permiso actualizado');
    });

    test('revocarAcceso() pide confirmación y hace DELETE', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      jest.spyOn(manager, 'cargarMiembros').mockResolvedValue();
      mockFetchOnce(true, {});
      const evento = { target: { dataset: { usuarioId: '5' } } };

      await manager.revocarAcceso(evento);

      expect(global.fetch).toHaveBeenCalledWith('/api/listas/3/permisos/5', expect.objectContaining({ method: 'DELETE' }));
      expect(document.getElementById('miembrosExito').textContent).toBe('Acceso revocado');
    });

    test('revocarAcceso() no hace nada si se cancela la confirmación', async () => {
      global.confirm.mockReturnValueOnce(false);
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      const evento = { target: { dataset: { usuarioId: '5' } } };

      await manager.revocarAcceso(evento);

      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe('compartir', () => {
    test('compartirPorUsuario() exige seleccionar un usuario', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      document.getElementById('buscarUsuario').value = '';

      await manager.compartirPorUsuario({ preventDefault: jest.fn() });

      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('compartirPorUsuario() comparte con el usuario indicado', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      jest.spyOn(manager, 'cargarMiembros').mockResolvedValue();
      document.getElementById('buscarUsuario').value = 'Ana';
      mockFetchOnce(true, {});

      await manager.compartirPorUsuario({ preventDefault: jest.fn() });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/listas/3/compartir',
        expect.objectContaining({ method: 'POST', body: JSON.stringify({ usuario: 'Ana', nivel: 'editar' }) })
      );
    });

    test('compartirPorEmail() genera un enlace de invitación si el backend devuelve código', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      jest.spyOn(manager, 'cargarMiembros').mockResolvedValue();
      document.getElementById('emailDestino').value = 'x@test.com';
      mockFetchOnce(true, { codigo: 'abc123' });

      await manager.compartirPorEmail({ preventDefault: jest.fn() });

      expect(document.getElementById('enlaceInvitacionInput').value).toBe('http://localhost/aceptar-invitacion/abc123');
    });

    test('generarEnlaceCompartir() muestra el enlace generado', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      mockFetchOnce(true, { codigo: 'xyz789' });

      await manager.generarEnlaceCompartir();

      expect(document.getElementById('enlaceInvitacionInput').value).toContain('xyz789');
    });

    test('copiarEnlace() copia el input al portapapeles', () => {
      const manager = new DrawerListasManager();
      document.getElementById('enlaceInvitacionInput').value = 'http://x';

      manager.copiarEnlace();

      expect(document.execCommand).toHaveBeenCalledWith('copy');
      expect(document.getElementById('miembrosExito').textContent).toBe('Enlace copiado al portapapeles!');
    });

    test('compartirPorWhatsApp() abre wa.me con el número si se indica', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      manager.listas = [{ id: 3, nombre: 'Casa' }];
      document.getElementById('inputTelefonoWhatsApp').value = '+34 600 11 22 33';
      mockFetchOnce(true, { codigo: 'wa1' });

      await manager.compartirPorWhatsApp();

      expect(window.open).toHaveBeenCalledWith(expect.stringContaining('https://wa.me/34600112233'), '_blank');
    });

    test('compartirPorWhatsApp() usa web.whatsapp.com si no hay número', async () => {
      const manager = new DrawerListasManager();
      manager.listaEditandoId = 3;
      manager.listas = [{ id: 3, nombre: 'Casa' }];
      document.getElementById('inputTelefonoWhatsApp').value = '';
      mockFetchOnce(true, { codigo: 'wa2' });

      await manager.compartirPorWhatsApp();

      expect(window.open).toHaveBeenCalledWith(expect.stringContaining('https://web.whatsapp.com/send'), '_blank');
    });
  });

  describe('cambiarTabCompartir()', () => {
    test('activa el panel de usuario y enfoca su input', () => {
      const manager = new DrawerListasManager();
      const focusSpy = jest.spyOn(document.getElementById('buscarUsuario'), 'focus');

      manager.cambiarTabCompartir('usuario');

      expect(document.getElementById('panelUsuario').style.display).toBe('block');
      expect(document.getElementById('panelEmail').style.display).toBe('none');
      expect(focusSpy).toHaveBeenCalled();
    });
  });

  describe('buscarUsuarios()', () => {
    test('no busca si la query es demasiado corta', async () => {
      const manager = new DrawerListasManager();

      await manager.buscarUsuarios('a');

      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('renderiza los usuarios encontrados', async () => {
      const manager = new DrawerListasManager();
      mockFetchOnce(true, { usuarios: [{ nombre_usuario: 'Ana', email: 'ana@test.com' }] });

      await manager.buscarUsuarios('an');

      expect(document.getElementById('resultadosBusqueda').textContent).toContain('Ana');
    });
  });

  describe('escaparHTML()', () => {
    test('convierte etiquetas en texto plano', () => {
      const manager = new DrawerListasManager();

      expect(manager.escaparHTML('<b>hola</b>')).toBe('&lt;b&gt;hola&lt;/b&gt;');
    });
  });
});

describe('CrearListaModal', () => {
  test('lanza error si falta el modal o el formulario', () => {
    document.body.innerHTML = '';
    expect(() => new CrearListaModal()).toThrow();
  });

  test('onOpen() regenera el formulario vía FormBuilder', () => {
    const modal = new CrearListaModal();

    modal.open();

    const nombre = modal.form.querySelector('input[name="nombre"]');
    expect(nombre).not.toBeNull();
    expect(modal.element.hidden).toBe(false);
  });

  describe('onSubmit()', () => {
    function prepararFormularioConNombre(nombre) {
      const modal = new CrearListaModal();
      modal.open();
      modal.form.querySelector('input[name="nombre"]').value = nombre;
      return modal;
    }

    test('exige un nombre', async () => {
      const modal = prepararFormularioConNombre('');

      await modal.onSubmit({ preventDefault: jest.fn() });

      expect(global.Toast.error).toHaveBeenCalledWith('El nombre es requerido');
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test('crea la lista, cierra el modal y cambia a ella', async () => {
      const modal = prepararFormularioConNombre('Mi lista nueva');
      window.cambiarLista = jest.fn().mockResolvedValue();
      mockFetchOnce(true, { id: 42, nombre: 'Mi lista nueva' });

      await modal.onSubmit({ preventDefault: jest.fn() });

      expect(global.fetch).toHaveBeenCalledWith('/api/listas', expect.objectContaining({ method: 'POST' }));
      expect(modal.element.hidden).toBe(true);
      expect(window.cambiarLista).toHaveBeenCalledWith(42);
    });

    test('refresca el drawer asociado si existe', async () => {
      const modal = prepararFormularioConNombre('Otra lista');
      modal.drawerManager = { refrescar: jest.fn() };
      window.cambiarLista = jest.fn().mockResolvedValue();
      mockFetchOnce(true, { id: 43, nombre: 'Otra lista' });

      await modal.onSubmit({ preventDefault: jest.fn() });

      expect(modal.drawerManager.refrescar).toHaveBeenCalled();
    });

    test('muestra el error del backend si falla la creación', async () => {
      const modal = prepararFormularioConNombre('Lista repetida');
      mockFetchOnce(false, { error: 'Ya existe una lista con ese nombre' });

      await modal.onSubmit({ preventDefault: jest.fn() });

      expect(global.Toast.error).toHaveBeenCalledWith('Ya existe una lista con ese nombre');
    });
  });
});
