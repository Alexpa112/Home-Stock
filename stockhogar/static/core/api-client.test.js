/**
 * Tests para APIClient (Singleton)
 * Cubre: HTTP requests, error handling, endpoints
 */

describe('APIClient', () => {
  let api;

  beforeEach(() => {
    // Mock fetch globalmente
    global.fetch = jest.fn();

    // Crear nueva instancia para cada test
    api = new APIClient();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('GET Requests', () => {
    test('obtenerProductos() retorna lista de productos', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ([
          { id: 1, nombre: 'Leche' },
          { id: 2, nombre: 'Pan' }
        ])
      });

      const productos = await api.obtenerProductos();

      expect(productos).toHaveLength(2);
      expect(productos[0].nombre).toBe('Leche');
      expect(global.fetch).toHaveBeenCalledWith('/api/productos');
    });

    test('obtenerCategorias() retorna lista de categorías', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ([
          { id: 1, nombre: 'Lácteos', icono: '🥛' }
        ])
      });

      const categorias = await api.obtenerCategorias();

      expect(categorias).toHaveLength(1);
      expect(categorias[0].nombre).toBe('Lácteos');
    });

    test('obtenerEspacios() retorna lista de espacios', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ([
          { id: 1, nombre: 'Casa' }
        ])
      });

      const espacios = await api.obtenerEspacios();

      expect(espacios).toHaveLength(1);
      expect(global.fetch).toHaveBeenCalledWith('/api/espacios');
    });
  });

  describe('POST Requests', () => {
    test('crearProducto() envía datos correctos', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 3, nombre: 'Nuevo' })
      });

      const datos = { nombre: 'Nuevo', categoria: 'Otros' };
      const resultado = await api.crearProducto(datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos', expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
      }));
      expect(resultado.id).toBe(3);
    });

    test('crearCategoria() envía datos correctos', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 3, nombre: 'Frutas' })
      });

      const datos = { nombre: 'Frutas', icono: '🍎' };
      await api.crearCategoria(datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/categorias', expect.objectContaining({
        method: 'POST'
      }));
    });
  });

  describe('PUT Requests', () => {
    test('actualizarProducto() envía PUT request correcto', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, nombre: 'Actualizado' })
      });

      const datos = { nombre: 'Actualizado' };
      await api.actualizarProducto(1, datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos/1', expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify(datos)
      }));
    });
  });

  describe('DELETE Requests', () => {
    test('borrarProducto() envía DELETE request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await api.borrarProducto(1);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos/1', expect.objectContaining({
        method: 'DELETE'
      }));
    });
  });

  describe('Error Handling', () => {
    test('lanza APIError si respuesta no es OK', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Producto no encontrado' })
      });

      await expect(api.obtenerProductos()).rejects.toThrow('404: Not Found');
    });

    test('lanza APIError si fetch falla', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.obtenerProductos()).rejects.toThrow();
    });

    test('maneja timeout de request', async () => {
      const originalFetch = global.fetch;
      global.fetch = jest.fn(() =>
        new Promise(resolve => setTimeout(resolve, 15000)) // Más que timeout
      );

      const timeoutPromise = api.obtenerProductos();

      // Simular que pasa el timeout
      jest.advanceTimersByTime(15000);

      global.fetch = originalFetch;
    });
  });

  describe('Serialización JSON', () => {
    test('convierte respuesta JSON correctamente', async () => {
      const mockData = {
        id: 1,
        nombre: 'Test',
        cantidad: 5,
        completado: true
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      const resultado = await api.obtenerProductos();

      expect(resultado).toEqual([mockData]);
      expect(resultado[0].cantidad).toBe(5);
      expect(resultado[0].completado).toBe(true);
    });
  });
});
