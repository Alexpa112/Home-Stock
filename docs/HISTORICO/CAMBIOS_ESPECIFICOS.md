# Cambios Específicos: Archivos a Modificar

## 📁 Archivos a Modificar

### **1. `stockhogar/static/style.css`**

#### Cambios en raíz y variables

```css
/* AÑADIR después de :root */

:root {
  --keyboard-height: 0px;
}

/* MODIFICAR: viewport fit para notch */
html {
  overflow-x: hidden;
  /* AÑADIR: */
  padding-left: 0;
  padding-right: 0;
}

body {
  margin: 0;
  padding: 0; /* AÑADIR */
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  min-height: 100svh;
  min-height: 100dvh;
  overflow-x: hidden;
  overscroll-behavior-x: none;
  -webkit-overflow-scrolling: touch;
  /* AÑADIR: */
  padding-left: 0;
  padding-right: 0;
}

/* MODIFICAR: mejorar transición cuando teclado se abre */
body.is-keyboard-open #appShell {
  transform: translateY(calc(-1 * min(var(--keyboard-offset, 0px), 20vh)));
  /* AÑADIR: */
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

#### Cambios en Modal

```css
/* REEMPLAZAR .modal-fondo */
.modal-fondo {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end; /* Modal al fondo */
  z-index: 100;
  padding: 0;
  overflow-y: auto;
}

/* REEMPLAZAR .modal */
.modal {
  background: var(--surface);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  width: 100%;
  max-width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
  padding: 0;
  /* Prevenir que el modal sea más ancho que la pantalla */
  box-sizing: border-box;
}

/* MODIFICAR: form dentro del modal */
.modal form {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 20px;
  gap: 12px;
  flex: 1;
}

/* MODIFICAR: acciones del modal */
.acciones-modal {
  display: flex;
  gap: 8px;
  margin-top: auto; /* Botones al final */
  padding: 12px 20px 20px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  /* Seguro en iPhone con notch */
  padding-bottom: calc(20px + max(0px, env(safe-area-inset-bottom)));
}

/* AÑADIR: cuando teclado está abierto */
body.keyboard-open .modal {
  max-height: calc(100vh - var(--keyboard-height, 0px) - 20px);
}

