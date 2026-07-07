# Home-Stock (Stock de Casa)

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
    ├── __init__.py               # Fabrica de la app (create_app) y registro de blueprints
    ├── config.py                 # Constantes: categorías, rutas, valores por defecto
    ├── db.py                     # Conexión SQLite, migraciones del esquema
    ├── integraciones/
    │   ├── bring_sync.py          # Cliente no oficial de Bring!
    │   └── ticket_ocr.py          # Lectura OCR local de tickets
    ├── rutas/                     # Un blueprint por dominio (así se añade uno nuevo sin tocar los demás)
    │   ├── paginas.py              # "/" (la SPA)
    │   ├── productos.py            # /api/productos (+ lógica de stock compartida)
    │   ├── lista_compra.py         # /api/lista-compra
    │   ├── ajustes.py              # /api/ajustes y /api/bring/*
    │   └── tickets.py              # /api/tickets/*
    ├── static/                    # CSS/JS servidos tal cual
    └── templates/                 # HTML (Jinja2)
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

## Uso

- Pulsa el botón **+** para añadir un producto (nombre, categoría, cantidad,
  unidad y stock mínimo).
- Usa los botones **+ / −** de cada tarjeta para ajustar el stock al
  consumir o comprar productos.
- Los productos con cantidad igual o inferior al stock mínimo se resaltan
  en rojo para avisar de que hay que reponerlos.
- Filtra por categoría con los chips superiores o busca por nombre.

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

- En cuanto un producto baja a su stock mínimo (o menos) se añade solo a la
  pestaña **🛒 Lista de la compra**, marcado como "Repuesto automático". Si
  vuelves a subir su cantidad por encima del mínimo, desaparece solo.
- También puedes añadir cosas a mano desde el botón **+** de esa pestaña
  (cosas puntuales que no llevas como stock).
- Marcar el check de un artículo lo quita de la lista. Para los "repuesto
  automático", si no actualizas también el stock del producto en la pestaña
  Stock, puede volver a aparecer la próxima vez que se recalcule.

## Sincronización con Bring! (opcional)

Bring! no tiene una API pública oficial. La integración usa la librería de
terceros [`bring-api`](https://github.com/miaucl/bring-api) (la misma que
usa Home Assistant), que inicia sesión con el email y contraseña de tu
cuenta Bring! contra su API interna no documentada. Esto significa que:

- Tu email y contraseña de Bring! se guardan **sin cifrar** en
  `data/stock.db`, en la propia Raspberry. Si te preocupa, usa una cuenta
  secundaria de Bring! dedicada solo a esto.
- Puede dejar de funcionar sin aviso si Bring! cambia su backend.

Para activarla: abre **⚙️ Ajustes**, marca "Sincronizar con Bring!",
introduce tu email y contraseña, pulsa **Probar conexión** para cargar tus
listas de Bring!, elige la lista destino y pulsa **Guardar**. Desde la
pestaña de la lista de la compra, el botón **🔄 Sincronizar con Bring!**
envía los artículos pendientes a esa lista.

## Actualizar la app

```bash
cd ~/Home-Stock
git pull
docker compose up -d --build
```

Esto descarga los cambios, reconstruye la imagen con el código nuevo y
reinicia el contenedor. Los datos en `data/stock.db` no se ven afectados.
