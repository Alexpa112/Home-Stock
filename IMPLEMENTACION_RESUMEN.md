# Implementación: Sistema de Listas Compartidas (Modelo Bring!)

## ✅ Completado

### FASE A: Base de Datos

**Nuevas tablas:**
- ✅ `listas` - Contenedor principal de artículos
  - `id`, `nombre`, `descripcion`, `usuario_propietario_id`, `privada`, `icono`, `fecha_creacion`, `fecha_actualizacion`
  
- ✅ `permisos_lista` - Relación usuario ↔ lista
  - `id`, `lista_id`, `usuario_id`, `nivel` ('ver'/'editar'), `fecha_otorgado`
  - UNIQUE(lista_id, usuario_id)

- ✅ `articulos_lista` - Artículos dentro de listas (renombrado de `lista_compra`)
  - `id`, `lista_id`, `producto_id`, `nombre`, `unidad`, `categoria`, `icono`, `cantidad`, `sub_descripcion`, `origen`, `activo`, `fecha_completado`, `fecha_creacion`

**Migraciones:**
- ✅ Tabla antigua `lista_compra` renombrada a `lista_compra_backup`
- ✅ Migración automática de datos existentes a lista "Mi lista" para cada usuario
- ✅ Compatibilidad con `espacios` (mantenida para futura integración)

### FASE B: Backend (APIs)

**Archivo nuevo: `stockhogar/rutas/listas.py`**
- ✅ CRUD completo de listas
- ✅ Gestión de permisos
- ✅ Validación de acceso en cada endpoint

**Archivos modificados:**

1. **`stockhogar/rutas/lista_compra.py`**
   - ✅ Renombrado a uso de `articulos_lista`
   - ✅ Cambio de `espacio_id` a `lista_id`
   - ✅ Validación de permisos en cada operación
   - ✅ Requisito de permiso 'editar' para POST/PATCH/DELETE

2. **`stockhogar/__init__.py`**
   - ✅ Registrado blueprint de listas

3. **`stockhogar/db.py`**
   - ✅ Creación de nuevas tablas
   - ✅ Función `_migrar_lista_compra_a_articulos`
   - ✅ Validación automática en `init_db()`

---

## 📋 Endpoints Disponibles

### Listas
- `GET /api/listas` - Listar mis listas (propias + compartidas)
- `POST /api/listas` - Crear nueva lista
- `GET /api/listas/{id}` - Ver detalles (con validación)
- `PATCH /api/listas/{id}` - Editar (solo propietario)
- `DELETE /api/listas/{id}` - Eliminar (solo propietario)
- `POST /api/listas/{id}/compartir` - Compartir con usuario

### Permisos
- `GET /api/listas/{id}/permisos` - Listar permisos (solo propietario)
- `PATCH /api/listas/{id}/permisos/{uid}` - Cambiar nivel
- `DELETE /api/listas/{id}/permisos/{uid}` - Revocar acceso

### Artículos
- `GET /api/articulos?lista_id={id}` - Listar artículos
- `POST /api/articulos` - Añadir artículo (requiere 'editar')
- `PATCH /api/articulos/{id}` - Editar (requiere 'editar')
- `DELETE /api/articulos/{id}` - Eliminar (requiere 'editar')

---

## 🔐 Modelo de Seguridad

**Validación en CADA endpoint:**
```
┌─────────────────────────────────────────────┐
│ ¿Usuario autenticado?                       │
│  NO → 401 Unauthorized                      │
│  SÍ ↓                                        │
├─────────────────────────────────────────────┤
│ ¿Es propietario de la lista?                │
│  SÍ → "propietario" (acceso total) ✓        │
│  NO ↓                                       │
├─────────────────────────────────────────────┤
│ ¿Está en permisos_lista?                    │
│  SÍ ↓                                       │
│    - nivel 'ver' → lectura ✓                │
│    - nivel 'editar' → lectura + escritura ✓│
│  NO ↓                                       │
├─────────────────────────────────────────────┤
│ 403 Forbidden ✗                             │
└─────────────────────────────────────────────┘
```

