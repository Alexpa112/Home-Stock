# Dreame!

Control de stock de artículos de casa con gestión de la lista de la compra
automática.

Aplicación web minimalista para llevar el inventario de productos del hogar
(comida, limpieza, higiene, etc.). Pensada para pesar muy poco y poder
ejecutarse de forma permanente en una Raspberry Pi 3.

## Stack

- **Backend:** Python + Flask (un único proceso, sin dependencias pesadas).
- **Base de datos:** SQLite (un fichero `stock.db`, cero configuración).
- **Frontend:** HTML + CSS + JavaScript vanilla (sin frameworks, sin build).
- **Despliegue:** contenedor Docker (imagen `python:3.11-slim` + Tesseract),
  orquestado con Docker Compose.

Todo el consumo de RAM/CPU es mínimo (unos pocos MB), apto de sobra para una
Raspberry Pi 3.

## Estructura del proyecto

```
StockHogar/
├── run.py                     # Punto de entrada: arranca el servidor
├── requirements.txt
├── Dockerfile                  # Imagen de la aplicación
├── docker-compose.yml          # Orquestación (puerto, volumen de datos, reinicio)
├── .dockerignore
├── data/
│   └── stock.db                # Base de datos SQLite (no versionar; persiste vía volumen)
└── stockhogar/                  # Paquete de la aplicación
    ├── __init__.py               # Fabrica de la app (create_app), blueprints y guardián de sesión
    ├── config.py                 # Constantes: categorías, rutas, valores por defecto
    ├── db.py                     # Conexión SQLite, migraciones del esquema
    ├── seguridad.py               # Clave de sesión local
    ├── integraciones/
    │   └── ticket_ocr.py          # Lectura OCR local de tickets
    ├── rutas/                     # Un blueprint por dominio (así se añade uno nuevo sin tocar los demás)
    │   ├── paginas.py              # "/" (la SPA)
    │   ├── auth.py                 # Login, logout y gestión de usuarios
    │   ├── productos.py            # /api/productos (+ lógica de stock compartida)
    │   ├── categorias.py           # /api/categorias
    │   ├── espacios.py             # /api/espacios (varios stocks independientes)
    │   ├── historial.py            # /api/historial (catálogo de artículos e iconos)
    │   ├── lista_compra.py         # /api/lista-compra
    │   └── tickets.py              # /api/tickets/*
    ├── static/                    # CSS/JS servidos tal cual
    └── templates/                 # HTML (Jinja2): index.html y login.html
```

Para añadir una funcionalidad nueva: crea un fichero en `stockhogar/rutas/`
con su propio `Blueprint`, y regístralo en `stockhogar/__init__.py`. Si
necesita hablar con un servicio externo, el cliente va en
`stockhogar/integraciones/`.

## Instalación en la Raspberry Pi (Docker)

La aplicación se despliega como contenedor Docker. Tesseract, Python y todas
las dependencias van dentro de la imagen — en la Raspberry solo hace falta
tener Docker instalado.

```bash
# 1. Instalar Docker (incluye el plugin de Docker Compose)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo reboot
```

Tras reiniciar y volver a conectar por SSH:

```bash
# 2. Descargar el proyecto
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock

# 3. Construir la imagen y arrancar el contenedor en segundo plano
docker compose up -d --build
```

La aplicación quedará escuchando en el puerto 5000 y accesible desde
cualquier dispositivo de la red local en:

```
http://<ip-de-la-raspberry>:5000
```

El contenedor se reinicia solo si falla o si se reinicia la Raspberry
(`restart: unless-stopped` en `docker-compose.yml`), en cuanto el propio
Docker arranca — no hace falta configurar ningún servicio `systemd` aparte.
La base de datos (`data/stock.db`) vive en la Raspberry, fuera del
contenedor, así que sobrevive a reconstrucciones de la imagen.

**Comandos útiles:**

```bash
docker compose logs -f          # ver los registros en tiempo real (Ctrl+C para salir)
docker compose ps               # ver si el contenedor está en marcha
docker compose restart          # reiniciar la aplicación
docker compose down             # pararla (los datos no se pierden)
```

La primera vez que abras la app en el navegador te pedirá crear una cuenta
(usuario y contraseña) antes de poder usarla — ver [Usuarios y
sesión](#usuarios-y-sesión).

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
