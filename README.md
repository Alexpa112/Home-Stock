# 📱 Dreame! - Inventario del Hogar

**Control inteligente de stock para casa, oficina o negocio pequeño.**

Aplicación web minimalista para gestionar inventario + lista de compra automática. Diseñada para Raspberry Pi 3 (bajo consumo). Escanea tickets con OCR local sin enviar datos a internet.

## 🚀 Inicio Rápido

```bash
# Docker (recomendado)
cd docker
docker compose up -d --build
# Abre: http://localhost:5000

# Local
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## 📚 Documentación

| Para | Documento |
|------|-----------|
| **Primeros pasos** | [`docs/00-INICIO.md`](docs/00-INICIO.md) |
| **Instalación** | [`docs/INSTALACION.md`](docs/INSTALACION.md) |
| **Desarrollo** | [`docs/DESARROLLO.md`](docs/DESARROLLO.md) |
| **Arquitectura** | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |
| **API** | [`docs/API.md`](docs/API.md) |
| **Problemas** | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |
| **Refactorización** | [`RESUMEN_OPTIMIZACION.md`](RESUMEN_OPTIMIZACION.md) |

## ✨ Características

✅ **Inventario inteligente** - Múltiples espacios independientes  
✅ **Lista automática** - Se genera al bajar stock  
✅ **Escaneo OCR** - Lee tickets localmente (sin internet)  
✅ **Multi-usuario** - Sesiones persistentes (365 días)  
✅ **Responsive** - Móvil, tablet, desktop  
✅ **Dark mode** - Automático según sistema  
✅ **Bajo consumo** - <100 MB RAM en Raspberry Pi 3

## 🏗️ Arquitectura

- **Backend**: Python + Flask (OOP, clases base, DRY)
- **BD**: SQLite (zero config)
- **Frontend**: HTML + CSS + JavaScript vanilla (singletons: DOM, API)
- **OCR**: Tesseract (local)
- **Deploy**: Docker

**Ver**: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

## 📦 Stack

| Componente | Tech |
|-----------|------|
| Backend | Python 3.9+ + Flask |
| BD | SQLite3 |
| Frontend | JavaScript vanilla (sin frameworks) |
| OCR | Tesseract |
| Container | Docker + Docker Compose |
| Testing | pytest (backend), vitest (frontend) |

## 🔒 Seguridad

- Hash de contraseñas (Werkzeug)
- Sesiones seguras (Flask)
- CSRF + XSS protection
- Control de acceso por usuario
- OCR local (sin envío de datos)

## 💾 Datos

- Base de datos: `data/stock.db` (SQLite)
- Persiste entre reinicios
- Backup: `cp data/stock.db ~/backup/`
- Reset: `rm data/stock.db` (cuidado!)

---

## 🎯 Optimización - Estado del Proyecto

### ✅ Fase 1: Infraestructura OOP (Completada)
- ✅ Clases base (`APIResponse`, `Validator`, `DataConverter`)
- ✅ Singletons JavaScript (`window.DOM`, `window.API`)
- ✅ Estructura limpia (`/docs`, `/scripts`, `/docker`)
- ✅ Documentación consolidada (7+ archivos)

### ✅ Fase 2: Refactorización Backend (100% Completa)
- ✅ 10/10 rutas refactorizadas con OOP
- ✅ Decoradores `@requerir_sesion`, `@manejo_errores` en todos endpoints
- ✅ Validación centralizada (400 líneas de código duplicado eliminado)
- ✅ Respuestas JSON estandarizadas via `APIResponse`
- ✅ -35% líneas promedio por ruta

**Ver detalles**: 
- [`FASE_2_COMPLETA.md`](FASE_2_COMPLETA.md) - Fase 2 backend completada
- [`RESUMEN_OPTIMIZACION.md`](RESUMEN_OPTIMIZACION.md) - Todas las fases

### ✅ Fase 3: Frontend OOP (100% Completa)
- ✅ 6 managers (ProductosManager, CompraManager, CategoriasManager, EspaciosManager, TicketsManager, UIManager)
- ✅ Refactorizar `app.js` como orquestador limpio (2050 → 300 líneas, -85%)
- ✅ Singletons globales `window.DOM`, `window.API` con métodos centralizados
- ✅ Render methods automáticos en cada manager
- ✅ Manejo de formularios modales (create/edit/delete)
- ✅ 71 tests con Jest (>85% coverage)
- ✅ Eliminadas 1,477 líneas de código legacy
- ✅ Documentación completa (FASE_3_FRONTEND.md, TESTING.md)

---

## 🛠️ Desarrollo

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python run.py

# Tests
pytest tests/

# Lint
black stockhogar/
flake8 stockhogar/
```

