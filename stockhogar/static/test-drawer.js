/**
 * TEST SUITE - MODALES (Mis Listas)
 * Pruebas detalladas para validar funcionalidad de modales y lista de listas
 */

class ModalTestSuite {
  constructor() {
    this.results = [];
    this.startTime = null;
    this.endTime = null;
  }

  log(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = {
      'info': '📋',
      'success': '✅',
      'error': '❌',
      'warning': '⚠️',
      'debug': '🔍',
      'test': '🧪'
    }[type] || '•';
    console.log(`[${timestamp}] ${prefix} ${message}`);
  }

  assert(condition, message, details = '') {
    if (condition) {
      this.log(`PASS: ${message}`, 'success');
      this.results.push({ test: message, status: 'PASS', details });
      return true;
    } else {
      this.log(`FAIL: ${message} ${details ? `(${details})` : ''}`, 'error');
      this.results.push({ test: message, status: 'FAIL', details });
      return false;
    }
  }

  async wait(ms = 300) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // TEST 1: DOM Elements - Modales
  async testDOMElements() {
    this.log('TEST 1: Verificando elementos DOM de modales', 'test');

    const modalMisListas = document.getElementById('modalMisListas');
    const modalEditarLista = document.getElementById('modalEditarLista');
    const modalCrearLista = document.getElementById('modalCrearLista');
    const listaListas = document.getElementById('listaListas');
    const btnCerrarMisListas = document.getElementById('btnCerrarMisListas');
    const btnEditarMisListas = document.getElementById('btnEditarMisListas');
    const btnCrearNuevaLista = document.getElementById('btnCrearNuevaLista');

    this.assert(modalMisListas, 'Modal "Mis Listas" existe');
    this.assert(modalEditarLista, 'Modal "Editar Lista" existe');
    this.assert(modalCrearLista, 'Modal "Crear Lista" existe');
    this.assert(listaListas, 'Contenedor de listas existe');
    this.assert(btnCerrarMisListas, 'Botón cerrar Mis Listas existe');
    this.assert(btnEditarMisListas, 'Botón editar Mis Listas existe');
    this.assert(btnCrearNuevaLista, 'Botón crear nueva lista existe');
  }

  // TEST 2: Manager instances
  async testManagerInstances() {
    this.log('TEST 2: Verificando instancias de managers', 'test');

    this.assert(window.drawerListasManager, 'DrawerListasManager está instanciado');
    this.assert(window.crearListaModal, 'CrearListaModal está instanciado');

    if (window.drawerListasManager) {
      const manager = window.drawerListasManager;
      this.assert(typeof manager.abrirModal === 'function', 'abrirModal es función');
      this.assert(typeof manager.cerrarModal === 'function', 'cerrarModal es función');
      this.assert(typeof manager.cargarListas === 'function', 'cargarListas es función');
      this.assert(typeof manager.cambiarLista === 'function', 'cambiarLista es función');
      this.assert(typeof manager.toggleModoEdicion === 'function', 'toggleModoEdicion es función');
      this.assert(typeof manager.abrirAjustesLista === 'function', 'abrirAjustesLista es función');
    }
  }

  // TEST 3: Modal open/close
  async testModalOpenClose() {
    this.log('TEST 3: Probando abrir/cerrar "Mis Listas"', 'test');

    const manager = window.drawerListasManager;
    const modal = document.getElementById('modalMisListas');
    const fondo = document.getElementById('modalMisListas').parentElement;

    // Abrir
    manager.abrirModal();
    await this.wait(400);

    this.assert(!modal.hidden, 'Modal no está hidden después de abrir', modal.hidden);
    this.assert(document.body.classList.contains('modal-open'), 'Body tiene clase modal-open');

    // Cerrar
    manager.cerrarModal();
    await this.wait(400);

    this.assert(modal.hidden, 'Modal está hidden después de cerrar', modal.hidden);
    this.assert(!document.body.classList.contains('modal-open'), 'Body no tiene clase modal-open');
  }

