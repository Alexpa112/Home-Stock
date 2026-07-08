# 📍 REFERENCIA RÁPIDA - UBICACIÓN DE TODAS LAS COSAS

## 🎯 ESTRUCTURA HTML DE MODALES (Correcta)
```
<div id="modalXXX" class="modal-fondo" hidden>
  <div class="modal">
    <div class="modal-header">
      <h2>Título</h2>
    </div>
    <div class="modal-content">
      <!-- Contenido (form o div) aquí -->
    </div>
    <div class="modal-footer">
      <button>Botón</button>
    </div>
  </div>
</div>
```

---

## 📋 UBICACIÓN DE MODALES EN HTML (templates/index.html)

| Modal | ID | Línea | Estado |
|-------|----|----|--------|
| Editar/Nuevo Producto | `#modal` | 77 | ✅ Estructura correcta |
| Añadir a Compras | `#modalCompra` | 126 | ✅ Estructura correcta |
| Catálogo | `#modalCatalogo` | 159 | ✅ Estructura correcta |
| Ajustes | `#modalAjustes` | 173 | ✅ Estructura correcta |
| Escanear Ticket | `#modalTicket` | 202 | ✅ Estructura correcta |
| Categorías | `#modalCategorias` | 241 | ✅ Estructura correcta |
| Nuevo Stock | `#modalEspacioForm` | 278 | ✅ Estructura correcta |
| Cambiar Lista | `#modalCambiarLista` | 312 | ✅ Estructura correcta |
| Selector Iconos | `#modalSelectorIconos` | 321 | ✅ Especial (pequeña) |
| Mis Listas | `#modalMisListas` | 333 | ✅ Estructura correcta |
| Crear Nueva Lista | `#modalCrearLista` | 375 | ✅ Estructura correcta |

---

## 🎨 CSS CRÍTICO - ORDEN DE CARGA Y CASCADA

### ⚠️ IMPORTANTE: `responsive.css` OVERRIDE `style.css`
Los archivos se cargan en este orden:
1. `style.css` (línea 719-796: `.modal-fondo`, `.modal`, `.modal-header`, etc.)
2. `responsive.css` (línea 44-68: ANULA `.modal-fondo`, `.modal`)

**SI MODIFICAS ALGO EN STYLE.CSS, VERIFICA QUE NO ESTÉ OVERRIDEADO EN RESPONSIVE.CSS**

### style.css - Reglas Base

| Clase | Línea | Qué hace |
|-------|-------|----------|
| `.modal-fondo` | 719 | Contenedor fixed, flex, overlay |
| `.modal` | 738 | Contenedor blanco, max-height 90vh |
| `.modal-header` | 750 | Header con border-bottom |
| `.modal-content` | 760 | Contenido con flex: 1 y overflow-y: auto |
| `.modal-footer` | 770 | Footer con flex layout, flex-wrap: wrap |
| `.modal-footer button` | 780 | Botones responsive: flex: 1; min-width: 100px |
| `.modal-ticket` | 1091 | max-height: 80vh |
| `.modal-catalogo` | 1093 | max-height: 85vh |

**style.css ACTUAL (.modal-fondo línea 719):**
```css
.modal-fondo {
  position: fixed;
  inset: 0;
  background: rgba(20, 16, 10, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;     /* ← ARRIBA */
  z-index: 100;
  padding-top: 5vh;                /* ← 5% espacio superior */
  padding-left: 16px;
  padding-right: 16px;
  padding-bottom: 16px;
  min-height: 100vh;               /* ← Ocupa pantalla completa */
  overscroll-behavior: contain;
  overflow: hidden;                /* ← Sin scroll contenedor */
}
```

### responsive.css - Reglas que OVERRIDE

| Clase | Línea | Qué hace | IMPORTANTE |
|-------|-------|----------|-----------|
| `.modal-fondo` | 44 | **ANULA style.css** | ⚠️ Tiene justify-content, padding, overflow |
| `.modal` | 59 | max-height: 85dvh (dinámico) | Reemplaza 90vh de style.css |

**responsive.css ACTUAL (.modal-fondo línea 44):**
```css
.modal-fondo {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;     /* ← CORRECTO (arriba) */
  padding: 5vh 16px 16px 16px;     /* ← CORRECTO (5% top) */
  min-height: 100vh;               /* ← CORRECTO */
  overflow: hidden;                /* ← CORRECTO */
}
```

---

## ⚙️ JAVASCRIPT - FUNCIONES IMPORTANTES

### app.js

| Función | Línea | Qué hace |
|---------|-------|----------|
| `habilitarCierreSeguro()` | 341 | Click en fondo → cierra modal |
| `habilitarDragDown()` | 352 | Drag hacia abajo > 80px → cierra modal |
| Llamada para modalAjustes | 1588 | `habilitarDragDown(modalAjustesContenedor, ...)` |
| Llamada para modalTicket | 1722 | `habilitarDragDown(modalTicketContenedor, ...)` |

### drawer-listas.js

