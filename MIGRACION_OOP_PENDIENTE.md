# 📋 Migración OOP - Funcionalidades Pendientes

**Estado**: Restauración de código legacy completada  
**Objetivo**: Migrar TODAS las funcionalidades al patrón OOP sin perder nada  
**Prioridad**: CRÍTICA (debe hacerse correctamente)

---

## ⚠️ Contexto del Problema

La refactorización anterior fue demasiado agresiva:
- ❌ Se eliminaron archivos legacy (listas-manager, ui-components) sin migrar su funcionalidad
- ❌ Se perdieron características críticas: gestión de listas, usuarios, historial
- ❌ La aplicación quedó funcional pero incompleta

**Solución**: Los archivos legacy se restauraron como fallback. Ahora se migrará correctamente.

---

## 🔄 Funcionalidades a Migrar

### 1. **ListasManager** ❌ CRÍTICA (1,500+ líneas)

**Estado actual**: DrawerListasManager en modules/listas-manager.js (legacy)

**Funcionalidades**:
```javascript
// Gestión de listas
cargarMisListas()              // ← FALTA
crearLista(datos)              // ← FALTA
actualizarLista(id, datos)     // ← FALTA
borrarLista(id)                // ← FALTA
cambiarLista(listaId)          // ← FALTA
seleccionarLista(id)           // ← FALTA

// Renderizado
renderizarSelectorListas()     // ← FALTA
render()                       // ← FALTA
abrirModal()                   // ← FALTA
cerrarModal()                  // ← FALTA
```

**Métodos legacy a migrar desde drawer-listas.js**:
- `init()` - Inicialización
- `setupEventListeners()` - Wireado de eventos
- `cargarListas()` - GET /api/listas
- `renderLista()` - HTML para cada lista
- `renderizarSelectorListas()` - Modal de selección
- `actualizarListaActual()` - Cambiar lista activa
- `toggleModoEdicion()` - Modo edición/visualización
- `abrirModalEditar(lista)` - Abrir formulario
- `guardarCambiosLista(e)` - Guardar cambios
- `marcarListaActual(id)` - Marcar como activa

**Dónde integrar**: `stockhogar/static/modules/listas-manager.js` (refactorizar OOP)

---

### 2. **UsuariosManager** ❌ CRÍTICA (400+ líneas)

**Estado actual**: Funciones sueltas en app-legacy.js

**Funcionalidades faltantes**:
```javascript
// Gestión de usuarios
cargarUsuarios()               // ← FALTA
crearUsuario(datos)            // ← FALTA
actualizarUsuario(id, datos)   // ← FALTA
borrarUsuario(id)              // ← FALTA
obtenerUsuarioActual()         // ← FALTA

// Renderizado
renderListaUsuarios()          // ← FALTA
render()                       // ← FALTA
```

**Métodos legacy a migrar desde app-legacy.js**:
- `cargarEstadoAuth()` - GET /auth/me
- `cargarUsuarios()` - GET /api/usuarios
- `renderListaUsuarios()` - Renderizar lista
- `crearUsuario()` - POST usuario
- `borrarUsuario(u)` - DELETE usuario
- `abrirFormularioUsuario()` - Modal crear
- `cerrarFormularioUsuario()` - Cerrar modal

**Dónde integrar**: `stockhogar/static/modules/usuarios-manager.js` (NUEVO)

---

### 3. **HistorialManager** ⚠️ IMPORTANTE (200+ líneas)

**Estado actual**: Funciones sueltas en app-legacy.js

**Funcionalidades faltantes**:
```javascript
// Historial de productos
cargarHistorial()              // ← FALTA
obtenerHistorial(filtro)       // ← FALTA
render()                       // ← FALTA
```

**Métodos legacy a migrar**:
- `cargarHistorial()` - GET /api/historial
- `renderHistorial()` - Renderizar tabla
- Filtrado por producto/fecha
- Paginación (si existe)

**Dónde integrar**: `stockhogar/static/modules/historial-manager.js` (NUEVO)

---

### 4. **UIManager** ⚠️ INCOMPLETO (necesita expansión)

**Estado actual**: Parcialmente implementado en modules/ui-manager.js

**Funcionalidades que necesita agregar**:
```javascript
// Selector de iconos
abrirSelectorIconos(seleccionado, callback)  // ← FALTA
cerrarSelectorIconos()                       // ← FALTA
renderizarIconosGrid(filtro)                 // ← FALTA
crearSelectorIconos(contenedor, selected)    // ← FALTA

// Modales genéricos (usar ui-components.js)
abrirModalGenerico(config)     // ← FALTA
cerrarModalGenerico()          // ← FALTA
```

