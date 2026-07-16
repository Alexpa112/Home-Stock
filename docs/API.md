# 📡 Referencia API - Dreame!

## Autenticación

Todos los endpoints (excepto `/login`) requieren sesión activa.

```javascript
// Si sesión expira, API Client redirige a /login automáticamente
const productos = await window.API.obtenerProductos();  // ✓
```

---

## Endpoints

### Productos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/productos` | Listar todos (del espacio actual, aislado por sesión) |
| `POST` | `/api/productos` | Crear nuevo producto |
| `PATCH` | `/api/productos/:id` | Actualizar producto (o `delta` para +/-) |
| `DELETE` | `/api/productos/:id` | Eliminar producto |

#### GET /api/productos
```javascript
const productos = await window.API.obtenerProductos();
// [
//   {
//     id: 1,
//     nombre: "Leche",
//     categoria: "Lácteos",
//     cantidad: 2,
//     unidad: "l",
//     stock_minimo: 1,
//     icono: "🥛",
//     revisar_caducidad: false,
//     dias_aviso: 30,
//     ...
//   },
//   ...
// ]
```

#### POST /api/productos
```javascript
const nuevo = await window.API.crearProducto({
  nombre: "Pan",           // Requerido
  categoria: "Panadería",  // Default: "Otros"
  cantidad: 1,             // Default: 0
  unidad: "ud",            // Default: "ud"
  stock_minimo: 2,         // Default: 1
  icono: "🥖",             // Opcional
  dias_aviso: 7            // Default: 30 días
});
// { id: 123, nombre: "Pan", ... }
```

#### PATCH /api/productos/:id

**Opción 1: Delta (aumentar/disminuir)**
```javascript
// Aumentar 2 unidades
await window.API.actualizarProducto(1, { delta: 2 });

// Disminuir 1 unidad
await window.API.actualizarProducto(1, { delta: -1 });
```

**Opción 2: Actualizar campos**
```javascript
await window.API.actualizarProducto(1, {
  nombre: "Leche desnatada",
  cantidad: 3,
  stock_minimo: 1,
  icono: "🥛"
});
```

#### DELETE /api/productos/:id
```javascript
await window.API.borrarProducto(1);  // Devuelve void
```

---

### Listas de Compra

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/listas` | Listar mis listas (propias + compartidas) |
| `POST` | `/api/listas` | Crear nueva lista |
| `PATCH` | `/api/listas/:id` | Actualizar lista |
| `DELETE` | `/api/listas/:id` | Eliminar lista |
| `POST` | `/api/listas/:id/seleccionar` | Seleccionar como activa |
| `GET` | `/api/listas/buscar-usuarios` | Buscar usuarios para compartir (`rutas/permisos.py`) |
| `GET` | `/api/listas/:id/miembros` | Ver miembros/permisos de la lista |
| `POST` | `/api/listas/:id/compartir` | Compartir con otro usuario |
| `PATCH` | `/api/listas/:id/permisos/:usuario_id` | Cambiar nivel de permiso |
| `DELETE` | `/api/listas/:id/permisos/:usuario_id` | Revocar acceso |
| `POST` | `/api/listas/aceptar-invitacion/:codigo` | Aceptar invitación por email |

#### GET /api/listas
```javascript
const { propias, compartidas } = await window.API.obtenerListas();
// propias: [
//   {
//     id: 1,
//     nombre: "Mi lista",
//     descripcion: "...",
//     icono: "📋",
//     color: "#B5551A",
//     privada: true,
//     mi_rol: "propietario",
//     usuario_propietario_id: 5,
//     ...
//   }
// ]
// compartidas: [ lista compartida conmigo ]
```

#### POST /api/listas
```javascript
const nueva = await window.API.crearLista({
  nombre: "Compra semanal",      // Requerido
  descripcion: "Cada lunes",     // Opcional
  icono: "🛒",                   // Default: "📋"
  color: "#B5551A",              // Default color
  privada: true                  // Default: true
});
```

#### POST /api/listas/:id/seleccionar
```javascript
// Cambiar la lista activa
await window.API.seleccionarLista(5);
// Desde ahora, artículos nuevos van aquí
```

#### POST /api/listas/:id/compartir
```javascript
await window.API.compartirLista(1, {
  usuario: "maria",     // Nombre usuario
  nivel: "editar"       // "editar" o "ver"
});
```

---

### Artículos (Items en Listas)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/articulos?lista_id=1` | Artículos de una lista |
| `POST` | `/api/articulos` | Crear artículo |
| `PATCH` | `/api/articulos/:id` | Actualizar artículo |
| `DELETE` | `/api/articulos/:id` | Eliminar artículo |

