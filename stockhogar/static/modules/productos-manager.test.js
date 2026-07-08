/**
 * Tests para ProductosManager
 * Cubre: CRUD, filtrado, render, modales
 */

describe('ProductosManager', () => {
  let manager;
  let mockDOM;
  let mockAPI;

  beforeEach(() => {
    // Mock DOM Manager
    mockDOM = {
      lista: { innerHTML: '' },
      vacio: { hidden: false },
      filtros: { innerHTML: '' },
      get: jest.fn((id) => {
        const elements = {
          lista: { innerHTML: '' },
          vacio: { hidden: false },
          filtros: { innerHTML: '' },
          campoNombre: { value: '' },
          campoCategoria: { value: '' },
          campoCantidad: { value: '1' },
          campoUnidad: { value: 'ud' },
          campoIcono: { value: '' },
          modal: { hidden: true },
          modalTitulo: { textContent: '' },
          productoId: { value: '' },
          formProducto: { reset: jest.fn() },
          btnQuitarIconoProducto: { hidden: true }
        };
        return elements[id];
      })
    };

    // Mock API Client
    mockAPI = {
      obtenerProductos: jest.fn().mockResolvedValue([
        { id: 1, nombre: 'Leche', categoria: 'Lácteos', cantidad: 2, unidad: 'L' },
        { id: 2, nombre: 'Pan', categoria: 'Panadería', cantidad: 1, unidad: 'ud' }
      ]),
      crearProducto: jest.fn().mockResolvedValue({
        id: 3, nombre: 'Nuevo', categoria: 'Otros', cantidad: 1, unidad: 'ud'
      }),
      actualizarProducto: jest.fn().mockResolvedValue({
        id: 1, nombre: 'Leche actualizada', categoria: 'Lácteos', cantidad: 3, unidad: 'L'
      }),
      borrarProducto: jest.fn().mockResolvedValue(null)
    };

    // Crear instancia del manager
    manager = new ProductosManager(mockAPI, mockDOM);
  });

  describe('CRUD Operations', () => {
    test('cargar() obtiene productos del API', async () => {
      await manager.cargar();

      expect(mockAPI.obtenerProductos).toHaveBeenCalled();
      expect(manager.productos).toHaveLength(2);
      expect(manager.productos[0].nombre).toBe('Leche');
    });

    test('crear() añade producto a lista y notifica', async () => {
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.crear({ nombre: 'Nuevo', categoria: 'Otros' });

      expect(mockAPI.crearProducto).toHaveBeenCalled();
      expect(manager.productos).toContainEqual(
        expect.objectContaining({ nombre: 'Nuevo' })
      );
      expect(listener).toHaveBeenCalledWith('producto-creado', expect.any(Object));
    });

    test('actualizar() modifica producto existente', async () => {
      manager.productos = [{ id: 1, nombre: 'Leche', categoria: 'Lácteos' }];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.actualizar(1, { nombre: 'Leche actualizada' });

      expect(mockAPI.actualizarProducto).toHaveBeenCalledWith(1, { nombre: 'Leche actualizada' });
      expect(listener).toHaveBeenCalledWith('producto-actualizado', expect.any(Object));
    });

    test('borrar() elimina producto de lista', async () => {
      manager.productos = [
        { id: 1, nombre: 'Leche' },
        { id: 2, nombre: 'Pan' }
      ];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.borrar(1);

      expect(mockAPI.borrarProducto).toHaveBeenCalledWith(1);
      expect(manager.productos).toHaveLength(1);
      expect(manager.productos[0].id).toBe(2);
      expect(listener).toHaveBeenCalledWith('producto-borrado', 1);
    });
  });

  describe('Filtrado', () => {
    beforeEach(() => {
      manager.productos = [
        { id: 1, nombre: 'Leche', categoria: 'Lácteos' },
        { id: 2, nombre: 'Pan', categoria: 'Panadería' },
        { id: 3, nombre: 'Queso', categoria: 'Lácteos' }
      ];
    });

    test('filtrar() por categoría devuelve solo esos productos', () => {
      const filtrados = manager.filtrar('Lácteos');

      expect(filtrados).toHaveLength(2);
      expect(filtrados.every(p => p.categoria === 'Lácteos')).toBe(true);
    });

    test('filtrar() por texto busca en nombre', () => {
      const filtrados = manager.filtrar(null, 'leche');

      expect(filtrados).toHaveLength(1);
      expect(filtrados[0].nombre).toBe('Leche');
    });

    test('obtenerFiltrados() aplica ambos filtros', () => {
      manager.filtroCategoria = 'Lácteos';
      manager.textoBusqueda = 'queso';

      const filtrados = manager.obtenerFiltrados();

      expect(filtrados).toHaveLength(1);
      expect(filtrados[0].nombre).toBe('Queso');
    });
  });

  describe('Helpers', () => {
    test('obtenerPorId() retorna producto correcto', () => {
      manager.productos = [
        { id: 1, nombre: 'Leche' },
        { id: 2, nombre: 'Pan' }
      ];

      const producto = manager.obtenerPorId(1);

      expect(producto).toEqual({ id: 1, nombre: 'Leche' });
    });

    test('obtenerPorNombre() retorna producto por nombre', () => {
      manager.productos = [
        { id: 1, nombre: 'Leche', categoria: 'Lácteos' }
      ];

      const producto = manager.obtenerPorNombre('Leche');

      expect(producto).toEqual({ id: 1, nombre: 'Leche', categoria: 'Lácteos' });
    });

    test('_escapeHtml() escapa caracteres especiales', () => {
      const input = '<script>alert("xss")</script>';
      const escaped = manager._escapeHtml(input);

      expect(escaped).not.toContain('<script>');
      expect(escaped).toContain('&lt;');
    });
  });

  describe('Event Emitter', () => {
    test('suscribir() registra listener', () => {
      const listener = jest.fn();

      manager.suscribir(listener);
      manager.notificar('test-event', { data: 'test' });

      expect(listener).toHaveBeenCalledWith('test-event', { data: 'test' });
    });

    test('suscribir() retorna función para desuscribirse', () => {
      const listener = jest.fn();
      const unsubscribe = manager.suscribir(listener);

      manager.notificar('test', {});
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
      manager.notificar('test', {});
      expect(listener).toHaveBeenCalledTimes(1); // No aumentó
    });
  });
});
