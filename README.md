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

### Panel de gestión del servidor

El panel (rendimiento, mantenimiento, reinicio, logs en vivo, backups,
configuración y usuarios) es un **proyecto independiente**, fuera de este
repositorio: [StockHogar-Panel](../StockHogar-Panel). Se instala y se
ejecuta por separado (proceso y puerto propios), y solo necesita saber dónde
está esta instalación de StockHogar para leer/escribir sus mismos ficheros
(`.env`, base de datos, logs, backups). Consulta su propio README para
instalarlo.

## 📚 Documentación

| Para | Documento |
|------|-----------|
| **Primeros pasos** | [`docs/00-INICIO.md`](docs/00-INICIO.md) |
| **Instalación** | [`docs/INSTALACION.md`](docs/INSTALACION.md) |
| **Desarrollo** | [`docs/DESARROLLO.md`](docs/DESARROLLO.md) |
| **Arquitectura** | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |
| **API** | [`docs/API.md`](docs/API.md) |
| **Problemas** | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |

## ✨ Características

✅ **Inventario inteligente** - Stock con avisos de mínimos y caducidad  
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
| Testing | pytest (backend), Jest (frontend) |

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

### ⚠️ Fase 3: Frontend OOP (parcial - documentación desactualizada)
- ✅ Singletons globales `window.DOM`, `window.API` con métodos centralizados (`static/core/`)
- ✅ Algunos módulos extraídos como managers independientes (`static/modules/drawer-listas.js`, `form-builder.js`, `ui-components.js`)
- ❌ `app.js` sigue siendo un orquestador monolítico (~2200 líneas, no las 300 líneas históricamente reportadas aquí); el resto de managers listados en versiones anteriores de este README (ProductosManager, CompraManager, CategoriasManager, EspaciosManager, TicketsManager) no existen como ficheros separados
- ✅ Tests con Jest para los módulos ya extraídos

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
| **Fase 3** | Frontend (JavaScript) | ⚠️ Parcial | Singletons `DOM`/`API` + 3 módulos extraídos (`drawer-listas.js`, `form-builder.js`, `ui-components.js`); `app.js` sigue siendo un orquestador monolítico (~2200 líneas) |
| **Fase 4** | Tests Backend | ⏳ Pendiente | pytest coverage (bonus) |

Ver detalle de por qué la Fase 3 está marcada como parcial en la sección "Fase 3: Frontend OOP" más arriba.

---

## 📝 Licencia

MIT - Libre para uso personal y comercial

---

**¿Primer viaje?** → Lee [`docs/00-INICIO.md`](docs/00-INICIO.md)  
**¿Vas a desarrollar?** → Lee [`docs/DESARROLLO.md`](docs/DESARROLLO.md)  
**¿Quieres entender la arquitectura?** → Lee [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

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

### Manual

```bash
cd ~/Home-Stock
git pull
docker compose up -d --build
```

Esto descarga los cambios, reconstruye la imagen con el código nuevo y
reinicia el contenedor. Los datos en `data/stock.db` no se ven afectados.

### Automática (Raspberry Pi)

`install.sh` deja instalado automáticamente (si la rama activa es
`produccion` y hay `crontab` disponible) el cron de
`scripts/auto_update.sh`, que cada 5 minutos comprueba si hay commits
nuevos en `origin/produccion`:

- Si no hay cambios, no hace nada.
- Si los hay, ejecuta `install.sh --update` (`git pull --ff-only` +
  reconstrucción del contenedor Docker), igual que el proceso manual.
- Se salta la comprobación si hay cambios locales sin commitear o si ya
  hay una instalación en curso (usa un lock, `.install.lock`).
- Se puede pausar temporalmente creando el flag
  `data/auto_actualizacion_pausada.flag` (gestionable desde el endpoint
  `/api/auto-actualizacion` o desde el Panel de Gestión).
- El log queda en `logs/auto_update.log`.

**Refresco del frontend:** la app no usa Service Worker. El frontend
consulta cada 15 s el endpoint `/api/cache-version` (que cambia con cada
`git pull`, al variar el `mtime` de `docker-compose.yml`). En cuanto
detecta una versión distinta, limpia cualquier caché/Service Worker
residual y fuerza un `location.reload()`, de modo que tras una
actualización automática los clientes abiertos recargan solos y ven el
código nuevo sin intervención manual.
