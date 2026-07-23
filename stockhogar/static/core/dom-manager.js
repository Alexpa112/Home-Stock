/**
 * DOM MANAGER - Centraliza TODOS los selectores del proyecto
 * Patrón: Single Responsibility - Solo gestiona acceso a elementos
 * Beneficio: Si un ID cambia, solo cambias aquí, no en 10 lugares
 */
class DOMManager {
  constructor() {
    this.cache = new Map();
  }

  /**
   * Obtiene elemento con caching automático
   * @param {string} id - ID del elemento
   * @param {boolean} cacheado - Si usa caché (default true)
   * @returns {Element|null}
   */
  get(id, cacheado = true) {
    if (cacheado && this.cache.has(id)) {
      return this.cache.get(id);
    }
    const el = document.getElementById(id);
    if (el && cacheado) {
      this.cache.set(id, el);
    }
    return el;
  }

  // ===== TOPBAR Y CABECERA =====
  get topbar() { return this.get('appShell'); }
  get btnTema() { return this.get('btnTema'); }
  get btnCategorias() { return this.get('btnCategorias'); }
  get btnEscanearTicket() { return this.get('btnEscanearTicket'); }
  get btnAjustes() { return this.get('btnAjustes'); }

  // ===== SELECTOR DE LISTA =====
  get selectorLista() { return this.get('selectorLista'); }
  get listaActualBtn() { return this.get('listaActualBtn'); }
  get listaActualIcono() { return this.get('listaActualIcono'); }
  get listaActualNombre() { return this.get('listaActualNombre'); }
  get listaActualRol() { return this.get('listaActualRol'); }
  get btnCambiarLista() { return this.get('btnCambiarLista'); }

  // ===== VISTA STOCK =====
  get vistaStock() { return this.get('vistaStock'); }
  get buscador() { return this.get('buscador'); }
  get filtros() { return this.get('filtros'); }
  get lista() { return this.get('lista'); }
  get vacio() { return this.get('vacio'); }

  // ===== VISTA COMPRA =====
  get vistaCompra() { return this.get('vistaCompra'); }
  get gruposCompra() { return this.get('gruposCompra'); }
  get compraVacia() { return this.get('compraVacia'); }
  get seccionCompletados() { return this.get('seccionCompletados'); }
  get btnToggleCompletados() { return this.get('btnToggleCompletados'); }
  get tilesCompletados() { return this.get('tilesCompletados'); }

  // ===== TABS =====
  get tabs() { return this.get('tabs'); }

  // ===== MODAL PRODUCTO =====
  get modal() { return this.get('modal'); }
  get btnAbrirModal() { return this.get('btnAbrirModal'); }
  get formProducto() { return this.get('formProducto'); }
  get modalTitulo() { return this.get('modalTitulo'); }
  get productoId() { return this.get('productoId'); }
  get campoNombre() { return this.get('campoNombre'); }
  get campoCategoria() { return this.get('campoCategoria'); }
  get campoIcono() { return this.get('campoIcono'); }
  get selectorIconoProducto() { return this.get('selectorIconoProducto'); }
  get btnQuitarIconoProducto() { return this.get('btnQuitarIconoProducto'); }

  // ===== MODAL COMPRA =====
  get modalCompra() { return this.get('modalCompra'); }
  get formCompra() { return this.get('formCompra'); }
  get compraModalTitulo() { return this.get('compraModalTitulo'); }
  get compraEditId() { return this.get('compraEditId'); }
  get compraCampoCantidad() { return this.get('compraCampoCantidad'); }
  get compraCampoSubdescripcion() { return this.get('compraCampoSubdescripcion'); }
  get compraCampoCategoria() { return this.get('compraCampoCategoria'); }
  get compraCampoIcono() { return this.get('compraCampoIcono'); }
  get selectorIconoCompra() { return this.get('selectorIconoCompra'); }
  get btnQuitarIconoCompra() { return this.get('btnQuitarIconoCompra'); }
  get compraBotonGuardar() { return this.get('compraBotonGuardar'); }

  // ===== DRAWER LISTAS =====
  get modalMisListas() { return this.get('modalMisListas'); }
  get listaListas() { return this.get('listaListas'); }
  get btnCerrarMisListas() { return this.get('btnCerrarMisListas'); }
  get btnEditarMisListas() { return this.get('btnEditarMisListas'); }
  get btnCrearNuevaLista() { return this.get('btnCrearNuevaLista'); }

  // ===== FAB =====
  get fab() { return this.get('btnAbrirModal'); }

  /**
   * Toggle visibilidad con atributo 'hidden'
   */
  toggle(elemento, visible = null) {
    if (!elemento) return;
    if (visible === null) {
      elemento.hidden = !elemento.hidden;
    } else {
      elemento.hidden = !visible;
    }
  }

  /**
   * Añade/quita clase con validación
   */
  toggleClass(elemento, className, force = null) {
    if (!elemento) return;
    if (force === null) {
      elemento.classList.toggle(className);
    } else {
      elemento.classList.toggle(className, force);
    }
  }

  /**
   * Limpia caché (útil si se recarga el DOM)
   */
  clearCache() {
    this.cache.clear();
  }
}

// Instancia global singleton (solo en navegador: en tests se usa require())
if (typeof window !== 'undefined') {
  window.DOM = new DOMManager();
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = DOMManager;
}
