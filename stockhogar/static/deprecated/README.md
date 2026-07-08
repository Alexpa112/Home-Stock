# 📦 Código Legacy - DEPRECATED

Estos archivos han sido **reemplazados** por la nueva arquitectura OOP de Fase 3.

## Por qué fueron deprecados

### ❌ `drawer-listas.js` (616 líneas)
**Reemplazado por**: `window.listsManager` (futuro) en `modules/`

- La funcionalidad de gestión de listas ahora está integrada en managers OOP
- Los métodos están centralizados en managers con render automático
- Remover este archivo redujo el acoplamiento y facilitó testing

### ❌ `ui-components.js` (445 líneas)
**Reemplazado por**: UIManager + métodos en managers

- Las clases base (`ModalBase`, `FormModal`) ya no son necesarias
- Los managers manejan modales directamente con `abrirModal()`, `cerrarModal()`
- Cada manager es responsable de su propio UI (encapsulación)

### ❌ `test-drawer.js` (416 líneas)
**Propósito**: Era un archivo de prueba para drawer

- No se usaba en producción
- Removido para limpiar el codebase

## Migración a nueva arquitectura

**Antes (legacy)**:
```javascript
// ui-components.js
class FormModal extends ModalBase { ... }

// drawer-listas.js
class DrawerListasManager { ... }

// app.js - múltiples frameworks
// ...
```

**Ahora (OOP + managers)**:
```javascript
// modules/productos-manager.js
class ProductosManager {
  abrirModalCrear() { ... }
  guardarProducto(e) { ... }
  cerrarModal() { ... }
}

// modules/espacios-manager.js
class EspaciosManager {
  abrirModalCrear() { ... }
  guardarEspacio(e) { ... }
}

// app.js - limpio y orquestado
managers.productos.abrirModalCrear();
```

## Beneficios de la migración

✅ **Menos código**: 1,477 líneas → 0 (migrado a managers)  
✅ **Más cohesión**: UI está junto a la lógica de datos  
✅ **Mejor testing**: Cada manager testeable independientemente  
✅ **Más mantenible**: Regla de responsabilidad única (SRP)  
✅ **Menos acoplamiento**: Managers no dependen de componentes UI base  

## Si necesitas recuperarlos

Los archivos están en `deprecated/` para referencia histórica. Pero **no recomendamos usarlos** - la nueva arquitectura es superior.

Para ver cómo migramos la funcionalidad:
- Listas → `modules/listas-manager.js` (futuro)
- Modales → `modules/productos-manager.js`, `espacios-manager.js`, etc.
- UI Base → `modules/ui-manager.js`

---

**Referencia**: Ver `FASE_3_FRONTEND.md` para detalles de la refactorización.
