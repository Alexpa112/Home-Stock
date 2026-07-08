# 🏗️ Arquitectura - Dreame!

## Principios de Diseño

- **OOP Puro**: Clases reutilizables, herencia, responsabilidad única
- **DRY**: No repetir código - centralizar validación, conversión, helpers
- **Minimalismo**: Zero frameworks pesados, cero build tools
- **Escalabilidad**: Estructura lista para crecer sin refactorizar

---

## Backend: Python + Flask

### Estructura Modular (Blueprints)

Cada dominio es un blueprint independiente en `stockhogar/rutas/`:

```
rutas/
├── auth.py           # Login, usuarios, sesión
├── productos.py      # Inventario
├── listas.py         # Múltiples listas de compra
├── articulos_lista.py # Ítems de listas
├── categorias.py     # Gestión de categorías
├── espacios.py       # Múltiples stocks
├── historial.py      # Catálogo + aprendizaje de iconos
├── tickets.py        # Gestión de tickets
└── ocr_tickets.py    # Escaneo OCR
```

### Capa de Abstracción (Base OOP)

**`stockhogar/api/base.py`** - Respuestas API estandarizadas:
```python
APIResponse.success(data, 200)
APIResponse.error("mensaje", 400)
APIResponse.validacion("error")
APIResponse.no_autorizado()

@requerir_sesion      # Decorador: requiere login
@manejo_errores       # Decorador: captura excepciones
def mi_endpoint():
    ...
```

### Validación Centralizada

**`stockhogar/utils/validation.py`** - Validador único:
```python
Validator.entero_no_negativo(valor, "nombre_campo")
Validator.string_requerido(valor, "nombre", max_len=100)
Validator.string_opcional(valor, default="", max_len=50)
```

### Conversión de Datos

**`stockhogar/utils/converters.py`** - Conversores JSON:
```python
DataConverter.producto_to_dict(row, dias_aviso_defecto)
DataConverter.lista_to_dict(row, usuario_id, include_detalles)
DataConverter.articulo_lista_to_dict(row)
```

---

## Frontend: JavaScript OOP

### DOM Manager - Centralización de Selectores

**`stockhogar/static/core/dom-manager.js`**

Problema antes:
```javascript
const btnTema = document.getElementById('btnTema');
const btnCategorias = document.getElementById('btnCategorias');
// ... 100+ líneas de selectores sueltos
```

Solución:
```javascript
// window.DOM es un singleton accesible globalmente
window.DOM.btnTema        // → elemento #btnTema
window.DOM.btnCategorias  // → elemento #btnCategorias
window.DOM.vistaStock     // → elemento #vistaStock

// Con caching automático + helpers
window.DOM.toggle(elemento)
window.DOM.toggleClass(elemento, 'activo')
window.DOM.clearCache()   // Si el DOM se recarga
```

Beneficios:
- Si un ID cambia, **solo cambias aquí**
- Caching automático de búsquedas
- Acceso consistente a todos los elementos

### API Client - Cliente HTTP Centralizado

**`stockhogar/static/core/api-client.js`**

Antes:
```javascript
fetch('/api/productos')
  .then(res => {
    if (res.status === 401) window.location.href = '/login';
    if (!res.ok) throw new Error('Error');
    return res.json();
  })
  // ... repetido 50 veces
```

Después:
```javascript
// window.API es un singleton
window.API.obtenerProductos()
window.API.crearProducto({ nombre: 'Leche', ... })
window.API.actualizarProducto(id, { cantidad: 5 })
window.API.borrarProducto(id)

// Manejo de errores centralizado
try {
  const productos = await window.API.obtenerProductos();
} catch (error) {
  if (error.isAuthError) { /* sesión expirada */ }
  if (error.isNetworkError) { /* sin conexión */ }
  if (error.isNotFound) { /* 404 */ }
}
```

Beneficios:
- **Un único lugar** para cambiar manejo de errores
- **Timeout automático**
- **Sesión 401 → login automático**
- **Error handling unificado**

### Módulos Funcionales

**`stockhogar/static/modules/`** - Componentes OOP:

```javascript
class ProductosManager extends EventTarget {
  constructor() {
    this.api = window.API;
    this.dom = window.DOM;
  }
  
  async cargar() { ... }
  async crear(datos) { ... }
  async actualizar(id, datos) { ... }
}

// Uso
window.productosManager = new ProductosManager();
window.productosManager.cargar();
```

---

## Base de Datos: SQLite

### Esquema Normalizado

```sql
-- Usuarios
users (id, nombre_usuario, contraseña_hash, fecha_creacion)

-- Espacios (multiple stocks)
espacios (id, usuario_propietario_id, nombre, color, fecha_creacion)

-- Productos (por espacio)
productos (id, espacio_id, nombre, categoria, cantidad, unidad, 
           stock_minimo, icono, dias_aviso, fecha_creacion, fecha_actualizacion)

-- Listas de compra (Bring! style)
listas (id, usuario_propietario_id, nombre, descripcion, icono, color, 
        privada, fecha_creacion, fecha_actualizacion)

-- Artículos en listas
articulos_lista (id, lista_id, nombre, cantidad, unidad, categoria, icono, 
                 completado, fecha_creacion, fecha_completado)

-- Permisos para listas compartidas
permisos_lista (lista_id, usuario_id, nivel, fecha_otorgado)

-- Catálogo (historial de artículos + iconos aprendidos)
historial_articulos (id, usuario_id, nombre, icono, categoria, unidad, 
                     cantidad_defecto, fecha_creacion)
```

