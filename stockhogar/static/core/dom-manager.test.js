/**
 * Tests para DOMManager (Singleton)
 * Cubre: selectores, caching, manipulación DOM
 */

describe('DOMManager', () => {
  let dom;

  beforeEach(() => {
    // Crear nuevo DOMManager para cada test
    dom = new DOMManager();

    // Mock document.getElementById
    document.getElementById = jest.fn((id) => {
      const mockElements = {
        lista: { id: 'lista', innerHTML: '', hidden: false },
        vacio: { id: 'vacio', hidden: true },
        modal: { id: 'modal', hidden: true },
        campoNombre: { id: 'campoNombre', value: '' },
        btnGuardar: { id: 'btnGuardar', addEventListener: jest.fn() }
      };
      return mockElements[id];
    });
  });

  describe('Selectores', () => {
    test('get() retorna elemento por ID', () => {
      const elemento = dom.get('lista');

      expect(elemento).not.toBeNull();
      expect(document.getElementById).toHaveBeenCalledWith('lista');
    });

    test('get() cachea elemento', () => {
      const el1 = dom.get('lista');
      const el2 = dom.get('lista');

      expect(el1).toBe(el2); // Misma instancia
      expect(document.getElementById).toHaveBeenCalledTimes(1); // Solo una llamada
    });

    test('get() retorna null si elemento no existe', () => {
      document.getElementById = jest.fn(() => null);

      const elemento = dom.get('noexiste');

      expect(elemento).toBeNull();
    });
  });

  describe('Manipulación CSS', () => {
    test('toggleClass() añade clase si no existe', () => {
      const mockEl = { classList: { toggle: jest.fn() } };
      document.getElementById = jest.fn(() => mockEl);

      dom.toggleClass('elemento', 'active');

      expect(mockEl.classList.toggle).toHaveBeenCalledWith('active');
    });

    test('toggle() cambia propiedad hidden', () => {
      const mockEl = { hidden: false };
      document.getElementById = jest.fn(() => mockEl);

      dom.toggle('elemento');

      expect(mockEl.hidden).toBe(true);
    });

    test('toggle() con estado explícito', () => {
      const mockEl = { hidden: true };
      document.getElementById = jest.fn(() => mockEl);

      dom.toggle('elemento', false);

      expect(mockEl.hidden).toBe(false);
    });
  });

  describe('Validación', () => {
    test('existe() retorna true si elemento existe', () => {
      document.getElementById = jest.fn(() => ({ id: 'test' }));

      const existe = dom.existe('test');

      expect(existe).toBe(true);
    });

    test('existe() retorna false si elemento no existe', () => {
      document.getElementById = jest.fn(() => null);

      const existe = dom.existe('noexiste');

      expect(existe).toBe(false);
    });
  });

  describe('Performance', () => {
    test('clear() limpia cache', () => {
      const el1 = dom.get('lista');
      dom.clear('lista');

      // Después de limpiar, la siguiente llamada debería ir a DOM
      document.getElementById = jest.fn(() => ({ id: 'lista' }));
      const el2 = dom.get('lista');

      // Se llamó a getElementById la segunda vez
      expect(document.getElementById).toHaveBeenCalled();
    });

    test('clearAll() limpia todo el cache', () => {
      dom.get('lista');
      dom.get('modal');
      dom.clearAll();

      // Cache debe estar vacío
      expect(dom.cache.size).toBe(0);
    });
  });
});
