/**
 * Jest Setup - Configuración global para tests
 */

// Mock de window.DOM si no existe
if (typeof window === 'undefined' || !window.DOM) {
  global.window = global.window || {};
  global.window.DOM = {
    get: jest.fn(),
    toggle: jest.fn(),
    toggleClass: jest.fn(),
    existe: jest.fn(),
    clear: jest.fn(),
    clearAll: jest.fn()
  };
}

// Mock de window.API si no existe
if (typeof window === 'undefined' || !window.API) {
  global.window = global.window || {};
  global.window.API = {
    obtenerProductos: jest.fn(),
    crearProducto: jest.fn(),
    actualizarProducto: jest.fn(),
    borrarProducto: jest.fn(),
    obtenerCategorias: jest.fn(),
    crearCategoria: jest.fn(),
    borrarCategoria: jest.fn(),
    obtenerEspacios: jest.fn(),
    crearEspacio: jest.fn(),
    actualizarEspacio: jest.fn(),
    borrarEspacio: jest.fn(),
    cargarCompra: jest.fn(),
    crearArticuloCompra: jest.fn(),
    actualizarArticuloCompra: jest.fn(),
    marcarCompletadoCompra: jest.fn(),
    borrarArticuloCompra: jest.fn()
  };
}

// Mock de fetch si no existe
global.fetch = jest.fn();

// Mock de console methods para evitar output en tests
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
};

// Timeout por defecto para async tests
jest.setTimeout(10000);
