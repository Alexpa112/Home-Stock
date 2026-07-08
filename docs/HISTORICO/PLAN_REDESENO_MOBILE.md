# Plan de Rediseño Mobile-First - StockHogar

## 🎯 Objetivos

1. **Solucionar problema crítico:** Modal + teclado en iOS (botones desaparecen)
2. **Eliminar UX problems:** Scroll lateral, zoom involuntario
3. **Optimizar para casos de uso:**
   - En casa: consultar stock tranquilo
   - En supermercado: marcar compras rápido
4. **Integrar listas compartidas** de forma natural
5. **Mantener funcionalidad:** escaneo de ticket, OCR, etc

---

## 📐 Estrategia: Mobile-First + Progressive Enhancement

### Principios de Diseño

1. **Viewport limpio:** Evitar scroll lateral completamente
2. **Teclado consciente:** Modales redimensionables, scroll interno
3. **Touch-first:** Botones grandes, espacios amplios
4. **Performance:** Animaciones suaves, sin lag

---

## 🏗️ Cambios Estructurales Principales

### **1. VIEWPORT & META TAGS (prevenir zoom involuntario)**

**Problema actual:**
```html
<meta name="viewport" content="width=device-width, initial-scale=1, 
  minimum-scale=1, maximum-scale=1, user-scalable=no, ...">
```

**Problema:** `user-scalable=no` es agresivo y dificulta accesibilidad.

**Solución:**
```html
<meta name="viewport" content="width=device-width, initial-scale=1, 
  minimum-scale=1, maximum-scale=5, user-scalable=yes, 
  viewport-fit=cover">
```

- Permitir zoom (hasta 5x) para accesibilidad
- El resto del CSS evitará que se active sin querer
- Usar `touch-action: manipulation` en botones/inputs

---

### **2. LAYOUT BASE (eliminar scroll lateral)**

**Cambios en CSS:**

```css
html, body {
  width: 100%;
  height: 100%;
  overflow-x: hidden;  /* ✓ mantener */
  overflow-y: auto;
  margin: 0;
  padding: 0;
}

#appShell {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  /* Prevenir horizontal scroll */
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
}

/* ✓ Importante: sin padding horizontal en body */
body {
  padding-left: 0;
  padding-right: 0;
}
```

**Resultado:** Cero scroll lateral

---

### **3. MODALES (solucionar problema del teclado iOS)**

**Problema actual:** Modal fixed, no se redimensiona con teclado

**Solución: Dos cambios**

#### **A) Detectar teclado abierto**

```javascript
// Detectar cuando se abre el teclado en iOS/Android
const visualViewport = window.visualViewport;

visualViewport?.addEventListener('resize', () => {
  const keyboardHeight = window.innerHeight - visualViewport.height;
  document.documentElement.style.setProperty(
    '--keyboard-height', 
    `${keyboardHeight}px`
  );
  
  // Marcar que el teclado está abierto
  if (keyboardHeight > 50) {
    document.body.classList.add('keyboard-open');
  } else {
    document.body.classList.remove('keyboard-open');
  }
});
```

#### **B) CSS para modal inteligente**

```css
.modal-fondo {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  /* ↑ Modal siempre al final de la pantalla */
  z-index: 100;
  padding: 16px;
  padding-bottom: max(16px, env(safe-area-inset-bottom));
}

.modal {
  background: var(--surface);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  width: 100%;
  max-width: 100%;
  max-height: 90vh;
  /* ↑ Máximo 90% de la pantalla disponible */
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
}

.modal form {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  /* ↑ Contenido scrolleable si es necesario */
  padding: 20px;
  gap: 12px;
}

.acciones-modal {
  display: flex;
  gap: 8px;
  margin-top: auto;
  /* ↑ Botones siempre al final */
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

/* Cuando el teclado está abierto */
body.keyboard-open .modal {
  max-height: calc(100vh - var(--keyboard-height, 0px) - 32px);
}
```

**Resultado:** 
- Modal se redimensiona automáticamente
- Botones SIEMPRE visibles
- Contenido scrolleable si es muy largo
- Teclado no tapa nada

---

### **4. TABS (Stock vs Compra)**

**Problema:** En móvil, los tabs a veces ocupan mucho espacio

**Solución: Sticky tabs inteligentes**

