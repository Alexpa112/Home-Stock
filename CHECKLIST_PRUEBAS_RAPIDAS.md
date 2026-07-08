# ✅ CHECKLIST - PRUEBAS RÁPIDAS DEL DRAWER

**Fecha de inicio:** ___________  
**Probador:** ___________  
**Dispositivo/Navegador:** ___________

---

## 🚀 TEST 1: FUNCIONAMIENTO BÁSICO (5 min)

### Preparación
- [ ] Servidor iniciado: `python run.py`
- [ ] Navegador abierto: http://localhost:5000
- [ ] DevTools abierto (F12)
- [ ] Consola visible

### Tests Automatizados
```javascript
// Ejecutar en consola:
window.drawerTests.runAll()
```
- [ ] Tests ejecutados sin errores
- [ ] Resultado: "✅ TODOS LOS TESTS PASARON"
- [ ] Éxito: 100%
- [ ] Tiempo: < 5 segundos

**Notas:** ___________________________________________________________________

---

## 🎮 TEST 2: ABRIR DRAWER (2 min)

- [ ] Haz clic en header "📋 Mi inventario ▾"
- [ ] Drawer se desliza desde izquierda
- [ ] Fondo oscuro aparece
- [ ] Listas se cargan desde API
- [ ] Items son clickeables

**Observaciones:** __________________________________________________________

---

## ✕ TEST 3: CERRAR DRAWER (2 min)

### Opción 1: Botón X
- [ ] Haz clic en botón ✕
- [ ] Drawer se desliza hacia izquierda
- [ ] Fondo oscuro desaparece

### Opción 2: Click fondo
- [ ] Abre drawer
- [ ] Haz clic en fondo oscuro
- [ ] Drawer se cierra

### Opción 3: Tecla ESC
- [ ] Abre drawer
- [ ] Presiona ESC
- [ ] Drawer se cierra

**Observaciones:** __________________________________________________________

---

## 🔄 TEST 4: CAMBIAR LISTA (3 min)

- [ ] Abre drawer
- [ ] Si hay múltiples listas:
  - [ ] Haz clic en lista diferente
  - [ ] Drawer se cierra automáticamente
  - [ ] Item anterior está sin highlight
  - [ ] Nuevo item está en highlight
  - [ ] Página se recarga con nueva lista
- [ ] Si hay solo una lista:
  - [ ] Documento esto como "N/A - solo 1 lista"

**Observaciones:** __________________________________________________________

---

## ➕ TEST 5: CREAR NUEVA LISTA (5 min)

- [ ] Abre drawer
- [ ] Haz clic en "+ Nueva lista"
- [ ] Modal aparece con animación
- [ ] Formulario está vacío
- [ ] Campo "Nombre" tiene focus (cursor visible)

### Validación Nombre
- [ ] Intenta crear sin nombre → Error
- [ ] Intenta crear nombre 1 char → Error
- [ ] Crea con nombre válido (>= 2 chars) → OK

### Crear Lista
- [ ] Completa: Nombre = "Mi prueba"
- [ ] Deja icono default (📋)
- [ ] Haz clic en "Crear lista"
- [ ] Modal se cierra
- [ ] Lista aparece en drawer automáticamente
- [ ] Nueva lista está en highlight

**Observaciones:** __________________________________________________________

---

## 📱 TEST 6: RESPONSIVIDAD (5 min)

### Setup
- [ ] Abre DevTools (F12)
- [ ] Haz clic en device emulation (📱)

### iPhone 12 Pro (390x844)
- [ ] Drawer ocupa 100% ancho
- [ ] Items tienen altura >= 44px
- [ ] Texto legible sin zoom
- [ ] Botones clickeables
- [ ] Sin scroll horizontal

**Estado:** ✅ / ❌

### iPad (768x1024)
- [ ] Drawer tiene ancho fijo (280px)
- [ ] Items bien espaciados
- [ ] Fuentes legibles
- [ ] Layout se adapta

**Estado:** ✅ / ❌

### Desktop (1920x1080)
- [ ] Drawer tiene ancho fijo (300px)
- [ ] Perfectamente centrado
- [ ] Hover effects en items
- [ ] Mejor espaciado

**Estado:** ✅ / ❌

### Landscape (Móvil girado)
- [ ] Drawer se adapta
- [ ] Items scrolleables
- [ ] Sin overflow horizontal
- [ ] Teclado se detecta (si está visible)

**Estado:** ✅ / ❌

