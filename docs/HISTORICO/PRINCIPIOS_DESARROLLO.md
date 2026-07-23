# 🔴 PRINCIPIOS CRÍTICOS DE DESARROLLO - LEER ANTES DE CADA CAMBIO

## 1. PUNTO POR PUNTO CON TESTS FUNCIONALES

**REGLA**: Cada cambio = 1 test funcional ANTES de pasar al siguiente

```
Patrón obligatorio:
1. Identificar qué se va a cambiar
2. Hacer cambio MÍNIMO
3. TEST INMEDIATO en navegador
4. Verificar que NO rompe nada
5. Commit con hash
6. Pasar al siguiente SOLO si anterior OK
```

**Cambios recientes**:
- ✅ Commit 7039616: Modal caching → PROBADO ✓
- ✅ Commit 3093402: Botón duplicado → PROBADO ✓
- ⏳ App.js cargarMisListas() → PENDIENTE TEST

---

## 2. RAZONAMIENTO GLOBAL DE LA APP

**Estructura de flujo**:
```
Usuario login → cargarMisListas() → 
  ├─ SI tiene listas → renderizarSelectorListas() → selecciona lista
  └─ NO tiene listas → ??? (NUEVA LÓGICA)

Cuando usuario en Stock:
- Puede ver productos
- Puede agregar artículos a lista
- Puede filtrar por categoría
- Puede buscar productos

Cuando usuario abre Mis Listas:
- Ve modal selector
- Puede crear/eliminar listas
- Puede compartir listas
```

**Puntos CRÍTICOS que NO se pueden romper**:
1. ✅ Usuario puede ver stock aunque no tenga listas (ACTUAL)
2. ✅ Productos globales están disponibles siempre
3. ✅ Filtros por categoría funcionan
4. ✅ Búsqueda funciona
5. ✅ Login/registro funcionan
6. ✅ Traducción i18n funciona
7. ❌ CAMBIO: Agregar artículos REQUIERE lista (NUEVA VALIDACIÓN)

---

## 3. REUTILIZACIÓN DE CÓDIGO

**Funciones existentes que usar (NO crear nuevas)**:
```javascript
// En app.js:
- cargarMisListas() → Cargar listas del API
- renderizarSelectorListas() → Renderizar listas
- actualizarListaActual() → Actualizar lista seleccionada

// En drawer-listas.js:
- window.crearListaModal → Instancia del modal de crear lista
- window.crearListaModal.open() → Abrir modal
- window.crearListaModal.close() → Cerrar modal
- window.crearListaModal.onSubmit() → Enviar formulario

// En ui-components.js:
- ModalBase.open()
- ModalBase.close()
- FormModal.setupFormListeners()
```

**NO crear nuevas funciones si existen equivalentes**

---

## 4. MAPA DE DEPENDENCIAS

```
index.html
├── app.js (inicializa todo)
│   ├── cargarMisListas() [CRÍTICA]
│   ├── renderizarSelectorListas() [CRÍTICA]
│   └── actualizarListaActual() [CRÍTICA]
├── drawer-listas.js
│   ├── window.crearListaModal [GLOBAL]
│   └── window.drawerListasManager [GLOBAL]
├── form-builder.js
│   ├── FormBuilder.crearFormularioLista()
│   └── FormBuilder.inyectarFormularioEnModal()
└── ui-components.js
    ├── ModalBase
    └── FormModal
```

**Cambiar en A afecta a B?**
- app.js cargarMisListas() → Afecta renderizarSelectorListas() ✓
- drawer-listas.js window.crearListaModal → Usado por app.js ✓
- form-builder.js → Usado por drawer-listas.js ✓

---

## 5. ESTADO ACTUAL DE LAS LISTAS