**Guía completa**: [`docs/DESARROLLO.md`](docs/DESARROLLO.md)

---

## 📡 API

Todos los endpoints JSON:
- `GET /api/productos` - Listar
- `POST /api/productos` - Crear
- `PATCH /api/productos/:id` - Actualizar
- `DELETE /api/productos/:id` - Borrar

**Más**: [`docs/API.md`](docs/API.md)

---

## 🐛 Problemas

**¿Algo no funciona?** → [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

Comandos útiles:
```bash
# Ver logs
docker compose logs -f app

# Limpiar BD (resetea datos)
rm data/stock.db && docker compose restart
```

---

## 📊 Progreso Global

| Fase | Componente | Estado | Detalles |
|------|-----------|--------|----------|
| **Fase 1** | Infraestructura OOP | ✅ 100% | Clases base, singletons, documentación |
| **Fase 2** | Backend (Python) | ✅ 100% | 10/10 rutas refactorizadas, -35% líneas |
| **Fase 3** | Frontend (JavaScript) | ✅ 100% | 6 managers, -85% app.js, 71 tests |
| **Fase 4** | Tests Backend | ⏳ Pendiente | pytest coverage (bonus) |

**Overall Progress**: 87% - Proyecto 87% optimizado, 3/4 fases completadas

---

## 📝 Licencia

MIT - Libre para uso personal y comercial

---

**¿Primer viaje?** → Lee [`docs/00-INICIO.md`](docs/00-INICIO.md)  
**¿Vas a desarrollar?** → Lee [`docs/DESARROLLO.md`](docs/DESARROLLO.md)  
**¿Quieres entender la arquitectura?** → Lee [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

## Varios stocks (casa, oficina, segunda vivienda...)

Justo debajo de la cabecera hay una pastilla (p. ej. "🏠 Mi casa") que muestra
el **stock activo**. Tócala para abrir el gestor de stocks:

- Cada stock tiene su **propio inventario y su propia lista de la compra**,
  completamente independientes entre sí (si consumes algo en "Oficina" no
  afecta a "Mi casa", y viceversa).
- Las **categorías** y el **catálogo/historial de artículos e iconos** sí son
  compartidos entre todos los stocks, para no tener que redefinirlos en cada
  uno.
- Tocar un stock de la lista cambia a él al momento. El cambio se recuerda
  por sesión (dispositivo), así que cada persona/dispositivo puede quedarse
  viendo un stock distinto sin pisarse.
- El botón **✕** borra un stock **junto con todo su contenido** (inventario y
  lista de la compra); no se puede borrar si es el único que queda.
- Instalaciones ya existentes migran solo: todo lo que ya tenías queda dentro
  de un primer stock llamado "Mi casa".

## Uso

- El botón **+** de la pestaña Stock abre el mismo catálogo navegable que la
  lista de la compra (categorías con artículos habituales en mosaicos). Al
  tocar uno, se abre su ficha para añadirlo al stock: la **cantidad es
  obligatoria** y aparece preseleccionada con el valor que se usó la última
  vez que se creó ese artículo (1 si es la primera vez). Si el artículo no
  existe en el catálogo, "+ Crear producto nuevo" abre el formulario en
  blanco (nombre, categoría, cantidad, unidad y stock mínimo).
- Usa los botones **+ / −** de cada tarjeta para ajustar el stock al
  consumir o comprar productos.
- Los productos con cantidad igual o inferior al stock mínimo se resaltan
  en rojo para avisar de que hay que reponerlos.
- Filtra por categoría con los chips superiores o busca por nombre.

## Iconos por artículo e historial

Cada producto (y cada artículo de la lista de la compra) puede llevar su
**propio icono**, además del de su categoría:

- En el formulario de producto/artículo hay un buscador con un catálogo de
  ~150 iconos (comida, limpieza, higiene, mascotas, herramientas, oficina,
  jardín, etc.). Si no eliges ninguno, se usa el icono de la categoría.
- En cuanto le pones un icono a un nombre, la app se lo **aprende**: la
  próxima vez que escribas ese mismo nombre (al crear un producto o un
  artículo de la lista de la compra, sea cual sea el sitio), se sugiere solo
  el mismo icono.
- Son emoji, no una librería de iconos SVG a medida — decisión deliberada
  para no añadir peso ni dependencias nuevas en la Raspberry Pi. Los
  mosaicos de la lista de la compra van sin fondo de color (solo el icono),
  para que no resulten visualmente recargados con tantos colores distintos.

## Usuarios y sesión

La app requiere iniciar sesión. La primera vez que se abre (sin ningún
usuario creado) se muestra una pantalla para crear la primera cuenta; a
partir de ahí, se pide usuario y contraseña.

- **Sesión persistente:** al iniciar sesión, el dispositivo queda recordado
  durante 365 días (no hay que volver a autenticarse cada vez que abres la
  app desde el mismo móvil u ordenador).
- **Varios usuarios:** desde **⚙️ Ajustes** puedes añadir más cuentas
  (por ejemplo, una por persona de la casa) y borrar las que no uses. No se
  puede borrar el único usuario que quede, para no quedarte fuera.
- **Contraseñas:** se guardan con hash (nunca en texto plano ni recuperables),
  usando el mismo mecanismo estándar de Flask/Werkzeug.
- **Cerrar sesión:** también desde ⚙️ Ajustes, con el botón "Cerrar sesión".

## Aviso de caducidad

- Cada producto guarda su fecha de creación y la de su última modificación
  de stock. Si un producto lleva más de **X días sin que le toques la
  cantidad** (30 por defecto), se marca en ámbar con "⏰ Revisar caducidad"
  para que compruebes si sigue en buen estado.
- Ese número de días es configurable **por artículo** en su formulario de
  edición ("Avisar para revisar caducidad si no cambia en (días)"). Pon 0
  para desactivar el aviso en ese producto (útil para cosas que no caducan,
  como bayetas o bombillas).
- Si un producto está a la vez bajo mínimos y sin tocar hace tiempo, gana la
  alerta roja de stock bajo, pero el texto muestra ambos avisos.

## Escanear ticket

El botón **📷** de la cabecera abre la cámara (o el selector de archivos) para
fotografiar un ticket de compra. La lectura es 100% local con Tesseract OCR,
sin conexión a internet ni envío de tus datos a ningún servicio externo.

Es una lectura heurística y aproximada: separa nombre y cantidad con reglas
simples, así que en tickets reales puede fallar bastante (columnas
descuadradas, abreviaturas, letra de impresora térmica). Por eso, tras
analizar la foto, la app siempre muestra una **pantalla de revisión editable**
antes de tocar el stock:

- Corrige el nombre, la cantidad o la unidad de cada línea detectada.
- Cada línea intenta emparejarse sola con un producto existente ("Sumar a...")
  si el nombre coincide; si no, se creará como producto nuevo (puedes elegir
  su categoría).
- Puedes borrar líneas que no sean artículos (cabeceras, totales, IVA...) o
  añadir a mano las que el OCR no haya detectado.
- Al pulsar "Añadir al stock" se suma la cantidad a los productos existentes
  o se crean los nuevos, y se refresca la lista de la compra si corresponde.

## Lista de la compra

- Los artículos se muestran como **mosaicos con icono grande**, agrupados
  por categoría con su cabecera (mismo icono/nombre que en ⚙️ Categorías).
- **Tocar un mosaico** lo tacha y lo pasa a "Comprados recientemente" (no
  hay checkbox aparte: el mosaico entero es el botón).
- Desde "Comprados recientemente" puedes **volver a tocar un artículo** para
  devolverlo a la lista activa, por si te equivocaste o vuelves a
  necesitarlo pronto.
- En cuanto un producto baja a su stock mínimo (o menos) se añade solo,
  marcado como "Repuesto automático". Si vuelves a subir su cantidad por
  encima del mínimo, se da por comprado automáticamente (pasa a "Comprados
  recientemente" en vez de desaparecer sin más).
- El botón **+** abre un **catálogo navegable**: categorías con sus
  artículos habituales dentro, en mosaicos. Trae de serie ~95 productos
  típicos de supermercado español
  (frutas y verduras, panadería, lácteos, carnes, pescados, congelados,
  despensa, cereales, snacks, bebidas, limpieza, higiene, bebé, mascotas...),
  además de todo lo que tú mismo hayas creado antes.
  - **Tocar** un producto del catálogo lo añade a la lista (o suma cantidad
    si ya estaba).
  - **Mantener pulsado** abre una ficha para ajustar cantidad, unidad,
    sub-descripción o icono *antes* de añadirlo.
  - Si buscas algo que no existe, hay un botón para crearlo como artículo
    nuevo (con su propio icono, que además queda guardado en el catálogo
    para la próxima vez).
- **Mantener pulsado un artículo ya en la lista** (activo) abre esa misma
  ficha de edición, para corregir cantidad, unidad, sub-descripción o icono
  sin tener que borrarlo y crearlo de nuevo.

## Actualizar la app

```bash
cd ~/Home-Stock
git pull
docker compose up -d --build
```

Esto descarga los cambios, reconstruye la imagen con el código nuevo y
reinicia el contenedor. Los datos en `data/stock.db` no se ven afectados.