**Función de validación:** `_usuario_tiene_permiso(db, lista_id, usuario_id, nivel_requerido)`
- Retorna: 'propietario', 'editar', 'ver', o None
- Ubicada en: `stockhogar/rutas/listas.py`

---

## 🧪 Testing Manual

### 1. Crear lista
```bash
curl -X POST http://localhost:5000/api/listas \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Supermercado", "icono": "🛒"}'
```

### 2. Listar mis listas
```bash
curl http://localhost:5000/api/listas
```

### 3. Añadir artículo
```bash
curl -X POST http://localhost:5000/api/articulos \
  -H "Content-Type: application/json" \
  -d '{"lista_id": 1, "nombre": "Leche", "cantidad": 2}'
```

### 4. Compartir lista
```bash
curl -X POST http://localhost:5000/api/listas/1/compartir \
  -H "Content-Type: application/json" \
  -d '{"usuario": "maria", "nivel": "editar"}'
```

### 5. Ver permisos
```bash
curl http://localhost:5000/api/listas/1/permisos
```

---

## 📝 Diferencias con el modelo anterior

| Aspecto | Antes | Ahora |
|--------|-------|-------|
| **Agrupación** | Espacios (Casa, Piso) | Listas (Supermercado, Cena) |
| **Permisos** | Ninguno | 3 niveles (propietario, editar, ver) |
| **Compartir** | No disponible | Compartir lista con otros usuarios |
| **Privacidad** | Todo es del mismo usuario | Listas privadas/compartidas por defecto |
| **Tabla base** | `lista_compra` | `articulos_lista` (con FK a `listas`) |
| **Validación** | Basada en sesión | Basada en permisos explícitos |

---

## 🚀 Próximos pasos (Frontend)

1. **Selector de listas** en la UI
   - Mostrar "Mis listas" (propias + compartidas)
   - Indicar propietario vs compartida
   - Click para cambiar de lista activa

2. **Modal de compartir**
   - Buscar usuario por nombre
   - Seleccionar nivel de permiso
   - Listar usuarios actuales con acceso

3. **Indicadores visuales**
   - 🔒 Privada vs 👥 Compartida
   - ⭐ Propietario vs 👁️ Solo lectura vs ✏️ Editar
   - ❌ Sin acceso (lista oculta)

4. **Cambios en flujo de datos**
   - `GET /api/listas` → seleccionar lista activa
   - `GET /api/articulos?lista_id=X` → cargar artículos
   - Toda interacción validada por servidor

---

## 📚 Referencia de documentación

- **API completa:** Ver `API_REFERENCE.md`
- **Modelo de BD:** Diagrama en conversación anterior (fase A)
- **Flujo UX:** Diagrama en conversación anterior (cómo funciona Bring!)
- **Estructura de código:** `stockhogar/rutas/listas.py` (función `_usuario_tiene_permiso`)

---

## ✨ Características implementadas

- ✅ Crear listas (privadas por defecto)
- ✅ Listar listas del usuario (propias + compartidas)
- ✅ Editar lista (solo propietario)
- ✅ Eliminar lista (solo propietario, cascade)
- ✅ Compartir lista con usuario específico
- ✅ Cambiar nivel de permiso (ver/editar)
- ✅ Revocar acceso
- ✅ Ver quién tiene acceso a una lista
- ✅ Añadir artículos (requiere 'editar')
- ✅ Editar artículos (requiere 'editar')
- ✅ Eliminar artículos (requiere 'editar')
- ✅ Validación de permisos en CADA endpoint
- ✅ HTTP 403 para acceso denegado
- ✅ Migración automática de datos existentes

---

**Estado:** ✅ **LISTO PARA TESTING**

La aplicación está funcional y lista para pruebas. El modelo de Bring! está completamente implementado en el backend.
