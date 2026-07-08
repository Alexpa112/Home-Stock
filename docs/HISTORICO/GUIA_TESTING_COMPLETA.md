# Guía Completa de Testing - StockHogar Mobile-First

**Fecha:** 2026-07-08  
**Estado:** Listo para testing manual  
**Servidor:** http://localhost:5000  

---

## 🔐 Credenciales de acceso

```
Usuario: alejandro
Contraseña: 123456
```

---

## 🚀 Cómo empezar

1. **Abrir navegador:** http://localhost:5000
2. **Login:** Usar las credenciales arriba
3. **DevTools mobile:** Ctrl+Shift+M (Windows/Linux) o Cmd+Shift+M (Mac)
4. **Seleccionar dispositivo:** iPhone 15 (390x844)

---

## ✅ Checklist de Testing

### **Fase 1: Carga y Selector de Listas (CRÍTICO)**

- [ ] La app carga correctamente
- [ ] Se muestra la barra "Mis listas" bajo la cabecera
- [ ] El selector muestra: icono + nombre + rol (PROPIETARIO)
- [ ] Tap en selector abre modal de listas
- [ ] Modal muestra sección "Propias" con al menos 1 lista
- [ ] Modal cierra al tap en una lista
- [ ] Los tabs (Stock | Compra) aparecen bajo el selector
- [ ] Consola SIN errores rojos

### **Fase 2: Lista de Compra - Botones Funcionales**

Pestaña: **Compra** 🛒

#### A) Botón FAB (+)
- [ ] Tap en botón + abre modal "Añadir a la lista de la compra"
- [ ] Modal tiene campos: Nombre, Cantidad, Unidad, Categoría, Icono
- [ ] Hay 2 botones: "Cancelar" y "Añadir"
- [ ] Campo Nombre está enfocado automáticamente
- [ ] Font-size del input ≥ 16px (verificar en DevTools Inspect)
- [ ] Input min-height ≥ 44px (verificar en DevTools Inspect)

#### B) Añadir artículo
- [ ] Rellenar nombre: "Leche"
- [ ] Cantidad: 2
- [ ] Unidad: l
- [ ] Categoría: Lácteos y Huevos
- [ ] Icono: 🥛 (opcional)
- [ ] Tap "Añadir"
- [ ] Modal cierra
- [ ] Artículo aparece en la lista
- [ ] Se agrupa bajo "Lácteos y Huevos"

#### C) Long-press en artículo para editar
- [ ] Long-press (mantener > 500ms) en artículo "Leche"
- [ ] Se abre modal "Editar artículo"
- [ ] Los campos están prellenados con los datos actuales
- [ ] Hay botones: "Cancelar", "Borrar" (en rojo), "Guardar"
- [ ] Botón "Borrar" SÍ está visible (porque estamos editando)

#### D) Editar artículo
- [ ] Cambiar cantidad a 3
- [ ] Tap "Guardar"
- [ ] Modal cierra
- [ ] Artículo actualizado muestra 3 unidades
- [ ] (En DevTools, el JSON debe mostrar cantidad: 3)

#### E) Borrar artículo
- [ ] Long-press en artículo de nuevo
- [ ] Modal abre
- [ ] Tap "Borrar" (botón rojo)
- [ ] Confirmación: "¿Borrar este artículo de la lista?"
- [ ] Tap "OK" (o "Yes")
- [ ] Modal cierra
- [ ] Artículo desaparece de la lista

#### F) Completar artículo
- [ ] Añadir nuevo artículo: "Pan"
- [ ] Tap simple (no long-press) → artículo se marca como completado
- [ ] Se mueve a sección "Comprados recientemente" (abajo)
- [ ] El tile tiene estilo diferente (por ejemplo, opacidad)
- [ ] Tap en artículo completado → vuelve a la lista principal

#### G) Buscar en catálogo
- [ ] Tap en + nuevamente
- [ ] En modalCatalogo: buscar "Leche"
- [ ] Aparecen sugerencias del catálogo
- [ ] Tap en "Leche entera"
- [ ] Modal se cierra, artículo se añade

### **Fase 3: Stock - Botones Funcionales**

Pestaña: **Stock** 📦

#### H) Lista de productos
- [ ] Tab "Stock" está visible y es clickeable
- [ ] Tap en "Stock" → muestra vista de productos
- [ ] Hay un buscador "Buscar producto..."
- [ ] Hay filtros por categoría (chips)
- [ ] Botón + funciona para añadir nuevo producto