  // TEST 4: Listas cargadas
  async testListasLoaded() {
    this.log('TEST 4: Verificando que listas se cargan correctamente', 'test');

    const manager = window.drawerListasManager;
    this.assert(manager.listas && Array.isArray(manager.listas), 'Listas es un array', typeof manager.listas);

    const count = manager.listas.length;
    this.log(`Se cargaron ${count} listas`, 'debug');

    if (count > 0) {
      manager.listas.forEach((lista, idx) => {
        this.assert(lista.id, `Lista ${idx} tiene ID`, lista.id);
        this.assert(lista.nombre, `Lista ${idx} tiene nombre`, lista.nombre);
        this.assert(lista.color, `Lista ${idx} tiene color`, lista.color);
      });

      // Verificar que las tarjetas existen en DOM
      const tarjetas = document.querySelectorAll('.tarjeta-lista');
      this.assert(tarjetas.length > 0, `Existen ${tarjetas.length} tarjetas en DOM`);
    } else {
      this.log('No hay listas cargadas', 'warning');
    }
  }

  // TEST 5: Modo edición
  async testModoEdicion() {
    this.log('TEST 5: Probando modo edición', 'test');

    const manager = window.drawerListasManager;
    const btnEditar = document.getElementById('btnEditarMisListas');
    const listaListas = document.getElementById('listaListas');

    // Activar modo edición
    manager.toggleModoEdicion();
    await this.wait(200);

    this.assert(manager.modoEdicion === true, 'Modo edición activado');
    this.assert(listaListas.classList.contains('modo-edicion'), 'Contenedor tiene clase modo-edicion');
    this.assert(btnEditar.textContent === '✓', 'Botón muestra checkmark', btnEditar.textContent);

    // Verificar que engranajes están visibles
    const engranajes = document.querySelectorAll('.btn-editar-tarjeta');
    engranajes.forEach((btn, idx) => {
      const opacity = getComputedStyle(btn).opacity;
      this.assert(parseFloat(opacity) > 0, `Engranaje ${idx} tiene opacity > 0`, opacity);
    });

    // Desactivar modo edición
    manager.toggleModoEdicion();
    await this.wait(200);

    this.assert(manager.modoEdicion === false, 'Modo edición desactivado');
    this.assert(btnEditar.textContent === 'Editar', 'Botón muestra "Editar"', btnEditar.textContent);
  }

  // TEST 6: Styles de modales
  async testModalStyles() {
    this.log('TEST 6: Verificando estilos de modales', 'test');

    const modal = document.querySelector('.modal');
    const footer = document.querySelector('.modal-footer');
    const content = document.querySelector('.modal-content');

    if (modal) {
      const modalStyles = getComputedStyle(modal);
      const width = modalStyles.width;
      const height = modalStyles.height;

      this.log(`Modal size: ${width} × ${height}`, 'debug');
      this.assert(width !== 'auto', 'Modal tiene ancho definido');
      this.assert(height !== 'auto', 'Modal tiene alto definido');
    }

    if (footer) {
      const buttons = footer.querySelectorAll('button');
      buttons.forEach((btn, idx) => {
        const height = getComputedStyle(btn).height;
        this.assert(height === '40px', `Botón ${idx} tiene altura 40px`, height);
      });
    }

    if (content) {
      const styles = getComputedStyle(content);
      this.assert(styles.flex !== 'none', 'Modal-content es flexible');
      this.assert(styles.overflow === 'auto', 'Modal-content permite scroll', styles.overflow);
    }
  }

  // TEST 7: Tarjetas de listas
  async testTarjetas() {
    this.log('TEST 7: Verificando estructura de tarjetas', 'test');

    const tarjetas = document.querySelectorAll('.tarjeta-lista');
    this.log(`Encontradas ${tarjetas.length} tarjetas`, 'debug');

    tarjetas.forEach((tarjeta, idx) => {
      const header = tarjeta.querySelector('.tarjeta-header');
      const titulo = tarjeta.querySelector('.tarjeta-header h3');
      const engranaje = tarjeta.querySelector('.btn-editar-tarjeta');
      const avatares = tarjeta.querySelector('.tarjeta-avatares');
      const bgcolor = getComputedStyle(tarjeta).backgroundColor;

      this.assert(header, `Tarjeta ${idx} tiene header`);
      this.assert(titulo, `Tarjeta ${idx} tiene título`);
      this.assert(engranaje, `Tarjeta ${idx} tiene engranaje`);
      this.assert(avatares, `Tarjeta ${idx} tiene avatares`);
      this.assert(bgcolor !== 'rgba(0, 0, 0, 0)', `Tarjeta ${idx} tiene color de fondo`);
    });
  }

