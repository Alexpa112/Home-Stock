# Manual de instalación — Stock de Casa en Raspberry Pi (con Docker)

Guía paso a paso pensada para poder seguirla sin conocimientos previos de
informática. Tiempo estimado: 40–50 minutos.

## Antes de empezar, ten esto a mano

- Tu Raspberry Pi 3 y su cargador (micro-USB)
- Una tarjeta microSD de al menos 8 GB (mejor 16 GB o más)
- Un ordenador con lector de tarjetas SD (o un adaptador USB)
- El nombre y la contraseña de tu wifi de casa

## Requisitos

**Hardware**
- Raspberry Pi 3 (Modelo B o B+); también vale un modelo más nuevo (4 o 5)
- microSD de 8 GB mínimo
- Cargador micro-USB 5V/2.5A
- Wifi de casa (2,4 GHz) o cable de red

**Software** (se instala en los pasos siguientes)
- Raspberry Pi OS Lite (64 bits)
- Docker y Docker Compose — la aplicación en sí (Python, Tesseract, etc.)
  va empaquetada dentro de un contenedor, así que no hace falta instalar
  nada de eso a mano en la Raspberry.

No hace falta monitor, teclado ni ratón para la Raspberry: todo se hace a
distancia desde tu ordenador.

## Paso 1 — Preparar la tarjeta de memoria

1. En tu ordenador, ve a `raspberrypi.com/software` y descarga/instala
   **Raspberry Pi Imager**.
2. Conecta la tarjeta microSD al ordenador.
3. Abre Raspberry Pi Imager.
4. **Elegir dispositivo** → Raspberry Pi 3.
5. **Elegir sistema operativo** → "Raspberry Pi OS (other)" → "Raspberry Pi
   OS Lite (64-bit)".
6. **Elegir almacenamiento** → tu tarjeta microSD (revisa que sea la
   correcta: el siguiente paso la borra entera).
7. **Antes de pulsar "Escribir"**, busca el icono de engranaje ⚙️ /
   "Editar ajustes" y configura:
   - Nombre del equipo (hostname): `stockhogar`
   - Activar SSH → usar contraseña
   - Usuario: `pi` — Contraseña: la que quieras (apúntala)
   - Wifi: SSID y contraseña de tu red, país `ES`
8. Guarda, pulsa **Escribir**, confirma el borrado y espera a que termine.

## Paso 2 — Primer arranque

1. Saca la tarjeta del ordenador y métela en la Raspberry (ranura en la
   parte de abajo).
2. Conecta la alimentación.
3. Espera 2–3 minutos mientras arranca y se configura sola.

## Paso 3 — Conectarte por SSH

En tu PC, abre **PowerShell** y ejecuta:

```
ssh pi@stockhogar.local
```

- La primera vez, escribe `yes` cuando pregunte si continuar.
- Introduce la contraseña del Paso 1 (no se ve nada al escribirla, es
  normal).
- Deberías ver un prompt como `pi@stockhogar:~ $`.

Si no conecta con el nombre, busca la IP de "stockhogar" en la lista de
dispositivos conectados de tu router y usa `ssh pi@<esa-ip>`.

## Paso 4 — Instalar Docker

Docker es el programa que va a ejecutar la aplicación metida en su propia
"caja" aislada (llamada contenedor), con todo lo que necesita ya dentro.

```
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo reboot
```

La última línea reinicia la Raspberry para que el cambio de permisos surta
efecto. Espera un minuto y vuelve a conectarte por SSH como en el Paso 3.

Comprueba que se instaló bien:

```
docker --version
docker compose version
```

Ambos comandos deben responder con un número de versión (no un error).

## Paso 5 — Descargar y arrancar la aplicación

```
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock
docker compose up -d --build
```

La primera vez tarda varios minutos: está descargando y montando todo lo
que necesita la aplicación dentro del contenedor. Cuando termine, vuelves a
ver el símbolo `$` y el contenedor ya está funcionando de fondo (el `-d`
significa "en segundo plano", no hace falta dejar la ventana abierta).

## Paso 6 — Probarla

Desde el móvil u otro ordenador en la misma wifi, abre el navegador en
`http://stockhogar.local:5000` (o `http://<ip-de-la-raspberry>:5000`).
Deberías ver la app "Stock de Casa" funcionando.

El contenedor ya se reinicia solo si la Raspberry se apaga y se enciende,
así que aquí termina la instalación — no hace falta ningún paso más para
dejarlo arrancando siempre.

## Comprobación final

```
docker compose ps
```

Debe aparecer el contenedor `stock-hogar` con estado `Up` (o "running").

- [ ] `docker compose ps` muestra el contenedor en marcha
- [ ] Desde el móvil (misma wifi) cargo `http://stockhogar.local:5000`
- [ ] Tras `sudo reboot` y esperar un minuto, la app vuelve a estar
      disponible sin tocar nada

## Solución de problemas

**No conecta con `ssh pi@stockhogar.local`**
Busca la IP en la lista de dispositivos del router y conéctate con
`ssh pi@<ip>`. Comprueba también que la Raspberry esté encendida y el wifi
bien escrito en el Paso 1.

**`docker: command not found` o `permission denied` al usar Docker**
Si acabas de instalar Docker, asegúrate de haber reiniciado la Raspberry
(`sudo reboot`) después del Paso 4: el permiso para usar Docker sin `sudo`
solo se aplica tras reiniciar sesión.

**La página no carga desde el móvil**
Comprueba que estés en la misma wifi. Revisa el contenedor con
`docker compose ps` (dentro de la carpeta `Home-Stock`) y, si no aparece
"Up", mira los registros con `docker compose logs`.

**Ver qué está pasando (registro)**
Dentro de la carpeta `Home-Stock`:
```
docker compose logs -f
```
(`Ctrl+C` para salir).

**El escáner de tickets da error**
Tesseract va incluido dentro del contenedor, así que no debería hacer
falta instalar nada aparte. Si falla, revisa los registros con
`docker compose logs` para ver el error exacto.

## Actualizar la app en el futuro

```
cd ~/Home-Stock
git pull
docker compose up -d --build
```

Esto descarga los cambios, reconstruye el contenedor con el código nuevo y
lo reinicia. Los datos guardados en `data/stock.db` no se pierden.

## Glosario

- **Terminal/PowerShell**: ventana donde escribes órdenes de texto en vez
  de hacer clic en botones.
- **SSH**: forma de controlar la Raspberry a distancia desde tu ordenador.
- **IP**: dirección de un dispositivo en tu red (ej. 192.168.1.35).
- **sudo**: ejecutar un comando con permisos de administrador.
- **Git/repositorio**: herramienta y lugar donde está guardado el código
  del proyecto (en GitHub).
- **Docker**: programa que ejecuta aplicaciones metidas en "cajas"
  aisladas (contenedores), con todo lo que necesitan ya incluido dentro,
  para que funcionen igual en cualquier ordenador.
- **Contenedor**: una de esas "cajas" en marcha; en este proyecto se llama
  `stock-hogar`.
- **Docker Compose**: la herramienta que lee el fichero
  `docker-compose.yml` del proyecto y sabe cómo construir y arrancar el
  contenedor con la configuración correcta (puerto, carpeta de datos...).