**Métodos legacy a migrar desde app-legacy.js**:
- `crearSelectorIconos()` - Buscador + grid de iconos
- `abrirModalSelectorIconos()` - Modal de selección
- `cerrarModalSelectorIconos()` - Cerrar modal
- `renderizarIconosGrid(filtro)` - Renderizar grid

---

### 5. **Funciones Auxiliares** ⚠️ DISPERSAS

**Estado actual**: Funciones sueltas en app-legacy.js (utils)

**Funcionalidades dispersas**:
```javascript
// Utilidades globales
escapeHtml(texto)              // ← Movida a app.js ✅
normalizarTexto(texto)         // ← Movida a app.js ✅
ajustarColor(hex, delta)       // ← FALTA
iconoDeCategoria(nombre)       // ← FALTA
iconoEfectivo(item)            // ← FALTA
agregarPulsacion(el, corta, larga) // ← FALTA
sincronizarEstadoModal()       // ← FALTA
habilitarCierreSeguro()        // ← FALTA
habilitarDragDown()            // ← FALTA
```

**Dónde integrar**: `stockhogar/static/utils/helpers.js` (NUEVO archivo)

---

## 📊 Plan de Migración por Fases

### Fase A: ListasManager (Prioridad 1 - CRÍTICA)
1. Refactorizar DrawerListasManager → ListasManager OOP
2. Implementar todos los métodos CRUD
3. Integrar con ProductosManager y CompraManager
4. Tests: >80% coverage
5. **Duración estimada**: 3-4 horas

### Fase B: UsuariosManager (Prioridad 2 - CRÍTICA)
1. Crear UsuariosManager desde cero (migrate from app-legacy.js)
2. Implementar cargarUsuarios(), borrarUsuario(), etc.
3. Integrar modal de gestión de usuarios
4. Tests: >80% coverage
5. **Duración estimada**: 2-3 horas

### Fase C: HistorialManager (Prioridad 3 - IMPORTANTE)
1. Crear HistorialManager desde cero
2. Implementar cargarHistorial(), render()
3. Integrar filtrado y búsqueda
4. Tests: >80% coverage
5. **Duración estimada**: 2 horas

### Fase D: Funciones Auxiliares (Prioridad 4 - NORMAL)
1. Crear `utils/helpers.js` con funciones dispersas
2. Refactorizar UIManager para usar estos helpers
3. Limpiar código duplicado
4. **Duración estimada**: 1-2 horas

### Fase E: Limpieza Final (Prioridad 5 - FINAL)
1. Eliminar app-legacy.js (cuando todo esté migrado)
2. Eliminar ui-components.js (cuando UIManager cubra todo)
3. Eliminar listas-manager.js legacy (cuando ListasManager esté OOP)
4. Actualizar index.html
5. Tests e2e finales
6. **Duración estimada**: 1 hora

---

## 🔗 Dependencias Entre Managers

```
ListasManager
  ├→ ProductosManager (sincronizar lista)
  └→ CompraManager (artículos de la lista)

UsuariosManager
  ├→ UIManager (mostrar modal)
  └→ APIClient (autenticación)

HistorialManager
  └→ UIManager (mostrar modal/tabla)

UIManager (dependencia global)
  ├→ DOMManager
  ├→ ListasManager
  ├→ UsuariosManager
  └→ HistorialManager
```

---

## ✅ Checklist de Validación

Por cada manager nuevo, verificar:

- [ ] Todos los métodos CRUD implementados
- [ ] Event emitter funcionando (suscribir/notificar)
- [ ] Render method actualiza DOM correctamente
- [ ] Formularios modales funcionan (create/edit/delete)
- [ ] Validación de datos en cliente
- [ ] Manejo de errores (try/catch, APIError)
- [ ] Tests unitarios >80% coverage
- [ ] Integración con otros managers
- [ ] Sin funcionalidades perdidas del legacy
- [ ] Documentación actualizada

---

## 📝 Notas Importantes

1. **NO eliminar app-legacy.js hasta que TODO esté migrado**
2. **NO eliminar ui-components.js** (muchos managers la usan)
3. **Preservar TODAS las funcionalidades** - el legacy es la verdad
4. **Hacer commits pequeños** por cada manager
5. **Tests primero** - escribir tests antes de migrar
6. **Revisar index.html** - asegurar que se cargan todos los scripts

---

## 🎯 Objetivo Final

**100% funcionalidad OOP + 0% código legacy duplicado**

- ✅ 6 managers originales (productos, compra, categorías, espacios, tickets, ui)
- ✅ 3 managers nuevos (listas, usuarios, historial)
- ❌ 0 líneas de app-legacy.js
- ❌ 0 líneas de ui-components.js legacy
- ✅ 100% tests coverage >80%
- ✅ Documentación completa

---

**Última actualización**: 2026-07-08  
**Estado**: Planificación completada  
**Siguiente paso**: Iniciar Fase A (ListasManager)