  // TEST 8: Formulario crear lista
  async testFormCrearLista() {
    this.log('TEST 8: Verificando formulario crear lista', 'test');

    const form = document.getElementById('formCrearLista');
    const inputNombre = form?.querySelector('input[name="nombre"]');
    const inputColor = form?.querySelector('input[name="color"]');
    const btnCrear = document.querySelector('button[type="submit"][form="formCrearLista"]');

    this.assert(form, 'Formulario crear lista existe');
    this.assert(inputNombre, 'Input nombre existe');
    this.assert(inputColor, 'Input color existe');
    this.assert(btnCrear, 'Botón crear existe');

    if (inputNombre) {
      this.assert(inputNombre.hasAttribute('required'), 'Campo nombre es required');
      this.assert(inputNombre.getAttribute('maxlength') === '50', 'maxlength es 50');
    }

    if (inputColor) {
      this.assert(inputColor.getAttribute('type') === 'color', 'Input es type color');
    }
  }

  // TEST 9: Modal editar lista
  async testModalEditarLista() {
    this.log('TEST 9: Verificando modal editar lista', 'test');

    const modal = document.getElementById('modalEditarLista');
    const form = document.getElementById('formEditarLista');
    const inputNombre = form?.querySelector('input[name="nombre"]');
    const inputColor = form?.querySelector('input[name="color"]');
    const previewLista = document.getElementById('previewLista');
    const btnSalir = document.getElementById('btnSalirLista');
    const opcionesAjuste = document.querySelectorAll('.opcion-ajuste');

    this.assert(modal, 'Modal editar existe');
    this.assert(form, 'Formulario editar existe');
    this.assert(inputNombre, 'Input nombre existe');
    this.assert(inputColor, 'Input color existe');
    this.assert(previewLista, 'Preview de lista existe');
    this.assert(btnSalir, 'Botón "Salir" existe');
    this.assert(opcionesAjuste.length === 4, `Existen 4 opciones de ajuste`, opcionesAjuste.length);
  }

  // TEST 10: Viewport y responsividad
  async testViewport() {
    this.log('TEST 10: Verificando viewport y responsividad', 'test');

    const width = window.innerWidth;
    const height = window.innerHeight;

    this.log(`Viewport: ${width}x${height}px`, 'debug');

    // Abrir modal para que tenga dimensiones
    const manager = window.drawerListasManager;
    if (manager && !manager.estaAbierto) {
      manager.abrirModal();
      await this.wait(400);
    }

    const modal = document.querySelector('.modal');
    if (modal) {
      const modalWidth = modal.offsetWidth;
      const modalHeight = modal.offsetHeight;
      const modalPercent = ((modalWidth / width) * 100).toFixed(1);

      this.log(`Modal abierta: ${modalWidth}x${modalHeight}px (${modalPercent}% ancho)`, 'debug');
      this.assert(modalWidth > 0, 'Modal tiene ancho positivo', `${modalWidth}px`);
      this.assert(modalHeight > 0, 'Modal tiene alto positivo', `${modalHeight}px`);

      // Verificar que modales son full-width en mobile
      if (width < 768) {
        this.log('Detectado viewport mobile', 'debug');
        this.assert(modalWidth >= width - 20, 'Modal ocupa casi todo el ancho en mobile', `${modalPercent}%`);
      } else {
        this.log('Viewport desktop/tablet detectado', 'debug');
      }
    }

    // Cerrar modal después de test
    if (manager && manager.estaAbierto) {
      manager.cerrarModal();
      await this.wait(200);
    }
  }

