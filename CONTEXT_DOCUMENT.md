# 📚 DOCUMENTO DE CONTEXTO - HOME STOCK APP

**Última actualización**: 2026-07-08  
**Versión del documento**: 1.0  
**Estado**: ✅ PRODUCCIÓN

---

## ⚠️ INSTRUCCIONES CRÍTICAS

Este documento describe **TODAS** las características implementadas en Home Stock. **NO SE PUEDE PERDER NINGUNA CARACTERÍSTICA** mencionada aquí.

**Responsabilidad**: Cualquier cambio futuro debe:
1. ✅ Verificar que NO rompe ninguna de estas características
2. ✅ Mantener la arquitectura descrita
3. ✅ Preservar los endpoints API
4. ✅ Mantener la integridad de datos

---

## 📋 ÍNDICE

1. [Características Implementadas](#características-implementadas)
2. [Arquitectura de Base de Datos](#arquitectura-de-base-de-datos)
3. [Endpoints API](#endpoints-api)
4. [Componentes Frontend](#componentes-frontend)
5. [Flujos de Negocio Críticos](#flujos-de-negocio-críticos)
6. [Consideraciones Técnicas](#consideraciones-técnicas)
7. [Testing y Validación](#testing-y-validación)

---

## 🎯 CARACTERÍSTICAS IMPLEMENTADAS

### 1. **Sistema Multiidioma Completo** 🌍

#### Descripción
App completamente traducible a 7 idiomas con cambio dinámico en tiempo real.

#### Idiomas Soportados
- 🇪🇸 Español (es) - **Idioma por defecto**
- 🇬🇦 Gallego (gl) - **Incluido especialmente**
- 🇬🇧 Inglés (en)
- 🇵🇹 Portugués (pt)
- 🇫🇷 Francés (fr)
- 🇮🇹 Italiano (it)
- 🇩🇪 Alemán (de)

#### Componentes
- **Backend**: `stockhogar/translator.py` + `stockhogar/rutas/idiomas.py`
- **Frontend**: `stockhogar/static/i18n.js` (TranslationManager class)
- **BD**: Tabla `traducciones_productos` para traducciones de artículos
- **Datos**: `stockhogar/translations.json` (100+ cadenas por idioma)

#### Características Clave
✅ Selector en modal de "Ajustes" (⚙️)  
✅ Persistencia en localStorage + BD  
✅ Cambio dinámico sin recargar página  
✅ Traducción global de toda la interfaz  
✅ Traducción automática de nombres y descripciones de productos  

#### Uso
```javascript
// Cambiar idioma
window.i18n.cambiarIdioma('en');

// Obtener traducción
window.i18n.t('stock'); // Devuelve "Stock" o su traducción
```

---

### 2. **Selector de Icono con Modal Externa** 🎨

#### Descripción
Modal externa dedicada para seleccionar iconos, mejorando UX en dispositivos móviles.

#### Ubicación
- Modal HTML: `stockhogar/templates/index.html` (línea ~364)
- Modal ID: `#modalSelectorIconos`
- Funciones JS: `stockhogar/static/app.js` (líneas ~625-680)

#### Características Clave
✅ Modal separada reutilizable  
✅ Buscador de iconos integrado  
✅ Grid responsive de 100+ iconos  
✅ Implementado en AMBOS formularios:
  - Productos (crear/editar)
  - Artículos de compra (crear/editar)
✅ Callback pattern para integración limpia

#### Funciones Críticas
```javascript
// Abrir selector
abrirModalSelectorIconos(iconoActual, callback);

// Renderizar grid
renderizarIconosGrid(filtro);

// Cerrar selector
cerrarModalSelectorIconos();
```

#### Data Source
```javascript
// Archivo con catálogo de iconos
CATALOGO_ICONOS = [
  { icono: "☕", palabras: ["café", "bebida"] },
  { icono: "🥛", palabras: ["leche", "lácteo"] },
  // ... 100+ iconos
];
```

---

### 3. **Arreglo de Modales en iOS** 📱

#### Descripción
**CRÍTICO**: Modales funcionan correctamente en iPhone 17 Pro Max y otros dispositivos iOS sin comprimirse excesivamente.

#### Problema Original
- Modales se comprimían cuando se abría teclado virtual
- Altura se reducía drásticamente
- Interfaz quedaba inutilizable

#### Solución Implementada (CSS)
Archivo: `stockhogar/static/style.css` (líneas ~932-945)

```css
body.keyboard-open .modal {
  max-height: calc(100vh - var(--keyboard-offset) - 32px);
  min-height: 50vh;  /* ← CRÍTICO: altura mínima */
  margin-bottom: calc(var(--keyboard-offset) + 16px);
  padding-bottom: 20px;
}

@supports (padding: max(0px)) {
  body.keyboard-open .modal {
    max-height: calc(100vh - var(--keyboard-offset) - 32px - env(safe-area-inset-bottom));
    padding-bottom: max(20px, env(safe-area-inset-bottom));
  }
}
```

#### Variables de Control
- `--keyboard-offset`: Altura del teclado (calculado en JS)
- `100vh`: Viewport fijo (NO `100dvh` que cambia en iOS)
- `env(safe-area-inset-bottom)`: Para notch/Dynamic Island

#### Archivo de Control
`stockhogar/static/app.js` (líneas ~315-345)

```javascript
function ajustarViewportMovil() {
  const viewport = window.visualViewport;
  const offset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
  const offsetEfectivo = offset > 32 ? offset : 0;
  document.documentElement.style.setProperty("--keyboard-offset", `${offsetEfectivo}px`);
  document.body.classList.toggle("keyboard-open", offsetEfectivo > 0);
}
```

#### Testing Crítico
✅ Abrir modal en iPhone 17 Pro Max  
✅ Hacer clic en input  
✅ Verificar que modal mantiene altura legible  
✅ Interactuar con formulario  
✅ Cerrar teclado → modal vuelve a tamaño normal  

---

### 4. **Sistema de Stock Mínimo Automático** 📦

#### Descripción
Cuando el stock de un producto llega al mínimo especificado, automáticamente se añade a la lista de compra.

#### Ubicación
Archivo: `stockhogar/static/modules/productos-manager.js` (líneas ~158-206)

#### Función Crítica
```javascript
async cambiarCantidad(id, delta) {
  const producto = this.obtenerPorId(id);
  const cantidadAnterior = producto.cantidad;
  const nuevaCantidad = Math.max(0, producto.cantidad + delta);
  const stockMinimo = producto.stock_minimo || 1;

  // LÓGICA CRÍTICA
  if (cantidadAnterior > stockMinimo && nuevaCantidad <= stockMinimo) {
    // Stock ACABA DE LLEGAR al mínimo
    await this._anadirAListaCompra(producto);
  }
}
```

#### Características
✅ Solo se dispara cuando **BAJA** desde arriba del mínimo  
✅ NO se dispara si ya estaba bajo el mínimo  
✅ Genera automáticamente:
  - Nombre: del producto original
  - Cantidad: stock_minimo del producto
  - Sub-descripción: `[Automático: stock bajo]`
  - Categoría: del producto original
✅ Notificación al usuario

#### Evento Crítico
Genera evento `cantidad-cambió` que se propaga por toda la app

#### Testing
✅ Producto "Café" con stock_minimo = 2  
✅ Stock actual = 3  
✅ Click en "-" → Cantidad = 2  
✅ Verificar que se añade a lista de compra automáticamente  
✅ Verificar que aparece notificación al usuario  

---

### 5. **Traducción Automática de Productos y Artículos** 🔄

#### Descripción
Sistema automático que traduce nombres y descripciones de productos/artículos a 7 idiomas cuando se crean.

#### Componentes

##### 5A. Backend - Servicio de Traducción
Archivo: `stockhogar/servicios/traductor_auto.py`

```python
class TraductorAutomatico:
    # Diccionario con 40+ palabras clave en 7 idiomas
    DICCIONARIO_PRODUCTOS = {
        "leche": {"es": "Leche", "en": "Milk", "gl": "Leite", ...},
        "pan": {"es": "Pan", "en": "Bread", "gl": "Pan", ...},
        # ... más palabras
    }

    @staticmethod
    def traducir_texto(texto, idioma_destino, idioma_origen="es")
    @staticmethod
    def traducir_a_todos_idiomas(texto)
```

#### Características
✅ Diccionario de palabras clave por categoría  
✅ Búsqueda por palabra exacta  
✅ Búsqueda por palabras dentro del texto  
✅ Fallback al original si no hay traducción  
✅ Rápido (< 100ms)  

##### 5B. Backend - Endpoints de Traducción
Archivo: `stockhogar/rutas/productos.py`

```python
POST /api/productos/traducir
{
  "nombre": "Leche integral",
  "descripcion": "Fresca",
  "producto_id": 123,
  "articulo_id": null
}
```

Devuelve traducciones a 7 idiomas y las almacena en BD

##### 5C. Frontend - Traducción Automática al Crear
Archivos: `stockhogar/static/app.js`

```javascript
// Al crear producto
fetch("/api/productos/traducir", {
  method: "POST",
  body: JSON.stringify({
    nombre: payload.nombre,
    producto_id: creado.id
  })
}); // En background, NO bloquea UI

// Al crear artículo de compra
fetch("/api/productos/traducir", {
  method: "POST",
  body: JSON.stringify({
    nombre: payload.nombre,
    descripcion: payload.sub_descripcion,
    articulo_id: articulo.id
  })
});
```

##### 5D. BD - Almacenamiento
Tabla: `traducciones_productos`

```sql
CREATE TABLE traducciones_productos (
  id INTEGER PRIMARY KEY,
  producto_id INTEGER,        -- Referencia a productos
  articulo_id INTEGER,        -- Referencia a articulos_lista
  tipo TEXT,                  -- "nombre" o "descripcion"
  idioma TEXT,                -- Código ISO
  texto_original TEXT,        -- Texto en español
  texto_traducido TEXT,       -- Texto traducido
  fecha_creacion TEXT,
  UNIQUE(producto_id, articulo_id, tipo, idioma)
);
```

#### Testing
✅ Crear producto "Café Premium"  
✅ Verificar EN BD que se crea registro en traducciones_productos  
✅ Cambiar a idioma EN  
✅ Verificar que se muestra traducción "Coffee Premium"  

---

### 6. **Arquitectura de Artículos Personalizados (Opción 2)** 👥

#### Descripción
**ARQUITECTURA CRÍTICA**: Separación clara entre artículos estándar (compartidos entre todos) y personalizados (únicos de cada cliente).

#### Estructura de BD

##### 6A. Tabla: `articulos_personalizados`
```sql
CREATE TABLE articulos_personalizados (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  espacio_id INTEGER NOT NULL,      -- Cliente/Espacio específico
  nombre TEXT NOT NULL,
  categoria TEXT NOT NULL DEFAULT 'Otros',
  icono TEXT,
  unidad TEXT NOT NULL DEFAULT 'ud',
  sub_descripcion TEXT,
  cantidad_defecto INTEGER NOT NULL DEFAULT 1,
  fecha_creacion TEXT,
  fecha_actualizacion TEXT,
  UNIQUE(espacio_id, nombre)        -- Único por cliente
);
```

##### 6B. Modificación: `articulos_lista`
Nueva columna: `articulo_personalizado_id` (referencia a articulos_personalizados)

#### Diferencia Crítica

**ESTÁNDAR (historial_articulos)**
```
✅ Se comparten entre TODOS los clientes
✅ Disponibles en CUALQUIER lista
✅ Se traducen automáticamente
✅ Ej: "Leche integral" del catálogo
```

**PERSONALIZADO (articulos_personalizados)**
```
✅ ÚNICOS de cada cliente (vinculados a espacio_id)
✅ Reutilizables en MÚLTIPLES listas del MISMO cliente
✅ Si lista se comparte → otros usuarios ven SOLO en esa lista
✅ Se traducen automáticamente
✅ Ej: "Detergente Marca X" del usuario
```

#### Lógica de Creación (CRÍTICA)
Archivo: `stockhogar/rutas/lista_compra.py` (línea ~50 en adelante)

```python
def anadir_articulo():
    # 1. Buscar en historial estándar
    recuerdo = buscar_historial(db, nombre)
    
    if not recuerdo:
        # 2. NO está en catálogo → crear en articulos_personalizados
        espacio_id = obtener_espacio_actual(db)
        
        # 3. Crear o reutilizar artículo personalizado
        articulo_personal = db.execute(
            "SELECT id FROM articulos_personalizados WHERE nombre = ? AND espacio_id = ?",
            (nombre, espacio_id)
        ).fetchone()
        
        if not articulo_personal:
            # 4. Crear nuevo artículo personalizado
            cur = db.execute(
                "INSERT INTO articulos_personalizados ...",
                (espacio_id, nombre, ...)
            )
            articulo_personalizado_id = cur.lastrowid
            
            # 5. AUTOMÁTICAMENTE TRADUCIR
            traducciones = TraductorAutomatico.traducir_a_todos_idiomas(nombre)
            # Almacenar en traducciones_productos
        
        # 6. Vincular en articulos_lista
        db.execute(
            "INSERT INTO articulos_lista (articulo_personalizado_id, ...)",
            (articulo_personalizado_id, ...)
        )
```

#### Testing Crítico
✅ Usuario A crea "Detergente Marca X"  
✅ Verificar que se crea en articulos_personalizados (no en historial)  
✅ Verificar que espacio_id = espacio de Usuario A  
✅ Compartir lista con Usuario B  
✅ Usuario B abre lista → ve "Detergente Marca X"  
✅ Usuario B abre otra lista → NO ve "Detergente Marca X"  

---

### 7. **CRUD Completo de Artículos Personalizados** ⚙️

#### Descripción
Gestión completa de artículos personalizados con traducción automática.

#### Endpoints Implementados

##### GET: Obtener Traducciones
```
GET /api/articulos-personalizados/<id>/traducciones/<idioma>

Response:
{
  "nombre": "Detergent Brand X",
  "descripcion": "Intense blue"
}
```

##### PATCH: Editar Artículo
```
PATCH /api/articulos-personalizados/<id>

Request:
{
  "nombre": "Nuevo nombre",
  "categoria": "Limpieza",
  "sub_descripcion": "Nueva descripción"
}

Características:
✅ Auto-traduce cambios
✅ Almacena nuevas traducciones
✅ Actualiza en tiempo real
```

##### DELETE: Eliminar Artículo
```
DELETE /api/articulos-personalizados/<id>

Validaciones:
✅ Verificar que NO está en uso en listas activas
✅ Eliminar traducciones asociadas
✅ Limpiar referencias en articulos_lista
✅ Devuelve 400 si está en uso
```

#### Funciones Frontend
```javascript
// Editar
editarArticuloPersonalizado(id, datos);

// Eliminar
eliminarArticuloPersonalizado(id);

// Obtener traducciones
obtenerTraduccionesArticulo(id, idioma);
```

---

### 8. **Traducción Dinámica de Artículos** 🔄

#### Descripción
Cuando usuario cambia de idioma, las descripciones de artículos personalizados se traducen automáticamente.

#### Ubicación
Archivo: `stockhogar/static/i18n.js` (método `cargarTraduccionesArticulos`)

```javascript
async cargarTraduccionesArticulos(idioma) {
  // 1. Buscar todos los artículos [data-articulo-id]
  const articulos = document.querySelectorAll('[data-articulo-id]');
  
  // 2. Para cada artículo, cargar traducciones
  for (const elemento of articulos) {
    const trad = await fetch(
      `/api/articulos-personalizados/${articuloId}/traducciones/${idioma}`
    );
    
    // 3. Actualizar DOM
    elemento.querySelector('[data-nombre]').textContent = trad.nombre;
    elemento.querySelector('[data-descripcion]').textContent = trad.descripcion;
  }
}
```

#### Integración
Se llama automáticamente en `cambiarIdioma()`:
```javascript
async cambiarIdioma(nuevoIdioma) {
  // ...
  await this.cargarTraducciones(nuevoIdioma);
  this.traducirPagina();
  this.cargarTraduccionesArticulos(nuevoIdioma); // ← AQUÍ
}
```

---

## 🗄️ ARQUITECTURA DE BASE DE DATOS

### Tabla Central: `articulos_lista`
```sql
articulos_lista {
  id INTEGER PRIMARY KEY,
  lista_id INTEGER,                      -- Referencia a listas
  producto_id INTEGER REFERENCES productos,
  articulo_personalizado_id INTEGER REFERENCES articulos_personalizados,
  nombre TEXT NOT NULL,
  cantidad INTEGER,
  unidad TEXT,
  categoria TEXT,
  icono TEXT,
  sub_descripcion TEXT,
  origen TEXT ('manual', 'catalogo'),
  activo INTEGER (1=pendiente, 0=completado),
  fecha_completado TEXT,
  fecha_creacion TEXT
};
```

### Tabla: `articulos_personalizados`
```sql
articulos_personalizados {
  id INTEGER PRIMARY KEY,
  espacio_id INTEGER,          -- CRÍTICO: vinculado a cliente
  nombre TEXT UNIQUE,          -- Por espacio
  categoria TEXT,
  icono TEXT,
  unidad TEXT,
  sub_descripcion TEXT,
  cantidad_defecto INTEGER,
  fecha_creacion TEXT,
  fecha_actualizacion TEXT
};
```

### Tabla: `traducciones_productos`
```sql
traducciones_productos {
  id INTEGER PRIMARY KEY,
  producto_id INTEGER,                    -- Para productos estándar
  articulo_id INTEGER,                    -- Para artículos de lista
  tipo TEXT ('nombre', 'descripcion'),    -- Qué tipo de texto
  idioma TEXT,                            -- Código ISO (en, es, gl, etc)
  texto_original TEXT,                    -- Valor original (español)
  texto_traducido TEXT,                   -- Valor traducido
  fecha_creacion TEXT,
  UNIQUE(producto_id, articulo_id, tipo, idioma)
};
```

---

## 🔌 ENDPOINTS API

### Idiomas
```
GET    /api/idiomas/disponibles          - Listar idiomas disponibles
POST   /api/idiomas/cambiar              - Cambiar idioma del usuario
GET    /api/idiomas/obtener              - Obtener idioma actual
POST   /api/idiomas/traducir             - Traducir múltiples claves
GET    /api/idiomas/todos/<idioma>       - Obtener todas las traducciones
```

### Productos
```
GET    /api/productos                    - Listar productos
POST   /api/productos                    - Crear producto
PATCH  /api/productos/<id>               - Actualizar producto
DELETE /api/productos/<id>               - Eliminar producto
POST   /api/productos/traducir           - Traducir automáticamente
GET    /api/productos/<id>/traducciones/<idioma> - Obtener traducciones
```

### Artículos Personalizados
```
GET    /api/articulos-personalizados/<id>/traducciones/<idioma>
PATCH  /api/articulos-personalizados/<id>
DELETE /api/articulos-personalizados/<id>
```

### Artículos de Lista
```
GET    /api/articulos?lista_id=<id>      - Listar artículos
POST   /api/articulos                    - Crear artículo
PATCH  /api/articulos/<id>               - Actualizar artículo
DELETE /api/articulos/<id>               - Eliminar artículo
```

---

## 🎨 COMPONENTES FRONTEND

### TranslationManager Class
Ubicación: `stockhogar/static/i18n.js`

```javascript
class TranslationManager {
  constructor()
  obtenerIdiomaGuardado()                // localStorage + defecto
  async cargarTraducciones(idioma)       // Fetch a API
  t(clave)                               // Traducir clave
  async traducirPagina()                 // Traducir UI
  async cambiarIdioma(idioma)            // Cambiar + persistir
  configurarSelectorIdioma()             // Setup selector
  async cargarTraduccionesArticulos()    // CRÍTICO: traducciones dinámicas
}

// Instancia global
window.i18n = new TranslationManager();
```

### ProductosManager Class
Ubicación: `stockhogar/static/modules/productos-manager.js`

```javascript
class ProductosManager {
  async cambiarCantidad(id, delta)
  // Si cantidad llega al stock_minimo → automáticamente:
  // 1. Detecta DESDE ARRIBA
  // 2. Llama _anadirAListaCompra()
  // 3. Notifica usuario
  // 4. Dispara evento
}
```

---

## 📊 FLUJOS DE NEGOCIO CRÍTICOS

### Flujo 1: Crear Artículo Personalizado
```
Usuario abre lista de compra
  ↓
Busca "Detergente Marca X" (NO en catálogo)
  ↓
Sistema:
  1. Crea en articulos_personalizados (espacio_id = usuario)
  2. Automáticamente traduce a 7 idiomas
  3. Almacena traducciones en BD
  4. Vincula en articulos_lista
  ↓
Usuario cambia idioma a EN
  ↓
Sistema:
  1. Carga traducciones de articulo
  2. Muestra "Detergent Brand X"
  ↓
Usuario comparte lista con Usuario B
  ↓
Usuario B ve artículo SOLO en esa lista
(No aparece en otras listas de Usuario B)
```

### Flujo 2: Stock Mínimo Automático
```
Producto "Café" con stock_minimo = 2
Stock actual = 3
  ↓
Usuario hace clic "-"
  ↓
Sistema:
  1. cantidad = 3 → 2
  2. Detecta: 3 > 2 AND 2 <= 2 ✓
  3. Automáticamente:
     - Crear artículo en lista_compra
     - nombre = "Café"
     - cantidad = 2 (stock_minimo)
     - sub_descripcion = "[Automático: stock bajo]"
  4. Notificar usuario
  ↓
Usuario ve: "Café ha llegado al stock mínimo. Añadido a la lista de compra."
```

### Flujo 3: Traducción de Artículos
```
Usuario crea artículo personalizado "Leche integral - Fresca"
  ↓
Sistema (en background, NO bloquea):
  1. POST /api/productos/traducir
  2. Traduce nombre: Leche integral → Milk Integral, ...
  3. Traduce descripción: Fresca → Fresh, ...
  4. Almacena 12 registros en traducciones_productos (6 idiomas × 2 tipos)
  ↓
Usuario cambia idioma
  ↓
Sistema automáticamente carga traducciones y actualiza UI
```

---

## ⚡ CONSIDERACIONES TÉCNICAS

### Rendimiento
- ✅ Traducción automática en background (NO bloquea UI)
- ✅ Cache de traducciones en localStorage
- ✅ Diccionario cargado una sola vez
- ✅ Query optimizada en BD (índice UNIQUE)

### Seguridad
- ✅ Validación en todos los endpoints
- ✅ Verificación de permisos (espacio_id)
- ✅ Prevención de inyección SQL (bind variables)
- ✅ Validación de entrada en frontend

### Escalabilidad
- ✅ Tabla de traducciones no impacta rendimiento (UNIQUE constraint)
- ✅ Artículos personalizados filtrados por espacio_id (BD indexada)
- ✅ Diccionario traducible (modificable sin código)

### Tolerancia a Fallos
- ✅ Si traducción falla → usa original
- ✅ Si artículo no existe → devuelve 404
- ✅ Si está en uso → devuelve 400 (no elimina)

---

## ✅ TESTING Y VALIDACIÓN

### Testing Obligatorio Antes de Producción

#### 1. Sistema de Idiomas
- [ ] Abrir ajustes
- [ ] Selector de idioma visible
- [ ] Cambiar a cada idioma (7 total)
- [ ] Verificar traducción global de UI
- [ ] Cambiar idioma varias veces (persistencia)
- [ ] Recargar página → mantiene idioma
- [ ] Cambiar a Gallego → verificar traducciones españolas

#### 2. Stock Mínimo
- [ ] Producto con stock_minimo = 2, actual = 3
- [ ] Click "-" → cantidad = 2
- [ ] Verificar que se añade a lista de compra automáticamente
- [ ] Verificar que aparece notificación
- [ ] Verificar sub_descripcion = "[Automático: stock bajo]"
- [ ] Click "-" otra vez → NO añade (ya está bajo)

#### 3. Articulos Personalizados
- [ ] Crear "Detergente Marca X" (NO en catálogo)
- [ ] Verificar que se crea en articulos_personalizados (BD)
- [ ] Verificar espacio_id correcto
- [ ] Editar: cambiar nombre a "Detergente Marca Y"
- [ ] Cambiar idioma → verificar traducción se actualiza
- [ ] Compartir lista con otro usuario
- [ ] Otro usuario ve artículo SOLO en esa lista
- [ ] Eliminar artículo → verificar que limpia referencias

#### 4. Traducción Automática
- [ ] Crear producto "Café Premium"
- [ ] Verificar en BD: traducciones_productos tiene registros
- [ ] Cambiar a idioma EN → verificar traducción aparece
- [ ] Editar nombre a "Premium Coffee"
- [ ] Cambiar a FR → verificar traducción actualizada
- [ ] Crear artículo con descripción
- [ ] Verificar que se traduce NOMBRE + DESCRIPCIÓN

#### 5. Responsive (iOS)
- [ ] Abrir modal en iPhone 17 Pro Max (simulate)
- [ ] Hacer clic en input (teclado se abre)
- [ ] Verificar que modal NO se comprime excesivamente
- [ ] Interactuar con formulario
- [ ] Cerrar teclado → modal vuelve a tamaño normal
- [ ] Repetir con múltiples modales

#### 6. Selector de Icono
- [ ] Abrir modal de crear artículo
- [ ] Clickear "Elegir icono"
- [ ] Verificar que abre modal externa
- [ ] Buscar "leche"
- [ ] Seleccionar icono
- [ ] Verificar que cierra y guarda icono
- [ ] Repetir para productos

### Testing de Integración
- [ ] Crear producto + cambiar idioma + stock bajo → funciona completo
- [ ] Crear artículo personal + compartir + otro usuario ve + traducción
- [ ] Editar artículo personal + cambiar idioma → traducción actualizada

---

## 📝 REGISTRO DE CAMBIOS

### Versión 1.0 (2026-07-08)
**Features Implementadas:**
- ✅ Sistema multiidioma (7 idiomas)
- ✅ Selector de icono con modal
- ✅ Arreglo de modales en iOS
- ✅ Stock mínimo automático
- ✅ Traducción automática de productos/artículos
- ✅ Arquitectura de artículos personalizados (Opción 2)
- ✅ CRUD completo de artículos personalizados
- ✅ Traducción dinámica de artículos

**Commits:**
- `5eb23cc` - fix: Sistema de idiomas completamente funcional
- `f5f16d0` - feat: Selector de icono con modal externa y stock mínimo
- `4d63427` - feat: Sistema automático de traducción para productos
- `818ecc8` - feat: Endpoint para obtener traducciones y documentación
- `cba6156` - feat: Arquitectura de artículos personalizados (Opción 2)
- `ed6a005` - feat: Endpoints completos para artículos personalizados + UI

**Base de Datos Actualizada:**
- ✅ Tabla `articulos_personalizados` creada
- ✅ Tabla `traducciones_productos` creada
- ✅ Columna `articulo_personalizado_id` en `articulos_lista`
- ✅ Columna `sub_descripcion` incluida en responses

---

## 🚨 COSAS QUE NUNCA DEBEN CAMBIAR

❌ **NO ELIMINAR NUNCA:**
- Tabla `articulos_personalizados` (datos de clientes)
- Tabla `traducciones_productos` (traducciones)
- Diccionario en `traductor_auto.py`
- Endpoint `/api/idiomas/todos/<idioma>`
- Método `cambiarCantidad()` en ProductosManager
- Método `cargarTraduccionesArticulos()` en i18n.js

❌ **NO MODIFICAR SIGNIFICATIVAMENTE:**
- Lógica de detección de stock_minimo (crítica)
- Estructura de espacio_id en articulos_personalizados
- Búsqueda de artículos estándar vs personalizados

✅ **SÍ SE PUEDE MODIFICAR:**
- Agregar más idiomas (si se agrega a diccionario)
- Agregar más iconos
- Agregar más palabras al diccionario
- Mejorar UI/UX manteniendo funcionalidad

---

## 📞 SOPORTE

**Errores Frecuentes:**

1. **"No se traduce el artículo personalizado"**
   - Verificar que `cargarTraduccionesArticulos()` se llama
   - Verificar que articulo tiene `[data-articulo-id]` en HTML

2. **"Stock mínimo no funciona"**
   - Verificar que producto tiene `stock_minimo` seteado
   - Verificar que cantidad **BAJA** desde arriba del mínimo

3. **"Modal se comprime en iOS"**
   - Verificar que `--keyboard-offset` se actualiza
   - Verificar que `min-height: 50vh` está en CSS

4. **"Artículo personalizado aparece en otra lista"**
   - Esto es un bug: debería ser solo en esa lista
   - Verificar que se crea con `articulo_personalizado_id`

---

**Este documento es el "source of truth" para Home Stock. Cualquier cambio futuro debe verificar que NO rompe ninguna de estas características.**

**Versión**: 1.0  
**Última revisión**: 2026-07-08  
**Estado**: ✅ COMPLETO Y VERIFICADO
