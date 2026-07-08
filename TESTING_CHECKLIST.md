# Testing Checklist: Rediseño Mobile-First

**Servidor:** http://localhost:5000  
**Probado en:** iOS 18 Safari (DevTools mobile viewport)

---

## ✅ Checklist de Testing

### **1. Viewport y Configuración**
- [ ] Abrir DevTools (F12 / Cmd+Option+I)
- [ ] Toggle device toolbar (Ctrl+Shift+M)
- [ ] Seleccionar iPhone 15 (390x844)
- [ ] Refrescar página (Cmd+R)

### **2. Problemas Resueltos**

#### **A) Modal + Teclado (iOS)**
```
Pasos:
1. Tap en botón "+" (FAB)
2. Modal abre
3. Tap en "Nombre" (primer input)
4. Teclado virtual se abre
5. ✅ Verificar: Botones "Cancelar" y "Guardar" SIGUEN VISIBLES
6. ✅ Verificar: Modal se redimensiona (no desaparece)
7. ✅ Verificar: Contenido es scrolleable si es muy largo
```

#### **B) Scroll Lateral**
```
Pasos:
1. Refrescar página en mobile
2. Intentar deslizar horizontalmente
3. ✅ Verificar: NO hay scroll lateral
4. ✅ Verificar: Solo se puede hacer scroll vertical
```

#### **C) Zoom Involuntario**
```
Pasos:
1. Double-tap en cualquier área (NO en input)
2. ✅ Verificar: NO hace zoom
3. Intentar pinch-zoom (si tienes trackpad)
4. ✅ Verificar: NO hace zoom
```

#### **D) Inputs Touch-Friendly**
```
Pasos:
1. Tap en cualquier input modal
2. ✅ Verificar: Input tiene min-height 44px
3. ✅ Verificar: Font-size es 16px (no más pequeño)
4. ✅ Verificar: Fácil de tocar sin errores
```

#### **E) FAB Sube con Teclado**
```
Pasos:
1. Abrir modal (tap en +)
2. Tap en input
3. Teclado se abre
4. ✅ Verificar: FAB sube automáticamente
5. ✅ Verificar: FAB NO queda bajo el teclado
6. Cierra el modal
7. ✅ Verificar: FAB vuelve a posición original
```

#### **F) Tabs Sticky**
```
Pasos:
1. En la app principal (no en modal)
2. Scroll hacia abajo
3. ✅ Verificar: Tabs (Stock | Compra) se quedan visibles arriba
4. Scroll hacia arriba
5. ✅ Verificar: Cabecera se queda pegada
```

### **3. Nueva Feature: Selector de Listas**

#### **G) Selector Visible**
```
Pasos:
1. Página principal carga
2. ✅ Verificar: Hay una barra nueva bajo la cabecera
3. ✅ Verificar: Muestra icono + nombre + rol
4. Tap en barra
5. ✅ Verificar: Se abre MODAL (no dropdown)
```

#### **H) Modal Cambiar Lista**
```
Pasos:
1. Tap en selector de lista
2. Modal abre
3. ✅ Verificar: Muestra "Propias"
4. ✅ Verificar: Muestra "Compartidas conmigo" (si existen)
5. ✅ Verificar: Cada lista muestra icono + nombre + rol
6. Tap en una lista
7. ✅ Verificar: Modal se cierra
8. ✅ Verificar: Selector actualiza
```

### **4. Animaciones (150ms)**

```
Pasos:
1. Abrir modal
2. ✅ Verificar: Transición suave (no instant)
3. Cambiar de lista
4. ✅ Verificar: Transición suave (150ms aprox)
```

### **5. Dark Mode**

```
Pasos:
1. Tap en icono 🌙 (cambiar tema)
2. ✅ Verificar: Todo se ve bien en dark mode
3. Abrir modales
4. ✅ Verificar: Modales se adaptan a dark mode
```

### **6. Responsividad en otros tamaños**

```
Pasos:
1. Cambiar a diferentes devices en DevTools:
   - iPad (768x1024)
   - Desktop (1280x800)
2. ✅ Verificar: Layout se adapta correctamente
3. ✅ Verificar: No hay overflow horizontal
```

---

## 🎨 Visual Checklist

**Modal en estado normal (sin teclado):**
```
┌──────────────────────────┐
│ Nuevo producto           │
├──────────────────────────┤
│ Nombre: [input 44px+]    │
│ Categoría: [select]      │
│ Icono: [selector]        │
│ Cantidad: [input]        │
│ ...                      │
│ (scrolleable si necesario)
│                          │
├──────────────────────────┤
│ Cancelar  | Guardar      │ ← Siempre visible
└──────────────────────────┘
```

**Modal con teclado abierto:**
```
┌──────────────────────────┐
│ Nuevo producto           │
├──────────────────────────┤
│ Nombre: [input]          │  ← scrolleable
│ Categoría: [select]      │
│                          │
├──────────────────────────┤
│ Cancelar  | Guardar      │ ← Siempre visible, sin cubrir
├──────────────────────────┤
│                          │
│  ⌨️ TECLADO VIRTUAL      │ ← No cubre nada
│                          │
└──────────────────────────┘
```

---

## 📊 Resultados Esperados

| Test | Esperado | Resultado | ✅/❌ |
|------|----------|-----------|-------|
| Modal + teclado | Botones visibles | | |
| Scroll lateral | Prevenido | | |
| Zoom involuntario | Prevenido | | |
| Inputs 44px+ | Fácil tocar | | |
| FAB sube | Automático | | |
| Tabs sticky | Arriba siempre | | |
| Selector lista | Visible | | |
| Modal listas | Funciona | | |
| Animaciones 150ms | Suaves | | |
| Dark mode | Se adapta | | |
| Responsive | OK en todos | | |

---

## 🐛 Si algo falla

1. **Abre DevTools (F12)**
2. **Vete a Console**
3. **Busca errores rojos (si los hay)**
4. **Nota el error exacto**
5. **Reporta:**
   - Paso que falla
   - Qué esperas vs qué ves
   - Error de console (si existe)

---

## 📱 Simulación de Teclado en DevTools

Chrome desktop simula el teclado virtual si:
1. DevTools abierto
2. Device toolbar activado (mobile)
3. Tap en input (click en simulado)
4. El "teclado" aparece como overlay

⚠️ **Nota:** En desktop, el teclado virtual NO es real (no sube la página como en iOS). 
Para testing real de teclado, necesitas dispositivo iOS físico.

---

**Estado:** Listo para testing ✅  
**Fecha:** 2026-01-08  
**Cambios implementados:** CSS + HTML + JS  
