# 🧪 PRUEBAS EXHAUSTIVAS - Drawer Lateral (Opción 2)

## Fecha: 2026-07-08
## Estado: INICIANDO PRUEBAS

---

## 📋 CHECKLIST DE PRUEBAS

### FASE 1: FUNCIONALIDAD BÁSICA DEL DRAWER

#### 1.1 Abrir Drawer
- [ ] Click en header "📋 Mi inventario ▾" abre drawer
- [ ] Click en botón "▾" abre drawer
- [ ] Drawer se desliza desde izquierda suavemente
- [ ] Fondo oscuro aparece detrás del drawer
- [ ] Body recibe clase `drawer-open` para bloquear scroll

#### 1.2 Cerrar Drawer
- [ ] Click en botón ✕ cierra drawer
- [ ] Click en fondo oscuro cierra drawer
- [ ] Tecla ESC cierra drawer
- [ ] Swipe izquierda cierra drawer (móvil)
- [ ] Drawer se desliza hacia izquierda suavemente
- [ ] Fondo oscuro desaparece

#### 1.3 Contenido del Drawer
- [ ] Header "Mis Listas" visible
- [ ] Botón ✕ para cerrar visible
- [ ] Lista de listas cargada desde API
- [ ] Botón "+ Nueva lista" al final
- [ ] Items vacíos muestran mensaje "Sin listas aún"

### FASE 2: CARGANDO LISTAS

#### 2.1 API Integration
- [ ] GET /api/listas retorna lista de listas
- [ ] GET /api/listas/actual retorna lista actual
- [ ] Cada lista muestra: icono, nombre, rol
- [ ] Rol "PROPIETARIO" para listas del usuario
- [ ] Rol "COMPARTIDA" para listas compartidas

#### 2.2 Renderizado
- [ ] Cada item es un botón clickeable (44px mínimo altura)
- [ ] Item activo está resaltado con clase `active`
- [ ] Icono visible (emoji 24px)
- [ ] Nombre en texto normal
- [ ] Rol en texto pequeño

#### 2.3 Accesibilidad
- [ ] Items tienen `role="button"` y `tabindex="0"`
- [ ] Navegable con Tab y Enter
- [ ] Items reciben focus visible
- [ ] Screen reader puede leer contenido

### FASE 3: CAMBIAR DE LISTA

#### 3.1 Click en Lista
- [ ] Click en lista abre POST /api/listas/{id}/seleccionar
- [ ] Drawer se cierra automáticamente
- [ ] Lista actual se marca con clase `active`
- [ ] Página recarga para mostrar contenido de nueva lista

#### 3.2 Feedback Visual
- [ ] Item seleccionado está resaltado
- [ ] Transición suave al cambiar (300ms)
- [ ] No hay saltos visuales

### FASE 4: CREAR NUEVA LISTA

#### 4.1 Abrir Modal
- [ ] Click en "+ Nueva lista" abre modal
- [ ] Modal aparece con animación slideUp
- [ ] Drawer se cierra antes de abrir modal
- [ ] Formulario está vacío y listo

#### 4.2 Formulario de Crear Lista
- [ ] Campo "Nombre" (2-50 caracteres)
- [ ] Campo "Icono" con preview
- [ ] Botón "Cambiar icono" para selector
- [ ] Botones: Cancelar, Crear lista

#### 4.3 Validación
- [ ] Campo nombre es requerido
- [ ] Mínimo 2 caracteres
- [ ] Máximo 50 caracteres
- [ ] Error messages claros si no pasa validación

#### 4.4 Crear Lista
- [ ] POST /api/listas con nombre e icono
- [ ] Espera confirmación del servidor
- [ ] Si éxito: modal se cierra
- [ ] Si error: muestra alert con mensaje
- [ ] Nueva lista aparece en drawer automáticamente

### FASE 5: RESPONSIVIDAD

#### 5.1 Mobile (< 768px)
- [ ] Drawer ocupa 100% del ancho
- [ ] Items tienen 44px mínimo de altura
- [ ] Padding y gap responsivos
- [ ] Texto legible sin zoom
- [ ] Botones clickeables fácilmente

#### 5.2 Mobile Landscape
- [ ] Drawer se adapta a altura reducida
- [ ] Items scrolleables
- [ ] No hay overflow horizontal
- [ ] Teclado se detecta automáticamente

#### 5.3 Tablet (768px - 1024px)
- [ ] Drawer tiene 280px de ancho
- [ ] Items bien espaciados
- [ ] Fuentes escaladas apropiadamente
- [ ] Grid responsivo

#### 5.4 Desktop (>= 1024px)
- [ ] Drawer tiene 300px de ancho
- [ ] Mejor espaciado
- [ ] Hover effects en items
- [ ] Consistencia visual perfecta

### FASE 6: ACCESIBILIDAD

#### 6.1 Navegación de Teclado
- [ ] Tab navega entre elementos
- [ ] Enter activa botones
- [ ] ESC cierra drawer
- [ ] Focus visible en todos los elementos

#### 6.2 Screen Reader
- [ ] Drawer tiene aria-label "Mis listas"
- [ ] Items tienen role="button"
- [ ] Fondo tiene aria-hidden="true"
- [ ] Contenido es navegable

#### 6.3 Contraste
- [ ] Texto tiene suficiente contraste (WCAG 2.1)
- [ ] Colores accesibles
- [ ] Modo oscuro y claro soportados

### FASE 7: GESTOS Y INTERACCIÓN

#### 7.1 Swipe (Móvil)
- [ ] Swipe derecha en drawer no hace nada (o solo cierra si > 50px)
- [ ] Swipe izquierda (desde drawer) cierra drawer
- [ ] Sensible al gesto pero no demasiado