### Migraciones

En `stockhogar/db.py`:
- **Esquema inicial**: Creado al primer inicio
- **Migraciones**: Funciones `_migrar_*` que se ejecutan solo cuando necesario
- **Foreign keys**: Habilitadas automáticamente (`PRAGMA foreign_keys = ON`)

---

## Flujo de Datos

### Crear Producto

```
Frontend                          Backend
═════════════════════════════════════════════

usuario → modal → JavaScript      
  ↓
window.API.crearProducto()       
  ├─ POST /api/productos         → @bp.route("", POST)
  │                                ├─ Validator.string_requerido()
  │                                ├─ Validator.entero_no_negativo()
  │                                ├─ crear_producto_nuevo()
  │                                ├─ revisar_stock_bajo()
  │                                └─ APIResponse.success(producto)
  └─ render en la lista
```

### Refactorización: Antes vs Después

**Antes: Código duplicado**
```python
# En 5 rutas diferentes
try:
    cantidad = int(datos.get("cantidad", 0))
except ValueError:
    return jsonify({"error": "..."}), 400
```

**Después: Una única responsabilidad**
```python
# En utils/validation.py
cantidad = Validator.entero_no_negativo(datos.get("cantidad"), "cantidad")

# En todas las rutas
@manejo_errores
def mi_ruta():
    cantidad = Validator.entero_no_negativo(...)
```

---

## Seguridad

### Autenticación
- Hash de contraseñas: `werkzeug.security.generate_password_hash()`
- Sesiones persistentes: 365 días con cookie segura
- Decorador `@requerir_sesion` en endpoints protegidos

### Validación
- **Frontend**: Validación cliente (UX rápida)
- **Backend**: Validación servidor siempre (seguridad)
- Centralizada en `Validator` clase

### XSS Prevention
- `DataConverter.safe_field()` → evita acceso a keys no existentes
- Frontend: escape de HTML en templates Jinja2
- API devuelve JSON (no HTML inyectado)

### CSRF
- Flask CSRF protection automática en formularios
- API endpoints usan sesión (no tokens separados)

---

## Optimizaciones

| Problema | Solución | Dónde |
|----------|----------|-------|
| **100+ líneas selectores DOM sueltos** | DOMManager singleton | `core/dom-manager.js` |
| **Fetch calls duplicadas (50x)** | APIClient singleton | `core/api-client.js` |
| **Validación en cada ruta** | Validator clase | `utils/validation.py` |
| **row_to_dict() copiado 10x** | DataConverter | `utils/converters.py` |
| **Try-catch patterns iguales** | Decorador @manejo_errores | `api/base.py` |
| **Respuestas JSON inconsistentes** | APIResponse clase | `api/base.py` |

---

## Escalabilidad: Añadir Nueva Funcionalidad

### Ejemplo: Nuevo endpoint "favoritos"

1. **Backend**: Crea `stockhogar/rutas/favoritos.py`
```python
from ..api import APIResponse, requerir_sesion, manejo_errores
from ..utils import Validator, DataConverter

@bp.route("", methods=["GET"])
@requerir_sesion
@manejo_errores
def listar_favoritos():
    # Usa clases base, no duplicas validación
    ...
```

2. **Frontend**: Crea `stockhogar/static/modules/favoritos-manager.js`
```javascript
class FavoritosManager {
  constructor() {
    this.api = window.API;      // Usa singleton
    this.dom = window.DOM;      // Usa singleton
  }
  
  async cargar() {
    const favoritos = await this.api.obtenerFavoritos();
    // Renderiza...
  }
}
```

3. **Registra en `__init__.py`**: `app.register_blueprint(favoritos.bp)`

**Resultado**: 0 código duplicado, todo encapsulado.

---

## Convenciones

- **Archivos Python**: `snake_case`
- **Clases Python**: `PascalCase`
- **Archivos JS**: `kebab-case` (menos módulos) o `camelCase` (clases)
- **Clases JS**: `PascalCase`
- **IDs HTML**: `camelCase` con prefijo de módulo (ej: `btnAbrirModal`, `modalProducto`)
- **Funciones privadas**: Prefijo `_` en Python, `#` o prefijo `_` en JS
- **Constantes**: `UPPER_SNAKE_CASE`

---

## Roadmap Futuro

- [ ] Compartir listas entre usuarios (API lista, falta UI)
- [ ] Historial de cambios (auditoría)
- [ ] Gráficos de consumo
- [ ] Integración con APIs de supermercados
- [ ] App móvil nativa (Flutter/React Native)