#### GET /api/articulos?lista_id=1
```javascript
const articulos = await window.API.obtenerArticulos();
// [
//   {
//     id: 1,
//     lista_id: 5,
//     nombre: "Leche",
//     cantidad: 2,
//     unidad: "l",
//     categoria: "Lácteos",
//     icono: "🥛",
//     completado: false,
//     fecha_creacion: "2026-07-08T10:30:00",
//     fecha_completado: null
//   }
// ]
```

#### POST /api/articulos
```javascript
const nuevo = await window.API.crearArticulo({
  lista_id: 5,           // Requerido
  nombre: "Yogur",       // Requerido
  cantidad: 3,           // Default: 1
  unidad: "pack",        // Default: "ud"
  categoria: "Lácteos",  // Opcional
  icono: "🍮"            // Opcional
});
```

#### PATCH /api/articulos/:id
```javascript
// Marcar como completado
await window.API.actualizarArticulo(1, {
  completado: true
});

// O cambiar cantidad
await window.API.actualizarArticulo(1, {
  cantidad: 5
});
```

---

### Categorías

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/categorias` | Listar todas |
| `POST` | `/api/categorias` | Crear nueva |
| `PATCH` | `/api/categorias/:id` | Actualizar |
| `DELETE` | `/api/categorias/:id` | Eliminar |

#### GET /api/categorias
```javascript
const cats = await window.API.obtenerCategorias();
// [
//   { id: 1, nombre: "Lácteos", icono: "🥛" },
//   { id: 2, nombre: "Frutas", icono: "🍎" },
//   ...
// ]
```

---

### Espacios (Múltiples Stocks) — backend legacy, sin UI actual

Estos endpoints existen en `rutas/espacios.py` y siguen usándose internamente
para aislar `productos` por sesión (`obtener_espacio_actual`), pero **no hay
ninguna pantalla en la app que los llame** (`app.js` no invoca `/api/espacios`).
Ver la nota en `README.md` ("Varios stocks (espacios)").

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/espacios` | Listar espacios del usuario |
| `POST` | `/api/espacios` | Crear espacio |
| `PATCH` | `/api/espacios/:id` | Actualizar |
| `DELETE` | `/api/espacios/:id` | Eliminar |

---

## Códigos HTTP

| Código | Significado |
|--------|-------------|
| `200` | OK - Éxito |
| `201` | Created - Recurso creado |
| `204` | No Content - Éxito sin datos (DELETE) |
| `400` | Bad Request - Datos inválidos |
| `401` | Unauthorized - Sin sesión |
| `403` | Forbidden - Sin permiso |
| `404` | Not Found - Recurso no existe |
| `500` | Server Error - Error interno |

---

## Manejo de Errores

```javascript
try {
  const producto = await window.API.obtenerProductos();
} catch (error) {
  if (error.isAuthError) {
    console.log("Sesión expirada (401)");
    // Se redirige automáticamente
  }
  if (error.isValidationError) {
    console.log("Datos inválidos:", error.message);
  }
  if (error.isNotFound) {
    console.log("No encontrado (404)");
  }
  if (error.isNetworkError) {
    console.log("Sin conexión");
  }
  if (error.isServerError) {
    console.log("Error en servidor (5xx)");
  }
}
```

---

## Paginación (Futuro)

Por ahora NO hay paginación. Si hay >1000 productos:
```python
# TODO: Implementar en config.py
ITEMS_POR_PAGINA = 50
```

---

## Rate Limiting

No hay rate limiting implementado. En producción:
```python
# TODO: Añadir flask-limiter
# @limiter.limit("100 per hour")
# @bp.route("/api/productos")
```

---

## Webhooks

No hay webhooks. Para notificaciones:
- Usa polling (`setInterval`)
- O WebSocket (futuro)

---

## Ejemplos Completos

### Flujo: Crear producto y automaticamente añadir a lista

```javascript
// 1. Crear producto
const producto = await window.API.crearProducto({
  nombre: "Leche",
  cantidad: 3,
  stock_minimo: 1
});

// 2. Si producto está bajo stock, se crea automáticamente en lista de compra
// (Backend lo hace en revisar_stock_bajo())

// 3. Obtener artículos
const articulos = await window.API.obtenerArticulos();
// Verás el artículo de leche si está bajo mínimo
```

### Flujo: Compartir lista con alguien

```javascript
// 1. Crear lista (como propietario)
const lista = await window.API.crearLista({
  nombre: "Compra conjunta"
});

// 2. Compartir
await window.API.compartirLista(lista.id, {
  usuario: "maria",
  nivel: "editar"
});

// 3. Otra persona:
//    - Ve en "listas compartidas"
//    - Puede editar si nivel="editar"
//    - No puede cambiar permisos
```

---

Para más detalles técnicos: Lee [ARQUITECTURA.md](ARQUITECTURA.md)