| Función | Línea | Qué hace |
|---------|-------|----------|
| `setupDragDown()` | 198 | Setup de drag-down para modalMisListas |
| Llamada en `abrirModal()` | 189 | Se ejecuta cada vez que abre la modal |

---

## ✅ CHECKLIST - QUÉ FUNCIONA

- [x] Modales posicionadas al 5% del top (`padding-top: 5vh`)
- [x] `justify-content: flex-start` (ARRIBA, no centrado)
- [x] `min-height: 100vh` (ocupa pantalla completa)
- [x] `overflow: hidden` en `.modal-fondo` (no scroll contenedor)
- [x] Estructura header/content/footer en TODAS las modales
- [x] Botones responsive en `.modal-footer`
- [x] Cerrar al pulsar fuera (click-outside)
- [x] Cerrar al arrastrar hacia abajo (drag-down > 80px)
- [x] Sin botón Cancel en Ajustes
- [x] Mis Listas sin drawer overlay

---

## 🚨 COSAS A TENER EN CUENTA

1. **`responsive.css` ANULA `style.css`** - Si cambias algo en style.css para `.modal-fondo` o `.modal`, VERIFICA que responsive.css no lo esté overrideando

2. **Todas las modales deben tener estructura header/content/footer** - Si una modal no sigue esta estructura, los botones se van al footer y el contenido scrollea mal

3. **`padding-top: 5vh` es para TODAS las pantallas** - Las media queries en style.css no deben tocar `.modal-fondo`

4. **Los botones en `.modal-footer`** deben tener `flex: 1; min-width: 100px; min-height: 44px;`

5. **Dragging en mobile**: `habilitarDragDown()` solo funciona en touch events (`touchstart`, `touchmove`, `touchend`)

---

## 🎯 NUEVO DISEÑO - "MIS LISTAS" CON TARJETAS (✅ IMPLEMENTADO)

### Flujo de Navegación:
```
Mis Listas (tarjetas)
├─ Click en tarjeta → Abre esa lista
├─ Click en ⚙️ engranaje → Modal "Ajustes de la lista"
│  └─ Botón ROJO "Eliminar lista" dentro
└─ "+ Nueva lista" (final) → Modal "Crear lista"
   └─ "Siguiente" → Modal "Compartir lista"
```

### Estructura de Tarjeta (modalMisListas):
```html
<div class="tarjeta-lista" data-lista-id="123">
  <div class="tarjeta-header">
    <h3>Nombre de lista</h3>
    <button class="btn-editar-lista">⚙️</button>
  </div>
  <div class="tarjeta-contenido">
    <!-- Decoraciones/ilustraciones -->
  </div>
  <div class="tarjeta-avatares">
    <!-- Avatares de usuarios -->
  </div>
</div>
```

### CSS a crear:
- `.grid-listas` - Grid RESPONSIVO:
  - Mobile (<600px): 2 columnas
  - Tablet (600-900px): 3 columnas
  - Desktop (900-1400px): 4 columnas
  - Desktop grande (>1400px): 5 columnas
- `.tarjeta-lista` - contenedor con color variable, border-radius, sombra
- `.tarjeta-header` - nombre + ⚙️ engranaje
- `.tarjeta-contenido` - área de decoraciones
- `.tarjeta-avatares` - avatares overflow
- `.btn-crear-lista` - pegado al final (dentro modal-content)

### JavaScript a agregar:
- Event listener en tarjetas (click) → abre lista
- Event listener en ⚙️ (click) → abre modal Ajustes

---

## 📝 ÚLTIMA ACTUALIZACIÓN
**Fecha:** 2026-07-08  
**Cambios REALIZADOS:** 

### ✅ HTML (index.html línea 352-372)
- Cambié `<ul id="listaListas">` por `<div id="listaListas" class="grid-listas">`
- Moví "+ Nueva lista" desde footer a modal-content (antes del footer)
- Footer ahora solo tiene botón "Listo"

### ✅ CSS (style.css línea 1305+)
- `.grid-listas` - Grid responsive:
  - Mobile (<600px): 2 columnas
  - Tablet (600-900px): 3 columnas
  - Desktop (900-1400px): 4 columnas
  - Desktop grande (>1400px): 5 columnas
- `.tarjeta-lista` - Tarjetas cuadradas (aspect-ratio: 1) con color dinámico
- `.tarjeta-header` - Nombre + ⚙️ engranaje
- `.btn-editar-tarjeta` - Botón engranaje
- `.tarjeta-avatares` - Avatares al pie
- `.btn-crear-lista` - Botón "+ Nueva lista"

### ✅ JavaScript (drawer-listas.js)
- `crearElementoLista()` - Ahora crea `<div class="tarjeta-lista">` en lugar de `<li>`
- Click en tarjeta → abre esa lista
- Click en ⚙️ → abre ajustes (método `abrirAjustesLista()` agregado)
- `renderizarListas()` - Adaptado para grid

**Estado:** ✅ IMPLEMENTADO Y LISTO PARA PROBAR
