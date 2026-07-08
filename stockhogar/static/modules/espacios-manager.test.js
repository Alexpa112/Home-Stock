/**
 * Tests para EspaciosManager
 * Cubre: CRUD espacios, selección, estado
 */

describe('EspaciosManager', () => {
  let manager;
  let mockDOM;
  let mockAPI;

  beforeEach(() => {
    mockDOM = {
      espacios: { innerHTML: '' },
      get: jest.fn((id) => {
        const elements = {
          espacios: { innerHTML: '' },
          campoNombre: { value: '' },
          campoColor: { value: '#FF6B6B' },
          modal: { hidden: true },
          formEspacio: { reset: jest.fn() }
        };
        return elements[id];
      })
    };

    mockAPI = {
      obtenerEspacios: jest.fn().mockResolvedValue([
        { id: 1, nombre: 'Casa', color: '#FF6B6B', activo: true },
        { id: 2, nombre: 'Oficina', color: '#4ECDC4', activo: false }
      ]),
      crearEspacio: jest.fn().mockResolvedValue({
        id: 3, nombre: 'Garaje', color: '#95E1D3', activo: false
      }),
      actualizarEspacio: jest.fn().mockResolvedValue({
        id: 1, nombre: 'Casa Nueva', color: '#FF6B6B', activo: true
      }),
      borrarEspacio: jest.fn().mockResolvedValue(null)
    };

    manager = new EspaciosManager(mockAPI, mockDOM);
  });

  describe('CRUD Operations', () => {
    test('cargar() obtiene espacios del API', async () => {
      await manager.cargar();

      expect(mockAPI.obtenerEspacios).toHaveBeenCalled();
      expect(manager.espacios).toHaveLength(2);
      expect(manager.espacios[0].nombre).toBe('Casa');
    });

    test('crear() añade espacio y notifica', async () => {
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.crear({ nombre: 'Garaje', color: '#95E1D3' });

      expect(mockAPI.crearEspacio).toHaveBeenCalled();
      expect(manager.espacios).toContainEqual(
        expect.objectContaining({ nombre: 'Garaje' })
      );
      expect(listener).toHaveBeenCalledWith('espacio-creado', expect.any(Object));
    });

    test('actualizar() modifica espacio', async () => {
      manager.espacios = [{ id: 1, nombre: 'Casa', color: '#FF6B6B' }];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.actualizar(1, { nombre: 'Casa Nueva' });

      expect(mockAPI.actualizarEspacio).toHaveBeenCalledWith(1, { nombre: 'Casa Nueva' });
      expect(listener).toHaveBeenCalledWith('espacio-actualizado', expect.any(Object));
    });

    test('borrar() elimina espacio', async () => {
      manager.espacios = [
        { id: 1, nombre: 'Casa' },
        { id: 2, nombre: 'Oficina' }
      ];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.borrar(1);

      expect(mockAPI.borrarEspacio).toHaveBeenCalledWith(1);
      expect(manager.espacios).toHaveLength(1);
      expect(manager.espacios[0].id).toBe(2);
      expect(listener).toHaveBeenCalledWith('espacio-borrado', 1);
    });
  });

  describe('Selección', () => {
    test('seleccionar() cambia espacio actual', async () => {
      manager.espacios = [
        { id: 1, nombre: 'Casa', activo: true },
        { id: 2, nombre: 'Oficina', activo: false }
      ];

      await manager.seleccionar(2);

      expect(manager.espacioActualId).toBe(2);
    });

    test('obtenerActual() retorna espacio activo', () => {
      manager.espacios = [
        { id: 1, nombre: 'Casa', activo: true },
        { id: 2, nombre: 'Oficina', activo: false }
      ];

      const actual = manager.obtenerActual();

      expect(actual.nombre).toBe('Casa');
    });

    test('cambiar espacio notifica evento', async () => {
      manager.espacios = [
        { id: 1, nombre: 'Casa', activo: true },
        { id: 2, nombre: 'Oficina', activo: false }
      ];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.seleccionar(2);

      expect(listener).toHaveBeenCalledWith('espacio-seleccionado', 2);
    });
  });

  describe('Event Emitter', () => {
    test('suscribir() registra listener', () => {
      const listener = jest.fn();

      manager.suscribir(listener);
      manager.notificar('test-event', { data: 'test' });

      expect(listener).toHaveBeenCalledWith('test-event', { data: 'test' });
    });
  });
});
