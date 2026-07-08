# StockHogar - API Reference (Modelo Bring!)

## Autenticación

**Login:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "usuario": "juan",
  "password": "password123"
}
```

**Logout:**
```http
POST /api/auth/logout
```

---

## Listas (Nuevo modelo Bring!)

### Listar listas del usuario
Retorna listas propias + compartidas con el usuario.

```http
GET /api/listas
```

**Response:**
```json
{
  "propias": [
    {
      "id": 1,
      "nombre": "Supermercado",
      "descripcion": "Compra semanal",
      "icono": "🛒",
      "privada": true,
      "usuario_propietario_id": 1,
      "mi_rol": "propietario",
      "total_articulos": 5,
      "fecha_creacion": "2026-01-15T10:30:00",
      "fecha_actualizacion": "2026-01-20T14:45:00"
    }
  ],
  "compartidas": [
    {
      "id": 2,
      "nombre": "Cena en casa",
      "icono": "🍽️",
      "privada": false,
      "usuario_propietario_id": 2,
      "mi_rol": "editar",
      "fecha_creacion": "2026-01-18T09:00:00",
      "fecha_actualizacion": "2026-01-20T16:20:00"
    }
  ]
}
```

### Crear lista
```http
POST /api/listas
Content-Type: application/json

{
  "nombre": "Compra semanal",
  "descripcion": "Compras del fin de semana",
  "icono": "🛒",
  "privada": true
}
```

### Obtener detalles de lista
```http
GET /api/listas/{lista_id}
```

**Response:**
```json
{
  "id": 1,
  "nombre": "Supermercado",
  "descripcion": "Compra semanal",
  "icono": "🛒",
  "privada": true,
  "usuario_propietario_id": 1,
  "mi_rol": "propietario",
  "total_articulos": 5,
  "fecha_creacion": "2026-01-15T10:30:00",
  "fecha_actualizacion": "2026-01-20T14:45:00"
}
```

### Actualizar lista (solo propietario)
```http
PATCH /api/listas/{lista_id}
Content-Type: application/json

{
  "nombre": "Compra del mes",
  "descripcion": "Actualizado",
  "icono": "🛍️",
  "privada": false
}
```

### Eliminar lista (solo propietario)
```http
DELETE /api/listas/{lista_id}
```

---

## Permisos de Listas

### Compartir lista con usuario
```http
POST /api/listas/{lista_id}/compartir
Content-Type: application/json

{
  "usuario": "maria",
  "nivel": "editar"
}
```

**Niveles disponibles:**
- `"ver"` - Solo lectura
- `"editar"` - Lectura + escritura de artículos

**Response:**
```json
{
  "mensaje": "Lista compartida con maria",
  "nivel": "editar",
  "usuario": "maria"
}
```

### Listar permisos (solo propietario)
```http
GET /api/listas/{lista_id}/permisos
```

**Response:**
```json
{
  "propietario": {
    "usuario_id": 1,
    "nombre_usuario": "juan",
    "nivel": "propietario"
  },
  "compartida_con": [
    {
      "usuario_id": 2,
      "nombre_usuario": "maria",
      "nivel": "editar",
      "fecha_otorgado": "2026-01-20T14:00:00"
    },
    {
      "usuario_id": 3,
      "nombre_usuario": "carlos",
      "nivel": "ver",
      "fecha_otorgado": "2026-01-19T10:00:00"
    }
  ]
}
```

### Cambiar nivel de permiso (solo propietario)
```http
PATCH /api/listas/{lista_id}/permisos/{usuario_id}
Content-Type: application/json

{
  "nivel": "ver"
}
```

### Revocar acceso (solo propietario)
```http
DELETE /api/listas/{lista_id}/permisos/{usuario_id}
```

---

## Artículos en Listas

### Listar artículos de una lista
```http
GET /api/articulos?lista_id={lista_id}
```

**Response:**
```json
{
  "pendientes": [
    {
      "id": 1,
      "lista_id": 1,
      "producto_id": null,
      "nombre": "Leche",
      "unidad": "l",
      "categoria": "Lácteos",
      "icono": "🥛",
      "cantidad": 2,
      "sub_descripcion": "Desnatada",
      "origen": "manual",
      "activo": true
    }
  ],
  "completados": [
    {
      "id": 2,
      "lista_id": 1,
      "nombre": "Pan",
      "unidad": "ud",
      "categoria": "Panadería",
      "icono": "🍞",
      "cantidad": 1,
      "activo": false
    }
  ]
}
```

### Añadir artículo (requiere permiso 'editar')
```http
POST /api/articulos
Content-Type: application/json

{
  "lista_id": 1,
  "nombre": "Leche",
  "cantidad": 2,
  "unidad": "l",
  "categoria": "Lácteos",
  "icono": "🥛",
  "sub_descripcion": "Desnatada"
}
```

### Actualizar artículo (requiere permiso 'editar')
```http
PATCH /api/articulos/{item_id}
Content-Type: application/json

{
  "cantidad": 3,
  "activo": false
}
```

### Eliminar artículo (requiere permiso 'editar')
```http
DELETE /api/articulos/{item_id}
```

---

## Matriz de Permisos

| Acción | Propietario | Editar | Ver | Sin permiso |
|--------|-------------|--------|-----|------------|
| Ver lista | ✅ | ✅ | ✅ | ❌ |
| Añadir artículos | ✅ | ✅ | ❌ | ❌ |
| Eliminar artículos | ✅ | ✅ | ❌ | ❌ |
| Editar lista (nombre, etc) | ✅ | ❌ | ❌ | ❌ |
| Compartir / Invitar | ✅ | ❌ | ❌ | ❌ |
| Eliminar lista | ✅ | ❌ | ❌ | ❌ |
| Cambiar nivel de permiso | ✅ | ❌ | ❌ | ❌ |
| Revocar acceso | ✅ | ❌ | ❌ | ❌ |

---

## Códigos de Error

- `400 Bad Request` - Parámetros inválidos
- `401 Unauthorized` - No autenticado
- `403 Forbidden` - No tienes permisos
- `404 Not Found` - Recurso no existe
- `500 Internal Server Error` - Error del servidor

---

## Flujo Típico de Uso

1. **Login:**
   ```
   POST /api/auth/login → session token
   ```

2. **Crear lista:**
   ```
   POST /api/listas → lista_id
   ```

3. **Añadir artículos:**
   ```
   POST /api/articulos (lista_id, nombre, cantidad, etc)
   ```

4. **Ver artículos:**
   ```
   GET /api/articulos?lista_id=1
   ```

5. **Compartir lista:**
   ```
   POST /api/listas/{lista_id}/compartir (usuario, nivel)
   ```

6. **Otro usuario ve listas compartidas:**
   ```
   GET /api/listas → aparece en "compartidas"
   ```