#### I) Añadir producto
- [ ] Tap +
- [ ] Modal: "Nuevo producto"
- [ ] Rellenar: Nombre "Leche entera", Cantidad 5, Stock mínimo 1
- [ ] Tap "Guardar"
- [ ] Producto aparece en lista
- [ ] Muestra cantidad y botones +/−

#### J) Ajustar cantidad
- [ ] Tap − (restar) → cantidad baja a 4
- [ ] Tap + (sumar) → cantidad sube a 5
- [ ] Los cambios se guardan automáticamente

#### K) Editar producto
- [ ] Tap icono ✏️ en un producto
- [ ] Modal "Editar producto" con datos prellenados
- [ ] Cambiar algo (ej. cantidad a 10)
- [ ] Tap "Guardar"
- [ ] Cambio reflejado en la lista

#### L) Borrar producto
- [ ] Tap 🗑️ en un producto
- [ ] Confirmación: "¿Eliminar este producto del stock?"
- [ ] Tap "OK"
- [ ] Producto desaparece

### **Fase 4: iOS 18 Safari Fixes**

#### M) Modal + Teclado
- [ ] En modal (producto o artículo), tap en Nombre
- [ ] Teclado virtual se abre (en DevTools, simula con overlay)
- [ ] **CRÍTICO:** Botones "Cancelar" y "Guardar" SIGUEN VISIBLES
- [ ] Modal NO desaparece bajo el teclado
- [ ] **NO hay scroll sin contenido** (modal no es scrolleable si cabe)

#### N) Scroll Lateral
- [ ] En cualquier vista, intenta deslizar horizontalmente
- [ ] **NO hay overflow horizontal**
- [ ] **SÍ hay scroll vertical si el contenido es largo**

#### O) Zoom
- [ ] Double-tap en la página (NO en inputs)
- [ ] **NO hace zoom**
- [ ] Double-tap en inputs → DEBERÍA hacer zoom (normal)

#### P) FAB con Teclado
- [ ] Abre modal
- [ ] Tap en Nombre (teclado se abre)
- [ ] Botón FAB (+) sube automáticamente
- [ ] FAB NO queda bajo el teclado
- [ ] Cierra modal → FAB vuelve a la posición original

#### Q) Tabs Sticky
- [ ] En Stock, scroll hacia abajo
- [ ] Tabs (Stock | Compra) se quedan visibles en top
- [ ] Scroll hacia arriba → cabecera se queda pegada

### **Fase 5: Animaciones (150ms)**

#### R) Transiciones suaves
- [ ] Abrir/cerrar modal: transición suave (no instant)
- [ ] Cambiar de tema (🌙): cambio instantáneo OK
- [ ] Completar artículo: animación de ~280ms antes de actualizar

### **Fase 6: Dark Mode**

#### S) Cambiar tema
- [ ] Tap 🌙 en cabecera
- [ ] App cambia a dark mode
- [ ] Modales se adaptan correctamente
- [ ] Todos los colores son legibles
- [ ] Tap 🌙 nuevamente → light mode

### **Fase 7: Consola (FINAL CHECK)**

#### T) Errores en consola
- [ ] F12 → Console
- [ ] **NO hay errores rojos** (Errors)
- [ ] Warnings OK (amarillas)
- [ ] Si hay error: reportar exactamente qué dice

---

## 📊 Resultado Final

### Bugs encontrados
```
[] Aquí va: Descripción breve
[] El botón X no responde cuando...
[] El modal Y no abre porque...
```

### Problemas conocidos (si aplica)
- (Ninguno reportado aún)

### Funciones que funcionan bien ✓
- Selector de listas
- FAB abre modal
- Botones de guardar
- Búsqueda en catálogo
- Dark mode
- Animaciones suaves
- Responsive design

---

## 💡 Tips para Testing

1. **DevTools** → Network tab: puedes ver cada API call
2. **DevTools** → Console: errores JavaScript aparecen aquí
3. **Simular teclado:** Inspecciona un input en DevTools, y verás cómo se comporta
4. **Storage:** DevTools → Application → localStorage → verifica `lista-actual`
5. **Simular diferentes dispositivos:** iPhone 12, Pixel 5, iPad, etc.

---

## 🎯 Próximos pasos después de testing

1. Si todo funciona: ✅ LISTO PARA PRODUCCIÓN
2. Si hay bugs: reportar en sección "Bugs encontrados"
3. Pruebas en iOS real (si tienes dispositivo)
4. Pruebas en Android Chrome/Firefox

---

**Duración estimada de testing:** 15-20 minutos  
**Dificultad:** Fácil (solo clicks y verificación visual)

¡Buen testing! 🚀