#### 7.2 Touch
- [ ] Touch targets mínimo 44x44px
- [ ] Sin tap-highlight-color oscuro
- [ ] Feedback visual en active state

#### 7.3 Mouse
- [ ] Hover effects en desktop
- [ ] Click funciona en todos lados
- [ ] Cursor cambia a pointer en botones

### FASE 8: INTEGRACIÓN CON APP

#### 8.1 Selector Actual
- [ ] Header muestra lista actual
- [ ] Icono de lista actual
- [ ] Nombre de lista actual
- [ ] Rol actual (PROPIETARIO/COMPARTIDA)

#### 8.2 Cambio de Lista
- [ ] Vista Stock se actualiza con productos de nueva lista
- [ ] Vista Compra se actualiza
- [ ] Categorías se actualizan
- [ ] FAB sigue funcionando

#### 8.3 Sin Regresiones
- [ ] Modal de crear producto sigue funcionando
- [ ] Modal de ticket/OCR sigue funcionando
- [ ] Filtros siguen funcionando
- [ ] Búsqueda sigue funcionando
- [ ] Temas (claro/oscuro) siguen funcionando

### FASE 9: RENDIMIENTO

#### 9.1 Carga Inicial
- [ ] Listas se cargan rápido (< 1s)
- [ ] Drawer se abre sin delays
- [ ] Animaciones fluidas (60fps)

#### 9.2 Cambio de Lista
- [ ] Transición suave
- [ ] Sin memory leaks
- [ ] API responde rápido

### FASE 10: CASOS EDGE

#### 10.1 Sin Listas
- [ ] Si no hay listas: muestra "Sin listas aún"
- [ ] Botón "+ Nueva lista" sigue visible
- [ ] Permite crear primera lista

#### 10.2 Muchas Listas
- [ ] 10+ listas scrollean correctamente
- [ ] Performance no se degrada
- [ ] Items de lista son pequeños pero clickeables

#### 10.3 Nombres Largos
- [ ] Nombres con 50 caracteres se truncan
- [ ] No rompen el layout
- [ ] Son legibles (ellipsis si necesario)

#### 10.4 Caracteres Especiales
- [ ] Emojis en nombres funcionan
- [ ] Caracteres Unicode funcionan
- [ ] HTML está escapado (sin XSS)
- [ ] Tildes y acentos funcionan

### FASE 11: CONSISTENCIA VISUAL

#### 11.1 Colores
- [ ] Usa variables CSS correctas
- [ ] Tema claro y oscuro consistentes
- [ ] Contraste suficiente en ambos temas

#### 11.2 Tipografía
- [ ] Fuentes responsivas con clamp()
- [ ] Tamaños consistentes
- [ ] Pesos correctos (normal, 500, 600)

#### 11.3 Espaciado
- [ ] Padding consistente
- [ ] Gap entre elementos consistente
- [ ] Alineación perfecta

#### 11.4 Animaciones
- [ ] Duraciones: 300ms para drawers
- [ ] Easing: ease-out para entrada, ease para salida
- [ ] Sin animaciones abruptas

---

## 🧪 PROCEDIMIENTO DE PRUEBA

### Paso 1: Preparar Ambiente
```bash
# 1. Asegurar servidor corriendo en http://localhost:5000
# 2. Abrir DevTools en Chrome/Firefox
# 3. Habilitar device emulation para probar diferentes tamaños
```

### Paso 2: Probar Cada Fase
Para cada fase:
1. Leer descripción de pruebas
2. Ejecutar cada test
3. Marcar ✓ o ✗
4. Si ✗: documentar el bug
5. Tomar screenshot si es necesario

### Paso 3: Registro de Bugs
Si encuentra un bug:
- Descripción clara del problema
- Pasos para reproducir
- Dispositivo/navegador
- Screenshot si aplicable
- Severidad (crítica, alta, media, baja)

---

## 📱 DISPOSITIVOS A PROBAR

### Mobile
- [ ] iPhone 12 Pro (390x844)
- [ ] iPhone 13 Pro Max (430x932)
- [ ] iPhone SE (375x667)
- [ ] Pixel 6 (412x915)
- [ ] Samsung A10 (360x800)

### Tablet
- [ ] iPad (768x1024)
- [ ] iPad Pro (1024x1366)
- [ ] Samsung Tab (800x1280)

### Desktop
- [ ] 1920x1080
- [ ] 1366x768
- [ ] 1280x720

### Orientaciones
- [ ] Portrait (todos los dispositivos)
- [ ] Landscape (móvil y tablet)

---

## 🌐 NAVEGADORES

- [ ] Chrome (desktop y mobile)
- [ ] Firefox
- [ ] Safari (iOS)
- [ ] Edge

---

## ✅ RESULTADO FINAL

Si TODOS los tests pasan ✓:

**DRAWER LATERAL IMPLEMENTATION: COMPLETADO Y VERIFICADO**

Calidad: ⭐⭐⭐⭐⭐ PROFESIONAL
Fecha completada: ___________
Aprobado por: ___________

---

## 📝 NOTAS

- Documentar cualquier comportamiento inesperado
- Si encuentra mejora UX, anotar para versión siguiente
- Performance debe ser suave en todos los dispositivos
- Accesibilidad es no-negociable
- Sin regresiones en funcionalidad existente

---

## 🚀 SIGUIENTES PASOS (DESPUÉS DE APROBAR)

1. ✓ Drawer implementado
2. ✓ Pruebas exhaustivas completadas
3. ☐ Optimización de performance (si necesario)
4. ☐ Documentación final
5. ☐ Deployment a producción

