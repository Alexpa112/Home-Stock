# Manual de instalación — Stock de Casa en Raspberry Pi (con Docker)

Guía paso a paso pensada para poder seguirla sin conocimientos previos de
informática. Tiempo estimado: 40–50 minutos (55–65 si además haces el
Paso 7, de acceso desde fuera de casa).

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
La primera vez te pedirá **crear una cuenta** (usuario y contraseña) antes
de dejarte entrar — es la única vez que hace falta, porque el dispositivo
queda recordado durante un año. Después de crearla, ya deberías ver la app
"Stock de Casa" funcionando.

El contenedor ya se reinicia solo si la Raspberry se apaga y se enciende,
así que aquí termina la instalación en casa — no hace falta ningún paso más
para dejarlo arrancando siempre.

## Paso 7 — Acceso desde fuera de casa (sin abrir puertos, gratis)

Esto es opcional: solo hace falta si quieres poder abrir la app desde el
móvil con datos, o desde cualquier sitio que no sea tu wifi de casa. Usamos
**Tailscale Funnel**, un servicio gratuito que crea un acceso seguro (con
candado 🔒, como un banco) sin tocar nada en el router.

1. En tu ordenador o móvil, ve a `tailscale.com` y crea una cuenta gratis
   (puedes entrar directamente con tu cuenta de Google, Microsoft o GitHub,
   no hace falta contraseña nueva).
2. Conéctate por SSH a la Raspberry (Paso 3) e instala Tailscale:

   ```
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

3. Da de alta la Raspberry en tu cuenta:

   ```
   sudo tailscale up
   ```

   Te aparecerá un enlace (algo como `https://login.tailscale.com/a/xxxxx`).
   Copia ese enlace y ábrelo en el navegador de tu ordenador o móvil, e
   inicia sesión con la misma cuenta del paso 1. En cuanto lo autorices ahí,
   la terminal de la Raspberry seguirá sola.

4. Activa los certificados de seguridad (el "candado" 🔒) para tu cuenta:
   entra en `https://login.tailscale.com/admin/dns`, busca la sección
   **HTTPS Certificates** y pulsa **Enable HTTPS**. Es un único interruptor,
   se activa una sola vez para siempre.

5. Publica la app hacia fuera con este comando:

   ```
   sudo tailscale funnel 5000
   ```

   La primera vez te puede pedir confirmar (escribe `y`). Al terminar te
   enseña una dirección parecida a `https://stockhogar.tuusuario.ts.net`
   — **apunta esa dirección**, es la que vas a usar desde fuera de casa.
   Puedes salir con `Ctrl+C`: el acceso se queda funcionando igual, no hace
   falta dejar la ventana abierta ni el ordenador encendido.

6. Prueba desde el móvil con el wifi **apagado** (usando datos): abre esa
   dirección `https://...ts.net` en el navegador. Deberías ver la app igual
   que en casa.

Este acceso se guarda solo y vuelve a funcionar automáticamente si la
Raspberry se reinicia o se va la luz — no hace falta repetir ningún paso ni
crear ningún servicio adicional.

**Importante sobre seguridad:** esa dirección `https://...ts.net` es
pública (cualquiera con el enlace puede entrar), igual que si fuera la web
de un banco. No la compartas si no quieres que otras personas vean o toquen
tu stock. Si algún día quieres desactivar el acceso desde fuera (y dejar
solo el acceso por wifi de casa del Paso 6), ejecuta:

```
sudo tailscale funnel --https=443 off
```

## Comprobación final

```
docker compose ps
```

Debe aparecer el contenedor `stock-hogar` con estado `Up` (o "running").

- [ ] `docker compose ps` muestra el contenedor en marcha
- [ ] Desde el móvil (misma wifi) cargo `http://stockhogar.local:5000`
- [ ] Tras `sudo reboot` y esperar un minuto, la app vuelve a estar
      disponible sin tocar nada
- [ ] (Si hiciste el Paso 7) Desde el móvil con datos, sin wifi, cargo
      `https://...ts.net` y veo la app

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

**La dirección `https://...ts.net` no carga (Paso 7)**
Comprueba que el candado esté activado: entra en
`https://login.tailscale.com/admin/dns` y revisa que "HTTPS Certificates"
esté en "Enabled". Después vuelve a ejecutar `sudo tailscale funnel 5000`.

**Quiero ver si el acceso desde fuera está activo**
```
sudo tailscale funnel status
```
Debe mostrar el puerto 5000 con la dirección `https://...ts.net`.

**`sudo tailscale up` no me deja entrar / el enlace ha caducado**
Repite el comando `sudo tailscale up`, te dará un enlace nuevo; ábrelo
antes de que pasen unos minutos.

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
- **Tailscale**: servicio gratuito que permite acceder a la Raspberry desde
  fuera de casa sin abrir puertos en el router ni tener IP fija.
- **Funnel**: la función de Tailscale que hace pública una dirección
  `https://...ts.net` para poder entrar desde cualquier sitio, no solo
  desde tus propios dispositivos.
- **HTTPS / candado 🔒**: la conexión va cifrada, como en la web de un
  banco; nadie que esté "escuchando" por el camino puede leer lo que
  escribes o ves.