**Observaciones:** __________________________________________________________

---

## ⌨️ TEST 7: ACCESIBILIDAD (3 min)

### Navegación Keyboard
- [ ] Tab navega entre items
- [ ] Enter activa item seleccionado
- [ ] ESC cierra drawer
- [ ] Focus visible en todos elementos

### Screen Reader
Si tienes screen reader habilitado:
- [ ] Drawer se anuncia como "navegación"
- [ ] Items se leen correctamente
- [ ] Roles se anuncia (button)

**Observaciones:** __________________________________________________________

---

## 📊 TEST 8: PERFORMANCE (2 min)

### Animaciones
- [ ] Drawer entra suavemente (sin saltos)
- [ ] Drawer sale suavemente
- [ ] Fondo oscuro aparece sin lag
- [ ] Items se renderizan sin demora
- [ ] 60fps en animaciones

### Carga
- [ ] Listas cargan en < 1s
- [ ] Sin lag visible
- [ ] Sin memory leaks (inspeccionar Memory en DevTools si necesario)

**Observaciones:** __________________________________________________________

---

## 🎨 TEST 9: VISUAL (3 min)

### Tema Claro
- [ ] Colores se ven correctamente
- [ ] Contraste es suficiente
- [ ] Texto legible
- [ ] No hay typos visibles

### Tema Oscuro
- [ ] Colores se ven correctamente
- [ ] Contraste es suficiente
- [ ] Texto legible
- [ ] Transición smooth

### Botones
- [ ] Items tienen feedback visual (color/background)
- [ ] Botón "+ Nueva lista" se destaca
- [ ] Hover effects en desktop

**Observaciones:** __________________________________________________________

---

## 🔒 TEST 10: SEGURIDAD (2 min)

### XSS Protection
- [ ] Crea lista con nombre: `<script>alert('xss')</script>`
- [ ] Lista se crea normalmente (no ejecuta script)
- [ ] Nombre se muestra literal (con < >)

### Validación
- [ ] Intenta crear lista vacía → No permite
- [ ] Intenta crear nombre muy largo (>50) → Se trunca/rechaza
- [ ] Caracteres especiales funcionan (é, ñ, emoji)

**Observaciones:** __________________________________________________________

---

## 🐛 BUGS ENCONTRADOS

Si encontraste algún problema, documenta aquí:

### Bug 1
**Descripción:** _____________________________________________________________
**Pasos para reproducir:** __________________________________________________
**Severidad:** ⭐ / ⭐⭐ / ⭐⭐⭐ / ⭐⭐⭐⭐ / ⭐⭐⭐⭐⭐
**Screenshot:** (adjunta si posible)

### Bug 2
**Descripción:** _____________________________________________________________
**Pasos para reproducir:** __________________________________________________
**Severidad:** ⭐ / ⭐⭐ / ⭐⭐⭐ / ⭐⭐⭐⭐ / ⭐⭐⭐⭐⭐
**Screenshot:** (adjunta si posible)

---

## 📝 FEEDBACK GENERAL

¿Qué funcionó bien?  
___________________________________________________________________

¿Qué podría mejorar?  
___________________________________________________________________

¿Usabilidad es intuitiva?  
___________________________________________________________________

¿Rendimiento es aceptable?  
___________________________________________________________________

---

## ✅ RESULTADO FINAL

Total de tests realizados: ___ / 10

Tests pasados: ___ / 10

Bugs encontrados: ___

**ESTATUS FINAL:**
- [ ] ✅ TODO FUNCIONA PERFECTO (0 bugs críticos)
- [ ] ⚠️ FUNCIONA CON BUGS MENORES (bugs bajos/medios)
- [ ] ❌ NECESITA FIXES (bugs altos/críticos)

**Aprobado por:** _______________ **Fecha:** _______________

---

## 📋 CHECKLIST DE APROBACIÓN FINAL

- [ ] Todos los tests automatizados pasaron (100%)
- [ ] Pruebas manuales completadas (10 tests)
- [ ] Sin bugs críticos encontrados
- [ ] Responsividad verificada en 3+ tamaños
- [ ] Accesibilidad verificada
- [ ] Performance es aceptable
- [ ] No hay regressions en funcionalidad existente
- [ ] Documentación está completa
- [ ] Tests están documentados

**SI TODO ESTÁ ✓: LISTO PARA DEPLOYMENT**

---

**Fecha completada:** _______________  
**Revisado por:** _______________  
**Estado:** ✅ / ❌