```css
.tabs {
  position: sticky;
  top: 0;
  z-index: 3;
  /* ↑ Por debajo de cabecera (z:5) pero sobre contenido */
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 0;
  padding: 0;
  border-radius: 0;
}

.tab {
  flex: 1;
  /* ↑ Ocupan todo el ancho disponible */
  padding: 12px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.95rem;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
}

.tab.activo {
  border-bottom-color: var(--accent);
  color: var(--accent);
}

@media (max-width: 380px) {
  .tab {
    padding: 10px 6px;
    font-size: 0.85rem;
  }
}
```

**Resultado:** Tabs compactos, siempre accesibles

---

### **5. SELECTOR DE LISTAS (nueva feature)**

**Ubicación:** Donde ahora está "selector de espacio"

**Diseño:**

```css
.selector-lista {
  padding: 8px 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.lista-actual {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
}

.lista-actual-nombre {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text);
}

.lista-actual-rol {
  font-size: 0.75rem;
  color: var(--text-soft);
  padding: 2px 6px;
  background: var(--accent-soft);
  border-radius: var(--radius-pill);
}

.btn-cambiar-lista {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
}
```

**Modal para cambiar lista:**
- Muestra listas propias + compartidas
- Icono + nombre + rol (Propietario/Editar/Ver)
- Separadas visualmente
- Tap para cambiar

---

### **6. BOTÓN FLOTANTE (FAB)**

**Posicionamiento seguro en iOS:**

```css
.fab {
  position: fixed;
  bottom: calc(16px + max(0px, env(safe-area-inset-bottom)));
  /* ↑ Respeta notch en iPhone */
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
  z-index: 4;
  /* ↑ Por encima de tabs (3) pero bajo modales (100) */
  transition: all 0.2s ease;
}

.fab:active {
  transform: scale(0.95);
}

/* Cuando teclado está abierto, subir el FAB */
body.keyboard-open .fab {
  bottom: calc(
    16px + 
    max(0px, env(safe-area-inset-bottom)) + 
    var(--keyboard-height, 0px)
  );
}
```

**Resultado:** FAB siempre visible y accesible

---

### **7. INPUTS EN MODALES (grande y fácil de tocar)**

```css
.modal input,
.modal select,
.modal textarea {
  font-size: 16px;
  /* ↑ Crucial: 16px = previene zoom involuntario en iOS */
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  width: 100%;
  
  /* Touch-friendly */
  min-height: 44px;
  /* ↑ Apple HIG: mínimo 44x44 para touch */
  
  transition: border-color 0.2s ease;
}

.modal input:focus,
.modal select:focus,
.modal textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
```

**Resultado:** Inputs fáciles de tocar, sin zoom involuntario

---

### **8. CONTENIDO PRINCIPAL (Stock / Lista de Compra)**

```css
section[id^="vista"] {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  /* ↑ Scroll suave en iOS */
  padding: 12px 16px;
  padding-bottom: 80px;
  /* ↑ Espacio para el FAB */
}

/* Lista de productos */
.lista {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Cada producto/item */
.item {
  padding: 12px;
  background: var(--surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  min-height: 56px;
  /* ↑ Touch-friendly */
}

.item:active {
  background: var(--surface-2);
  transform: scale(0.98);
}
```

**Resultado:** Items fáciles de tocar, feedback inmediato

---

## 🔧 Cambios JavaScript Necesarios

### **Detector de Teclado (crítico)**

```javascript
class KeyboardManager {
  constructor() {
    this.isOpen = false;
    this.height = 0;
    this.init();
  }

  init() {
    // iOS 13+ con visualViewport
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', () => this.detect());
      window.visualViewport.addEventListener('scroll', () => this.detect());
    }

    // Fallback: escuchar focus/blur
    document.addEventListener('focusin', (e) => {
      if (this.isInput(e.target)) {
        setTimeout(() => this.detect(), 100);
      }
    });

    document.addEventListener('focusout', () => {
      setTimeout(() => this.detect(), 100);
    });
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
      `${keyboardHeight}px`
    );

    // Marcar clase
    if (keyboardHeight > 50) {
      if (!this.isOpen) {
        this.isOpen = true;
        document.body.classList.add('keyboard-open');
      }
    } else {
      if (this.isOpen) {
        this.isOpen = false;
        document.body.classList.remove('keyboard-open');
      }
    }
  }

  isInput(el) {
    return ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
  }
}

// Inicializar
const keyboard = new KeyboardManager();
```