body.keyboard-open .modal form {
  max-height: calc(100vh - var(--keyboard-height, 0px) - 120px);
  /* Dejar espacio para header y botones */
}
```

#### Cambios en inputs

```css
/* MODIFICAR: inputs, selects en modales */
.modal input,
.modal select,
.modal textarea {
  font-size: 16px; /* ← CRÍTICO: previene zoom involuntario iOS */
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  width: 100%;
  min-height: 44px; /* Apple HIG standard */
  
  /* Touch-friendly */
  -webkit-appearance: none;
  appearance: none;
  
  /* Debugging: font antialiasing */
  -webkit-font-smoothing: antialiased;
  
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.modal input:focus,
.modal select:focus,
.modal textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* Prevenir zoom al enfocar input */
.modal input {
  touch-action: manipulation;
}
```

#### Cambios en botones

```css
/* MODIFICAR: botones en general */
button {
  touch-action: manipulation; /* Previene doble-tap zoom */
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

/* MODIFICAR: botones en modales */
.modal button,
.acciones-modal button {
  min-height: 44px;
  padding: 12px 16px;
  font-size: 16px;
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s ease;
}

.modal .primario,
.acciones-modal .primario {
  background: var(--accent);
  color: var(--accent-contrast);
}

.modal .primario:active,
.acciones-modal .primario:active {
  transform: scale(0.98);
}

.modal .secundario,
.acciones-modal .secundario {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
}
```

#### Cambios en FAB

```css
/* MODIFICAR: .fab */
.fab {
  position: fixed;
  bottom: 16px;
  right: 16px;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: var(--accent-contrast);
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  z-index: 4; /* Bajo modales pero sobre tabs */
  transition: all 0.2s ease;
  touch-action: manipulation;
  
  /* Seguro en iPhone con notch */
  bottom: calc(16px + max(0px, env(safe-area-inset-bottom)));
}

.fab:active {
  transform: scale(0.95);
}

/* Cuando teclado abierto, subir FAB */
body.keyboard-open .fab {
  bottom: calc(
    16px + 
    max(0px, env(safe-area-inset-bottom)) + 
    var(--keyboard-height, 0px)
  );
}
```

#### Cambios en Tabs

```css
/* MODIFICAR: .tabs */
.tabs {
  position: sticky;
  top: 0;
  z-index: 3; /* Bajo cabecera (5) pero sobre contenido */
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 0;
  padding: 0;
  border-radius: 0;
}

.tab {
  flex: 1;
  padding: 12px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.95rem;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
  touch-action: manipulation;
  min-height: 44px; /* Touch standard */
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab.activo {
  border-bottom-color: var(--accent);
  color: var(--accent);
}

.tab:active {
  background: var(--surface-2);
}
```

#### Nuevo: Selector de Listas

```css
/* NUEVA SECCIÓN: Selector de listas */
.selector-lista {
  padding: 8px 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 48px; /* Touch standard */
}

.lista-actual {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}

.lista-actual-icono {
  font-size: 1.2rem;
}

.lista-actual-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.lista-actual-nombre {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text);
}

.lista-actual-rol {
  font-size: 0.7rem;
  color: var(--text-soft);
  padding: 2px 6px;
  background: var(--accent-soft);
  border-radius: var(--radius-pill);
  width: fit-content;
}

.btn-cambiar-lista {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-pill);
  transition: background 0.2s ease;
  touch-action: manipulation;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-cambiar-lista:active {
  background: var(--surface);
}
```

### **2. `stockhogar/static/app.js`**

#### Añadir al inicio del archivo

```javascript
// ============ KEYBOARD MANAGEMENT ============

class KeyboardManager {
  constructor() {
    this.isOpen = false;
    this.height = 0;
    this.listeners = [];
    this.init();
  }

  init() {
    // iOS 13+ con visualViewport
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', () => this.detect());
      window.visualViewport.addEventListener('scroll', () => this.detect());
    }

    // Fallback: escuchar focus/blur en inputs
    document.addEventListener('focusin', (e) => {
      if (this.isInput(e.target)) {
        setTimeout(() => this.detect(), 50);
      }
    });

    document.addEventListener('focusout', () => {
      setTimeout(() => this.detect(), 100);
    });

    // Escuchar cambios del viewport
    window.addEventListener('resize', () => this.detect());
  }

  detect() {
    const visualViewport = window.visualViewport;
    if (!visualViewport) return;

    // Calcular altura del teclado
    const keyboardHeight = Math.max(
      0,
      window.innerHeight - visualViewport.height
    );

    // Actualizar CSS variable
    document.documentElement.style.setProperty(
      '--keyboard-height',
      `${Math.round(keyboardHeight)}px`
    );

    // Marcar clase en body
    if (keyboardHeight > 50) {
      if (!this.isOpen) {
        this.isOpen = true;
        document.body.classList.add('keyboard-open');
        this.notifyListeners('open', keyboardHeight);
      }
    } else {
      if (this.isOpen) {
        this.isOpen = false;
        document.body.classList.remove('keyboard-open');
        this.notifyListeners('close', 0);
      }
    }

    this.height = keyboardHeight;
  }

  isInput(el) {
    return ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
  }

  onKeyboardChange(callback) {
    this.listeners.push(callback);
  }

  notifyListeners(state, height) {
    this.listeners.forEach(cb => cb({ state, height }));
  }

  getHeight() {
    return this.height;
  }

  isKeyboardOpen() {
    return this.isOpen;
  }
}

// Inicializar globalmente
const keyboard = new KeyboardManager();

// ============ SCROLL & ZOOM PREVENTION ============

class ScrollManager {
  constructor() {
    this.init();
  }

  init() {
    let startX = 0;
    let startY = 0;

    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
      const currentX = e.touches[0].clientX;
      const diffX = Math.abs(currentX - startX);
      const diffY = Math.abs(e.touches[0].clientY - startY);

      // Si hay movimiento horizontal > 20px
      if (diffX > 20) {
        // Verificar si el elemento puede scrollear
        let el = e.target;
        while (el && el !== document.body) {
          if (el.scrollWidth > el.clientWidth) {
            // Elemento tiene scroll horizontal, permitir
            return;
          }
          el = el.parentElement;
        }

        // Si no hay elemento scrolleable y se detecta scroll horizontal significativo
        if (diffX > 50 && diffY < 20) {
          // Scroll horizontal puro, probablemente involuntario
          e.preventDefault();
        }
      }
    }, { passive: false });
  }
}

