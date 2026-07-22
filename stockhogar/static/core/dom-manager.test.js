/**
 * Tests para DOMManager (Singleton)
 * Cubre: selectores, caching, manipulación DOM
 */
const DOMManager = require('./dom-manager.js');

describe('DOMManager', () => {
  let dom;

  beforeEach(() => {
    dom = new DOMManager();

    document.getElementById = jest.fn((id) => {
      const mockElements = {
        lista: { id: 'lista', innerHTML: '', hidden: false },
        vacio: { id: 'vacio', hidden: true },
        modal: { id: 'modal', hidden: true },
        campoNombre: { id: 'campoNombre', value: '' },
        btnGuardar: { id: 'btnGuardar', addEventListener: jest.fn() },
      };
      return mockElements[id] || null;
    });
  });

  describe('Selectores', () => {
    test('get() retorna elemento por ID', () => {
      const elemento = dom.get('lista');

      expect(elemento).not.toBeNull();
      expect(document.getElementById).toHaveBeenCalledWith('lista');
    });

    test('get() cachea elemento por defecto', () => {
      const el1 = dom.get('lista');
      const el2 = dom.get('lista');

      expect(el1).toBe(el2);
      expect(document.getElementById).toHaveBeenCalledTimes(1);
    });

    test('get() con cacheado=false no usa ni alimenta la caché', () => {
      dom.get('lista', false);
      dom.get('lista', false);

      expect(document.getElementById).toHaveBeenCalledTimes(2);
    });

    test('get() retorna null si el elemento no existe', () => {
      const elemento = dom.get('noexiste');

      expect(elemento).toBeNull();
    });
  });

  describe('Manipulación CSS', () => {
    test('toggleClass() alterna la clase en el elemento dado', () => {
      const mockEl = { classList: { toggle: jest.fn() } };

      dom.toggleClass(mockEl, 'active');

      expect(mockEl.classList.toggle).toHaveBeenCalledWith('active');
    });

    test('toggleClass() con force explícito', () => {
      const mockEl = { classList: { toggle: jest.fn() } };

      dom.toggleClass(mockEl, 'active', true);

      expect(mockEl.classList.toggle).toHaveBeenCalledWith('active', true);
    });

    test('toggleClass() no falla si el elemento es null', () => {
      expect(() => dom.toggleClass(null, 'active')).not.toThrow();
    });

    test('toggle() invierte la propiedad hidden por defecto', () => {
      const mockEl = { hidden: false };

      dom.toggle(mockEl);

      expect(mockEl.hidden).toBe(true);
    });

    test('toggle() con visible=true fuerza hidden=false', () => {
      const mockEl = { hidden: true };

      dom.toggle(mockEl, true);

      expect(mockEl.hidden).toBe(false);
    });

    test('toggle() con visible=false fuerza hidden=true', () => {
      const mockEl = { hidden: false };

      dom.toggle(mockEl, false);

      expect(mockEl.hidden).toBe(true);
    });

    test('toggle() no falla si el elemento es null', () => {
      expect(() => dom.toggle(null)).not.toThrow();
    });
  });

  describe('Caché', () => {
    test('clearCache() vacía la caché por completo', () => {
      dom.get('lista');
      dom.get('modal');
      expect(dom.cache.size).toBe(2);

      dom.clearCache();

      expect(dom.cache.size).toBe(0);
    });

    test('tras clearCache(), get() vuelve a consultar el DOM', () => {
      dom.get('lista');
      dom.clearCache();
      dom.get('lista');

      expect(document.getElementById).toHaveBeenCalledTimes(2);
    });
  });
});