### **Prevenir Scroll Lateral**

```javascript
class ScrollManager {
  constructor() {
    this.init();
  }

  init() {
    let startX = 0;
    let currentX = 0;

    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      currentX = startX;
    });

    document.addEventListener('touchmove', (e) => {
      currentX = e.touches[0].clientX;
      const diff = Math.abs(currentX - startX);

      // Si se detecta scroll horizontal
      if (diff > 10) {
        // Verificar si el elemento puede scrollear horizontalmente
        let el = e.target;
        while (el && el !== document) {
          if (el.scrollWidth > el.clientWidth) {
            // Permitir scroll en ese elemento
            return;
          }
          el = el.parentElement;
        }

        // Si no hay elemento scrolleable, prevenir
        if (diff > 50) {
          e.preventDefault();
        }
      }
    }, { passive: false });
  }
}

const scroll = new ScrollManager();
```

### **Prevenir Zoom Involuntario**

```javascript
class ZoomManager {
  constructor() {
    this.init();
  }

  init() {
    // Prevenir pinch-zoom
    document.addEventListener(
      'gesturestart',
      (e) => e.preventDefault(),
      { passive: false }
    );

    // Prevenir doble-tap zoom (pero permitir selección)
    let lastTap = 0;
    document.addEventListener('touchend', (e) => {
      const now = Date.now();
      const timesince = now - lastTap;

      if (timesince < 500 && timesince > 0) {
        // Doble tap en menos de 500ms = zoom attempt
        // Pero permitir si es en un input
        if (!this.isInput(e.target)) {
          e.preventDefault();
        }
      }
      lastTap = now;
    }, { passive: false });
  }

  isInput(el) {
    return ['INPUT', 'TEXTAREA', 'BUTTON', 'A'].includes(el.tagName);
  }
}

const zoom = new ZoomManager();
```

---

## 📱 Respuesta a Cada Problema

| Problema | Causa | Solución |
|----------|-------|----------|
| **Modal + teclado (iOS)** | Modal fixed, no redimensionable | `visualViewport` + CSS condicional |
| **Botones desaparecen** | Teclado cubre modal | `flex-direction: column` + `margin-top: auto` |
| **Scroll lateral** | Contenido más ancho que viewport | `overflow-x: hidden` + `max-width: 100%` |
| **Zoom involuntario** | Double-tap, pinch-zoom | `touch-action: manipulation` + JS preventivo |
| **Inputs muy pequeños** | Font-size < 16px | Siempre 16px en inputs |
| **Items difíciles de tocar** | Altura < 44px | `min-height: 56px` en items |

---

## 🎨 Orden de Implementación

### **Fase 1: Solucionar problemas críticos (iOS teclado)**
1. Detector de teclado (JS)
2. Modal inteligente (CSS)
3. Botones siempre visibles

### **Fase 2: Eliminar UX problems**
1. Prevenir scroll lateral (JS)
2. Prevenir zoom involuntario (JS)
3. Verificar en iOS 18 Safari

### **Fase 3: Integrar listas compartidas**
1. Selector de lista visible
2. Modal de cambio de lista
3. Mostrar rol del usuario

### **Fase 4: Optimización**
1. Test en Android
2. Ajustes finales
3. Documentación

---

## ✅ Checklist de Cumplimiento

- [ ] Modal no se cubre con teclado en iOS
- [ ] Botones de modal siempre visibles
- [ ] Zero scroll lateral
- [ ] Sin zoom involuntario
- [ ] Inputs con font-size 16px
- [ ] Items con min-height 56px
- [ ] FAB siempre accesible
- [ ] Selector de listas funcional
- [ ] Testeo en iOS 18 Safari
- [ ] Testeo en Android

---

## 📚 Referencia de Estándares

- **Apple HIG:** Min 44x44 para elementos interactivos
- **Google Material:** Min 48x48 para toque
- **WCAG 2.1:** Accesibilidad garantizada
- **iOS:** Notch, safe areas, visualViewport
- **Android:** Predictable scroll, gesture recognition

