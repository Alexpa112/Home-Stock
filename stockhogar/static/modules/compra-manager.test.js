/**
 * Tests para CompraManager
 * Cubre: CRUD artículos, completados, render
 */

describe('CompraManager', () => {
  let manager;
  let mockDOM;
  let mockAPI;

  beforeEach(() => {
    mockDOM = {
      lista: { innerHTML: '' },
      vacio: { hidden: false },
      get: jest.fn((id) => {
        const elements = {
          lista: { innerHTML: '' },
          vacio: { hidden: false },
          campoArticulo: { value: '' },
          campoCantidad: { value: '1' },
          campoUnidad: { value: 'ud' },
          modal: { hidden: true },
          formCompra: { reset: jest.fn() },
          articuloId: { value: '' }
        };
        return elements[id];
      })
    };

    mockAPI = {
      cargarCompra: jest.fn().mockResolvedValue([
        { id: 1, nombre: 'Leche', cantidad: 2, completado: false, lista_id: 1 },
        { id: 2, nombre: 'Pan', cantidad: 1, completado: false, lista_id: 1 }
      ]),
      crearArticuloCompra: jest.fn().mockResolvedValue({
        id: 3, nombre: 'Queso', cantidad: 1, completado: false
      }),
      actualizarArticuloCompra: jest.fn().mockResolvedValue({
        id: 1, nombre: 'Leche', cantidad: 3, completado: false
      }),
      marcarCompletadoCompra: jest.fn().mockResolvedValue({
        id: 1, completado: true
      }),
      borrarArticuloCompra: jest.fn().mockResolvedValue(null)
    };

    manager = new CompraManager(mockAPI, mockDOM);
  });

  describe('CRUD Operations', () => {
    test('cargarPorLista() obtiene artículos del API', async () => {
      await manager.cargarPorLista(1);

      expect(mockAPI.cargarCompra).toHaveBeenCalledWith(1);
      expect(manager.articulos).toHaveLength(2);
      expect(manager.articulos[0].nombre).toBe('Leche');
    });

    test('crear() añade artículo y notifica', async () => {
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.crear({ nombre: 'Queso', cantidad: 1 });

      expect(mockAPI.crearArticuloCompra).toHaveBeenCalled();
      expect(manager.articulos).toContainEqual(
        expect.objectContaining({ nombre: 'Queso' })
      );
      expect(listener).toHaveBeenCalledWith('articulo-creado', expect.any(Object));
    });

    test('actualizar() modifica artículo', async () => {
      manager.articulos = [{ id: 1, nombre: 'Leche', cantidad: 2 }];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.actualizar(1, { cantidad: 3 });

      expect(mockAPI.actualizarArticuloCompra).toHaveBeenCalledWith(1, { cantidad: 3 });
      expect(listener).toHaveBeenCalledWith('articulo-actualizado', expect.any(Object));
    });

    test('marcarCompletado() cambia estado de artículo', async () => {
      manager.articulos = [{ id: 1, nombre: 'Leche', completado: false }];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.marcarCompletado(1, true);

      expect(mockAPI.marcarCompletadoCompra).toHaveBeenCalledWith(1, true);
      expect(listener).toHaveBeenCalledWith('articulo-marcado-completado', 1);
    });

    test('borrar() elimina artículo de lista', async () => {
      manager.articulos = [
        { id: 1, nombre: 'Leche' },
        { id: 2, nombre: 'Pan' }
      ];
      const listener = jest.fn();
      manager.suscribir(listener);

      await manager.borrar(1);

      expect(mockAPI.borrarArticuloCompra).toHaveBeenCalledWith(1);
      expect(manager.articulos).toHaveLength(1);
      expect(manager.articulos[0].id).toBe(2);
      expect(listener).toHaveBeenCalledWith('articulo-borrado', 1);
    });
  });

  describe('Estadísticas', () => {
    test('totalPendientes retorna cantidad de pendientes', () => {
      manager.articulos = [
        { id: 1, completado: false },
        { id: 2, completado: true },
        { id: 3, completado: false }
      ];

      expect(manager.totalPendientes).toBe(2);
    });

    test('totalCompletados retorna cantidad de completados', () => {
      manager.articulos = [
        { id: 1, completado: false },
        { id: 2, completado: true },
        { id: 3, completado: true }
      ];

      expect(manager.totalCompletados).toBe(2);
    });

    test('calcular total por categoría', () => {
      manager.articulos = [
        { id: 1, nombre: 'Leche', categoria: 'Lácteos', cantidad: 2 },
        { id: 2, nombre: 'Queso', categoria: 'Lácteos', cantidad: 1 },
        { id: 3, nombre: 'Pan', categoria: 'Panadería', cantidad: 1 }
      ];

      const totales = manager._calcularTotalesPorCategoria();

      expect(totales['Lácteos']).toBe(3);
      expect(totales['Panadería']).toBe(1);
    });
  });

  describe('Agrupación', () => {
    test('_agruparPorCategoria agrupa artículos por categoría', () => {
      manager.articulos = [
        { id: 1, nombre: 'Leche', categoria: 'Lácteos' },
        { id: 2, nombre: 'Pan', categoria: 'Panadería' },
        { id: 3, nombre: 'Queso', categoria: 'Lácteos' }
      ];

      const agrupados = manager._agruparPorCategoria();

      expect(agrupados['Lácteos']).toHaveLength(2);
      expect(agrupados['Panadería']).toHaveLength(1);
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
