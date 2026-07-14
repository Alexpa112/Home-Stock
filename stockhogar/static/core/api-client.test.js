/**
 * Tests para APIClient (Singleton)
 * Cubre: HTTP requests, error handling, endpoints
 */
const { APIClient, APIError } = require('./api-client.js');

describe('APIClient', () => {
  let api;

  beforeEach(() => {
    global.fetch = jest.fn();
    api = new APIClient();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('GET Requests', () => {
    test('obtenerProductos() retorna lista de productos', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ([
          { id: 1, nombre: 'Leche' },
          { id: 2, nombre: 'Pan' }
        ])
      });

      const productos = await api.obtenerProductos();

      expect(productos).toHaveLength(2);
      expect(productos[0].nombre).toBe('Leche');
      expect(global.fetch.mock.calls[0][0]).toBe('/api/productos');
    });

    test('obtenerCategorias() retorna lista de categorías', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ([
          { id: 1, nombre: 'Lácteos', icono: '🥛' }
        ])
      });

      const categorias = await api.obtenerCategorias();

      expect(categorias).toHaveLength(1);
      expect(categorias[0].nombre).toBe('Lácteos');
    });

    test('GET no añade cabecera X-CSRFToken', async () => {
      global.fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ([]) });

      await api.obtenerProductos();

      const [, options] = global.fetch.mock.calls[0];
      expect(options.headers['X-CSRFToken']).toBeUndefined();
    });
  });

  describe('POST Requests', () => {
    test('crearProducto() envía datos correctos y cabecera CSRF', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 3, nombre: 'Nuevo' })
      });

      const datos = { nombre: 'Nuevo', categoria: 'Otros' };
      const resultado = await api.crearProducto(datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(datos),
      }));
      const [, options] = global.fetch.mock.calls[0];
      expect(options.headers['Content-Type']).toBe('application/json');
      expect(options.headers['X-CSRFToken']).toBe('');
      expect(resultado.id).toBe(3);
    });

    test('crearCategoria() envía datos correctos', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 3, nombre: 'Frutas' })
      });

      const datos = { nombre: 'Frutas', icono: '🍎' };
      await api.crearCategoria(datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/categorias', expect.objectContaining({
        method: 'POST'
      }));
    });
  });

  describe('PATCH Requests', () => {
    test('actualizarProducto() envía PATCH request correcto', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 1, nombre: 'Actualizado' })
      });

      const datos = { nombre: 'Actualizado' };
      await api.actualizarProducto(1, datos);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos/1', expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify(datos)
      }));
    });
  });

  describe('DELETE Requests', () => {
    test('borrarProducto() envía DELETE request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const resultado = await api.borrarProducto(1);

      expect(global.fetch).toHaveBeenCalledWith('/api/productos/1', expect.objectContaining({
        method: 'DELETE'
      }));
      expect(resultado).toBeNull();
    });
  });

  describe('Error Handling', () => {
    test('lanza APIError con el mensaje del backend si la respuesta no es OK', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Producto no encontrado' })
      });

      await expect(api.obtenerProductos()).rejects.toThrow('Producto no encontrado');
    });

    test('lanza APIError con mensaje por defecto si el backend no da detalle', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('no es JSON'); }
      });

      await expect(api.obtenerProductos()).rejects.toThrow('Internal Server Error');
    });

    test('lanza APIError si fetch falla por red', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.obtenerProductos()).rejects.toThrow('Network error');
    });

    test('hace timeout tras 10s sin respuesta y lanza APIError', async () => {
      jest.useFakeTimers();
      global.fetch.mockImplementationOnce((url, { signal }) => new Promise((resolve, reject) => {
        signal.addEventListener('abort', () => {
          const error = new Error('This operation was aborted');
          error.name = 'AbortError';
          reject(error);
        });
      }));

      const promesa = api.obtenerProductos();
      const expectacion = expect(promesa).rejects.toBeInstanceOf(APIError);

      await jest.advanceTimersByTimeAsync(10000);
      await expectacion;

      jest.useRealTimers();
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
        status: 200,
        json: async () => [mockData]
      });

      const resultado = await api.obtenerProductos();

      expect(resultado).toEqual([mockData]);
      expect(resultado[0].cantidad).toBe(5);
      expect(resultado[0].completado).toBe(true);
    });

    test('devuelve null en respuestas 204 sin cuerpo', async () => {
      global.fetch.mockResolvedValueOnce({ ok: true, status: 204 });

      const resultado = await api.borrarProducto(1);

      expect(resultado).toBeNull();
    });
  });
});