**Base de datos**:
```sql
CREATE TABLE listas (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  usuario_propietario_id INTEGER NOT NULL, -- FOREIGN KEY
  privada BOOLEAN DEFAULT 1,
  icono TEXT DEFAULT '📋',
  color TEXT DEFAULT '#B5551A'
)

CREATE TABLE stock_lista (
  lista_id INTEGER,
  producto_id INTEGER,
  cantidad INTEGER,
  stock_minimo INTEGER,
  UNIQUE(lista_id, producto_id),
  FOREIGN KEY(lista_id) REFERENCES listas(id)
)
```

**API endpoints existentes**:
- GET /api/listas → Obtener listas del usuario
- POST /api/listas → Crear lista
- DELETE /api/listas/<id> → Eliminar lista
- PATCH /api/listas/<id> → Actualizar lista

---

## 6. CAMBIOS PENDIENTES (ROADMAP)

```
FASE 2: Validar listas obligatorias [REPLANEADA]
  ❌ CANCELADO: Abrir modal automático (causaba conflictos de listeners)
  
  ✅ NUEVO ENFOQUE: Banner obligatorio
  - [ ] Si usuario sin listas → Mostrar banner rojo: "Debes crear una lista"
  - [ ] Banner permanece visible hasta crear primera lista
  - [ ] Usuario hace click en "Crear lista" voluntariamente
  - [ ] Una vez creada, banner desaparece
  - [ ] Menos invasivo, más limpio

FASE 3: Bloquear artículos sin lista
  - [ ] Backend: Validar que lista existe
  - [ ] Frontend: Deshabilitar botón si no hay lista
  - [ ] TEST: No se puede agregar artículo sin lista

FASE 4: Permitir eliminar listas
  - [ ] Backend: Permitir DELETE últimas listas
  - [ ] Frontend: Modal de confirmación
  - [ ] TEST: Pode eliminar todas las listas

FASE 5: UX del modal obligatorio
  - [ ] Mostrar mensaje "Debes crear una lista"
  - [ ] Botón X deshabilitado visualmente
  - [ ] Teclado Escape deshabilitado
```

---

## 7. CHECKLIST PRE-CAMBIO

**ANTES de hacer CUALQUIER cambio, responder**:

- [ ] ¿Qué función/componente voy a cambiar?
- [ ] ¿Qué dependencias tiene?
- [ ] ¿Qué se puede romper?
- [ ] ¿Hay funciones existentes que reutilizar?
- [ ] ¿Cuál será mi test funcional?
- [ ] ¿He identificado puntos críticos?
- [ ] ¿He planificado el rollback si falla?

**DESPUÉS de cambio, verificar**:
- [ ] ¿Funciona el cambio específico?
- [ ] ¿Se rompió algo existente?
- [ ] ¿Los tests pasan?
- [ ] ¿Debo hacer commit?

---

## 8. FUNCIONALIDADES QUE NO SE PUEDEN ROMPER (CRÍTICAS)

| Funcionalidad | Estado | Crítica | Testear |
|---|---|---|---|
| Ver Stock | ✅ OK | CRÍTICA | Siempre |
| Ver Productos | ✅ OK | CRÍTICA | Siempre |
| Crear Productos | ✅ OK | CRÍTICA | Siempre |
| Filtrar por Categoría | ✅ OK | CRÍTICA | Siempre |
| Buscar Productos | ✅ OK | CRÍTICA | Siempre |
| Login/Register | ✅ OK | CRÍTICA | Siempre |
| Crear Lista | ✅ OK | CRÍTICA | Siempre |
| Ver Lista Compra | ✅ OK | CRÍTICA | Siempre |
| i18n Traducción | ✅ OK | CRÍTICA | Spot check |
| Compartir Listas | ✅ OK | MEDIA | Cambios en listas |
| Editar Lista | ✅ OK | MEDIA | Cambios en listas |
| Eliminar Lista | ✅ OK | MEDIA | Cambios en listas |

---

**Última actualización**: 2026-07-09 (Current session)
**Versión**: 1.0
**Responsable**: Desarrollo StockHogar