const scrollManager = new ScrollManager();

// ============ ZOOM PREVENTION ============

class ZoomManager {
  constructor() {
    this.init();
  }

  init() {
    // Prevenir pinch-zoom
    document.addEventListener('gesturestart', (e) => {
      e.preventDefault();
    }, { passive: false });

    // Prevenir doble-tap zoom (excepto en inputs)
    let lastTap = 0;
    document.addEventListener('touchend', (e) => {
      const now = Date.now();
      const timesince = now - lastTap;

      if (timesince < 300 && timesince > 0) {
        // Doble tap detectado
        if (!this.isInteractive(e.target)) {
          e.preventDefault();
        }
      }
      lastTap = now;
    }, { passive: false });
  }

  isInteractive(el) {
    const interactive = ['INPUT', 'TEXTAREA', 'BUTTON', 'A', 'SELECT'];
    return interactive.includes(el.tagName) || el.closest('button, a, input, textarea, select');
  }
}

const zoomManager = new ZoomManager();
```

#### Modificar aperturas de modal

```javascript
// Cuando se abre cualquier modal, asegurar que está en el viewport
function abrirModal(modalElement) {
  // Mostrar modal
  modalElement.hidden = false;
  document.body.classList.add('modal-open');

  // Hacer scroll para que sea visible (importante en móvil)
  setTimeout(() => {
    const modal = modalElement.querySelector('.modal');
    if (modal) {
      modal.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, 100);
}

function cerrarModal(modalElement) {
  modalElement.hidden = true;
  document.body.classList.remove('modal-open');
  document.activeElement?.blur(); // Cerrar teclado
}
```

---

### **3. `stockhogar/templates/index.html`**

#### Mantener viewport actual (es correcto):

```html
<meta name="viewport" content="width=device-width, initial-scale=1, 
  minimum-scale=1, maximum-scale=5, user-scalable=yes, 
  viewport-fit=cover, interactive-widget=resizes-content">
```

#### AÑADIR: Nueva estructura para selector de listas

Reemplazar:
```html
<div class="barra-espacio" id="barraEspacio">
  <button id="btnEspacios" class="chip-espacio" title="Cambiar de stock">
    <span id="espacioActualIcono">🏠</span>
    <span id="espacioActualNombre">Cargando...</span>
    <span class="chip-espacio-flecha">▾</span>
  </button>
</div>
```

Por:
```html
<div class="selector-lista" id="selectorLista">
  <div class="lista-actual" id="listaActualBtn" role="button" tabindex="0">
    <span class="lista-actual-icono" id="listaActualIcono">📋</span>
    <div class="lista-actual-info">
      <span class="lista-actual-nombre" id="listaActualNombre">Cargando...</span>
      <span class="lista-actual-rol" id="listaActualRol">PROPIETARIO</span>
    </div>
  </div>
  <button class="btn-cambiar-lista" id="btnCambiarLista" title="Cambiar lista" aria-label="Abrir selector de listas">
    ▾
  </button>
</div>
```

#### AÑADIR: Modal para cambiar de lista

Antes de cerrar `</div id="appShell">`, añadir:

```html
<div id="modalCambiarLista" class="modal-fondo" hidden>
  <form id="formCambiarLista" class="modal">
    <div style="padding: 20px; padding-bottom: 0;">
      <h2>Mis listas</h2>
    </div>

    <div id="seccionListasPopias" style="padding: 20px; padding-top: 10px;">
      <p style="font-size: 0.75rem; color: var(--text-soft); font-weight: bold; margin: 0 0 8px 0; text-transform: uppercase;">
        Propias
      </p>
      <div id="listasPropias"></div>
    </div>

    <div id="seccionListasCompartidas" style="padding: 20px; padding-top: 10px; display: none;">
      <p style="font-size: 0.75rem; color: var(--text-soft); font-weight: bold; margin: 0 0 8px 0; text-transform: uppercase;">
        Compartidas conmigo
      </p>
      <div id="listasCompartidas"></div>
    </div>

    <div class="acciones-modal">
      <button type="button" class="secundario" id="btnCerrarCambiarLista">Cerrar</button>
    </div>
  </form>
</div>
```

---

## 🔧 Cambios en Lógica (app.js)

### Nuevas funciones para gestionar selector de listas

```javascript
// Función para cargar listas compartidas (usa API nueva)
async function cargarMisListas() {
  try {
    const response = await fetch('/api/listas');
    const data = await response.json();
    
    renderizarSelectorListas(data.propias, data.compartidas);
  } catch (error) {
    console.error('Error cargando listas:', error);
  }
}

function renderizarSelectorListas(propias, compartidas) {
  const containerPropias = document.getElementById('listasPropias');
  const containerCompartidas = document.getElementById('listasCompartidas');
  const seccionCompartidas = document.getElementById('seccionListasCompartidas');

  // Limpiar
  containerPropias.innerHTML = '';
  containerCompartidas.innerHTML = '';

  // Renderizar propias
  propias.forEach(lista => {
    const item = crearItemLista(lista);
    containerPropias.appendChild(item);
  });

  // Renderizar compartidas
  if (compartidas.length > 0) {
    seccionCompartidas.style.display = 'block';
    compartidas.forEach(lista => {
      const item = crearItemLista(lista);
      containerCompartidas.appendChild(item);
    });
  }
}

function crearItemLista(lista) {
  const div = document.createElement('div');
  div.className = 'lista-item';
  div.style.cssText = `
    padding: 12px;
    background: var(--surface);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 56px;
    margin-bottom: 8px;
    transition: all 0.2s ease;
  `;

  const icono = document.createElement('span');
  icono.textContent = lista.icono || '📋';
  icono.style.fontSize = '1.2rem';

  const info = document.createElement('div');
  info.style.cssText = 'flex: 1;';
  info.innerHTML = `
    <div style="font-weight: 600; font-size: 0.95rem;">${lista.nombre}</div>
    <div style="font-size: 0.75rem; color: var(--text-soft);">${lista.mi_rol.toUpperCase()}</div>
  `;

  div.appendChild(icono);
  div.appendChild(info);

  // Click handler
  div.addEventListener('click', () => {
    cambiarLista(lista.id);
  });

  div.addEventListener('active', () => {
    div.style.background = 'var(--surface-2)';
  });

  return div;
}

async function cambiarLista(listaId) {
  // Aquí iría la lógica para cambiar la lista actual
  // y recargar el contenido
  localStorage.setItem('lista-actual', listaId);
  
  // Cerrar modal
  document.getElementById('modalCambiarLista').hidden = true;
  
  // Recargar datos
  cargarProductosStock();
  cargarListaCompra();
  
  // Actualizar selector visible
  cargarMisListas();
}
```

---

## ✅ Checklist de Cambios

- [ ] **CSS:** Variables `--keyboard-height`
- [ ] **CSS:** Modal redimensionable con teclado
- [ ] **CSS:** Inputs con font-size 16px
- [ ] **CSS:** Items con min-height 56px
- [ ] **CSS:** FAB movible con teclado
- [ ] **CSS:** Prevención de scroll lateral
- [ ] **JS:** Detector de teclado (KeyboardManager)
- [ ] **JS:** Prevención de scroll lateral (ScrollManager)
- [ ] **JS:** Prevención de zoom (ZoomManager)
- [ ] **HTML:** Nuevo selector de listas
- [ ] **HTML:** Modal para cambiar lista
- [ ] **JS:** Funciones para cargar/cambiar listas
- [ ] **Testing:** iOS 18 Safari
- [ ] **Testing:** Android Chrome/Firefox