  // TEST 11: Botones en footer
  async testFooterButtons() {
    this.log('TEST 11: Verificando botones en footer', 'test');

    const footers = document.querySelectorAll('.modal-footer');
    this.log(`Encontrados ${footers.length} footers`, 'debug');

    footers.forEach((footer, idx) => {
      const buttons = footer.querySelectorAll('button');
      this.assert(buttons.length > 0, `Footer ${idx} tiene botones`, buttons.length);

      buttons.forEach((btn, bIdx) => {
        const height = getComputedStyle(btn).height;
        const padding = getComputedStyle(btn).padding;
        this.assert(height === '40px', `Footer ${idx} Botón ${bIdx} altura correcta`, height);
      });
    });
  }

  // TEST 12: Console errors
  async testConsoleErrors() {
    this.log('TEST 12: Verificando errores en consola', 'test');

    // Esta es una verificación manual - los errores se ven en la consola
    this.log('Revisa la consola arriba para errores en rojo', 'warning');
  }

  // Ejecutar todos los tests
  async runAll() {
    this.startTime = Date.now();
    this.log('═══════════════════════════════════════════════════════════════', 'info');
    this.log('INICIANDO TEST SUITE COMPLETO - MODALES "MIS LISTAS"', 'test');
    this.log('═══════════════════════════════════════════════════════════════', 'info');

    await this.testDOMElements();
    await this.wait(100);
    await this.testManagerInstances();
    await this.wait(100);
    await this.testModalOpenClose();
    await this.wait(100);
    await this.testListasLoaded();
    await this.wait(100);
    await this.testModoEdicion();
    await this.wait(100);
    await this.testModalStyles();
    await this.wait(100);
    await this.testTarjetas();
    await this.wait(100);
    await this.testFormCrearLista();
    await this.wait(100);
    await this.testModalEditarLista();
    await this.wait(100);
    await this.testViewport();
    await this.wait(100);
    await this.testFooterButtons();
    await this.wait(100);
    await this.testConsoleErrors();

    this.endTime = Date.now();
    return this.printResults();
  }

  // Imprimir resultados
  printResults() {
    const duration = this.endTime - this.startTime;
    const passed = this.results.filter(r => r.status === 'PASS').length;
    const failed = this.results.filter(r => r.status === 'FAIL').length;
    const total = this.results.length;
    const percentage = ((passed / total) * 100).toFixed(1);

    this.log('═══════════════════════════════════════════════════════════════', 'info');
    this.log('RESULTADOS FINALES', 'info');
    this.log('═══════════════════════════════════════════════════════════════', 'info');

    this.log(`✅ TESTS PASADOS: ${passed}/${total}`, 'success');
    this.log(`❌ TESTS FALLIDOS: ${failed}/${total}`, failed > 0 ? 'error' : 'success');
    this.log(`📊 PORCENTAJE DE ÉXITO: ${percentage}%`, percentage === '100.0' ? 'success' : 'warning');
    this.log(`⏱️  TIEMPO TOTAL: ${duration}ms`, 'debug');

    if (failed === 0) {
      this.log('✅ ¡TODOS LOS TESTS PASARON CORRECTAMENTE!', 'success');
    } else {
      this.log('❌ ALGUNOS TESTS FALLARON - Revisa arriba para detalles', 'error');
      this.log('Tests fallidos:', 'warning');
      this.results.filter(r => r.status === 'FAIL').forEach(r => {
        this.log(`  • ${r.test} ${r.details ? `(${r.details})` : ''}`, 'warning');
      });
    }

    this.log('═══════════════════════════════════════════════════════════════', 'info');

    return {
      passed,
      failed,
      total,
      percentage: parseFloat(percentage),
      duration,
      success: failed === 0,
      results: this.results
    };
  }
}

// Auto-ejecutar si está en el documento
document.addEventListener('DOMContentLoaded', () => {
  window.drawerTests = new ModalTestSuite();

  console.log('%c🧪 MODAL TEST SUITE READY', 'color: #3F50B5; font-size: 14px; font-weight: bold;');
  console.log('%cEjecuta: window.drawerTests.runAll()', 'color: #666; font-style: italic;');
  console.log('%cO pruebas individuales: window.drawerTests.testDOMElements(), etc.', 'color: #666; font-style: italic;');
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ModalTestSuite;
}
