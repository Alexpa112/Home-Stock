/**
 * Tests para CategoriasManager
 * Cubre: CRUD categorías, búsqueda
 */

describe('CategoriasManager', () => {
  let manager;
  let mockDOM;
  let mockAPI;

  beforeEach(() => {
    mockDOM = {
      filtros: { innerHTML: '' },
      get: jest.fn((id) => {
        const elements = {
          filtros: { innerHTML: '' },
          campoNombre: { value: '' },
          campoIcono: { value: '' },
          modal: { hidden: true },
          formCategoria: { reset: jest.fn() },
          categoriaId: { value: '' }
        };
        return elements[id];
      })
    };

    mockAPI = {
      obtenerCategorias: jest.fn().mockResolvedValue([
        { id: 1, nombre: 'Lácteos', icono: '🥛' },
        { id: 2, nombre: 'Panadería', icono: '🍞' }
      ]),
      crearCategoria: jest.fn().mockResolvedValue({
        id: 3, nombre: 'Frutas', icono: '🍎'
      }),
      borrarCategoria: jest.fn().mockResolvedValue(null)
    };

    manager = new CategoriasManager(mockAPI, mockDOM);
  });

  describe('CRUD Operations', () => {
    test('cargar() obtiene categorías del API', async () => {
      await manager.cargar();

      expect(mockAPI.obtenerCategorias).toHaveBeenCalled();
      expect(manager.categorias).toHaveLength(2);
      expect(manager.categorias[0].nombre).toBe('Lácteos');
    });

    test('crear() añade categoría y notifica', async () => {
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.crear({ nombre: 'Frutas', icono: '🍎' });

      expect(mockAPI.crearCategoria).toHaveBeenCalled();
      expect(manager.categorias).toContainEqual(
        expect.objectContaining({ nombre: 'Frutas' })
      );
      expect(listener).toHaveBeenCalledWith('categoria-creada', expect.any(Object));
    });

    test('borrar() elimina categoría', async () => {
      manager.categorias = [
        { id: 1, nombre: 'Lácteos', icono: '🥛' },
        { id: 2, nombre: 'Frutas', icono: '🍎' }
      ];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.borrar(1);

      expect(mockAPI.borrarCategoria).toHaveBeenCalledWith(1);
      expect(manager.categorias).toHaveLength(1);
      expect(manager.categorias[0].id).toBe(2);
      expect(listener).toHaveBeenCalledWith('categoria-borrada', 1);
    });
  });

  describe('Búsqueda', () => {
    beforeEach(() => {
      manager.categorias = [
        { id: 1, nombre: 'Lácteos', icono: '🥛' },
        { id: 2, nombre: 'Panadería', icono: '🍞' },
        { id: 3, nombre: 'Frutas', icono: '🍎' }
      ];
    });

    test('obtenerPorNombre() retorna categoría correcta', () => {
      const cat = manager.obtenerPorNombre('Lácteos');

      expect(cat).toEqual({ id: 1, nombre: 'Lácteos', icono: '🥛' });
    });

    test('obtenerPorNombre() es case-insensitive', () => {
      const cat = manager.obtenerPorNombre('lácteos');

      expect(cat).toEqual({ id: 1, nombre: 'Lácteos', icono: '🥛' });
    });

    test('obtenerIconoPorNombre() retorna icono', () => {
      const icono = manager.obtenerIconoPorNombre('Frutas');

      expect(icono).toBe('🍎');
    });

    test('obtenerIconoPorNombre() retorna icono por defecto si no existe', () => {
      const icono = manager.obtenerIconoPorNombre('NoExiste');

      expect(icono).toBe('📦'); // icono por defecto
    });

    test('existeCategoria() verifica si existe', () => {
      expect(manager.existeCategoria('Lácteos')).toBe(true);
      expect(manager.existeCategoria('NoExiste')).toBe(false);
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
