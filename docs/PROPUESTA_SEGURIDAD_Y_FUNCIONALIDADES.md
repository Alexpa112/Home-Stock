# Propuesta de seguridad y funcionalidades — Dreame! / StockHogar

**Fecha:** 2026-08-05 · **Rama analizada:** `dev2` (587ca890) · **Autor:** alejandro.paz

**Contexto asumido (confirmado contigo):**
- La app se publica en Internet mediante Cloudflare Tunnel.
- El Panel de Gestión (`:5001`) escucha en la LAN.
- **Objetivo: abrir la app a cualquiera** (registro público, usuarios que no controlas).

Ese último punto es el que cambia todo. El código actual está escrito con la
hipótesis, muy razonable hasta ahora, de *"esto es un aparato doméstico en mi
red, usado por gente de confianza"*. Hay decisiones explícitamente documentadas
en el propio código que lo dicen (sesión de 365 días, contador de intentos en
memoria, contraseña única del panel). Esas decisiones dejan de ser válidas en
cuanto el registro es abierto.

Este documento separa: **(A)** lo que hay que arreglar sí o sí antes de abrirla,
**(B)** el endurecimiento posterior, y **(C)** el roadmap de producto.

### Decisiones ya tomadas (ver §7)

1. **Registro abierto de verdad**, sin fase de invitación. S-05 (cuotas y
   CAPTCHA) se mantiene como bloqueante de la Fase 0, sin margen.
2. **Se acepta depender de Cloudflare** como capa de borde: WAF, Turnstile y
   rate limiting ahí donde sea posible, en vez de reconstruirlo todo en la app.
3. **El panel sigue publicado por Cloudflare Tunnel con HTTPS**, como hoy. Esto
   cambia el diagnóstico de S-04 (ver ficha revisada): la app de desarrollo de
   Werkzeug y la autenticación de una sola contraseña dejan de ser un problema
   "solo de LAN" y pasan a estar expuestas a Internet igual que la app
   principal — la prioridad sube, no baja.
4. **Migrar de SQLite.** Se fija un plan de migración a PostgreSQL en vez de
   esperar a que el umbral de concurrencia se cumpla en producción.
5. **El titular legal sigue siendo Alejandro Paz Silva** (persona física). Se
   revisa la redacción de los textos legales para que sea coherente con un
   servicio de registro abierto (ver §7.5).

---

## 0. Resumen ejecutivo

| Bloque | Nº | Comentario |
|---|---|---|
| Hallazgos críticos | 5 | Explotables hoy desde Internet o rompen la app con tráfico normal |
| Hallazgos altos | 8 | Bloqueantes para un servicio público |
| Hallazgos medios/bajos | 13 | Deuda de seguridad a planificar |
| Funcionalidades bloqueantes | 8 | Faltan piezas que un servicio público da por hechas |
| Mejoras de producto | 12 | Roadmap, sin urgencia |

### Los cinco que arreglaría esta semana

1. **S-01 — El límite de intentos de login es un único cubo global.** Como el
   backend solo ve la IP del contenedor de Next, 5 fallos de cualquiera dejan
   sin login a todo el mundo durante 10 minutos. DoS de una línea de `curl`.
2. **S-02 — El SSE de mantenimiento agota los hilos con 8 usuarios.** Cada
   cliente abre un `EventSource` que bloquea un hilo de gunicorn; hay 8 en
   total. No es solo un DoS: es un techo duro de concurrencia.
3. **S-03 — El "terminal seguro" del panel permite `docker exec`** con
   argumentos libres → ejecución arbitraria dentro del contenedor, incluida la
   lectura de `data/secret.json` (clave de firma de sesiones).
4. **S-04 — No hay recuperación de contraseña ni verificación de email.** Sin
   esto no se puede abrir el registro: cada olvido es una cuenta perdida y una
   intervención manual tuya en el panel.
5. **S-05 — Registro abierto sin ninguna cuota.** Cuentas ilimitadas, OCR
   ilimitado (tu clave de Groq), almacenamiento ilimitado en la tarjeta SD.

---

## 1. Modelo de amenaza

### 1.1 Superficie actual

```
                 Internet
                    │
        ┌───────────▼────────────┐
        │  Cloudflare Tunnel     │  TLS termina aquí
        └───────────┬────────────┘
                    │  (la IP real del cliente se pierde aquí → S-01)
        ┌───────────▼────────────┐
        │ contenedor "frontend"  │  Next.js :3000 · cabeceras de seguridad · rewrites
        └───────────┬────────────┘
                    │  http://stockhogar:5000 (red bridge de Docker, sin TLS)
        ┌───────────▼────────────┐
        │ contenedor "stockhogar"│  Flask + gunicorn (2 workers × 4 hilos) · ROOT
        └───────────┬────────────┘
                    │  volumen ./data
        ┌───────────▼────────────┐
        │ data/stock.db  (SQLite, sin cifrar)                    │
        │ data/secret.json (clave de firma de sesiones)          │
        │ data/backups/*.db (copias sin cifrar)                  │
        └───────────┬────────────┘
                    │  mismo sistema de ficheros
        ┌───────────▼────────────┐
        │ Panel :5001            │  Werkzeug (dev server) · sin TLS · 1 contraseña
        └────────────────────────┘
                    │
              LAN doméstica
```

Salidas hacia terceros: **Groq** (foto del ticket), **Google/Apple** (OAuth),
**SMTP** (invitaciones y códigos 2FA), **GHCR** (imágenes Docker).

### 1.2 Qué protegemos y de quién

| Activo | Amenaza principal | Impacto si cae |
|---|---|---|
| `data/stock.db` | Acceso al panel o al contenedor | Inventario, gastos, recibos y emails de todos los hogares |
| `data/secret.json` | Lectura del volumen (S-03) | Falsificación de la sesión de cualquier usuario, indefinidamente (S-08) |
| `.env` | Panel comprometido | Secretos OAuth, credenciales SMTP, clave de Groq |
| Disponibilidad | Bot/escáner de Internet | S-01 y S-02 tumban la app sin necesidad de vulnerabilidad alguna |
| Datos de terceros | Fallo de aislamiento entre hogares | Incidente RGPD con obligación de notificación |
| La Raspberry Pi | Registro abierto sin cuotas | SD llena, cuota de Groq agotada, sistema inservible |

### 1.3 Lo que ya está bien hecho

No todo son problemas; conviene no romperlo al refactorizar:

- Guardián global de sesión en `before_request` (`stockhogar/__init__.py:142`)
  con lista blanca explícita de rutas públicas. Es el patrón correcto: un
  endpoint nuevo nace protegido.
- CSRF activo en toda la app con excepciones justificadas y documentadas.
- Contraseñas con `werkzeug.security` (pbkdf2/scrypt), nunca en claro.
- Verificación real de firma del `id_token` de Apple contra JWKS
  (`stockhogar/rutas/oauth.py:31`) y vinculación por email **solo si el
  proveedor lo ha verificado**. Esto es un error clásico y aquí está resuelto.
- `state` en OAuth, tokens de invitación de 192 bits.
- Cabeceras de seguridad completas en Next (HSTS, nosniff, CSP,
  Permissions-Policy, frame-ancestors).
- SQLite en WAL con `foreign_keys=ON` y `busy_timeout`.
- Política de privacidad que ya declara a Groq como encargado del tratamiento
  y la transferencia internacional.

---

## 2. Hallazgos de seguridad

### 2.1 Tabla resumen

| ID | Severidad | Área | Hallazgo |
|---|---|---|---|
| S-01 | Crítico | Backend | El rate limit de login es un cubo global; la IP registrada es la del proxy |
| S-02 | Crítico | Backend | El SSE de mantenimiento bloquea un hilo por cliente (techo: 8) |
| S-03 | Crítico | Panel | `docker exec` permitido en el "terminal seguro" → RCE en el contenedor |
| S-04 | Crítico | Panel | Servidor de desarrollo, sin TLS, contraseña única sin usuario ni 2FA |
| S-05 | Crítico | Backend | Registro abierto sin cuotas ni CAPTCHA |
| S-06 | Alto | Infra | Contenedores como root, sin límites de recursos ni `no-new-privileges` |
| S-07 | Alto | Backend | Sin recuperación de contraseña; el email nunca se verifica |
| S-08 | Alto | Backend | Sesiones de 365 días sin revocación ni invalidación al cambiar la contraseña |
| S-09 | Alto | Backend | Sin registro de auditoría de eventos de seguridad |
| S-10 | Alto | Backend | Enumeración de usuarios y alta en hogar sin consentimiento del invitado |
| S-11 | Alto | Datos | Backups sin cifrar, descargables, y sin copia fuera del dispositivo |
| S-12 | Alto | Frontend | CSP con `unsafe-inline` y `unsafe-eval` |
| S-13 | Alto | CI/CD | Los workflows no ejecutan tests ni ningún escaneo de seguridad |
| S-14 | Medio | Backend | `/api/log/client` público, exento de CSRF y sin límite → inyección en el log |
| S-15 | Medio | Backend | Autorización reimplementada en cada blueprint (riesgo de IDOR) |
| S-16 | Medio | Backend | Subidas validadas solo por extensión; recibos servidos sin `nosniff` propio |
| S-17 | Medio | Backend | Sin cabeceras de seguridad en las respuestas de Flask |
| S-18 | Medio | Datos | `secret.json` sin rotación; su filtración es permanente |
| S-19 | Medio | Frontend | La caché en `localStorage` no se limpia al cerrar sesión |
| S-20 | Medio | Backend | Política de contraseñas mínima (8 caracteres, sin comprobación de filtradas) |
| S-21 | Medio | Backend | Sin límite de peticiones en OCR, subida de recibos ni envío de emails |
| S-22 | Medio | Datos | Sin exportación de datos personales (RGPD art. 20) |
| S-23 | Medio | Calidad | `typescript.ignoreBuildErrors: true` en producción |
| S-24 | Bajo | Panel | Cookie de sesión del panel sin `Secure`; 7 días de vida |
| S-25 | Bajo | Backend | Base de datos sin cifrar en reposo |
| S-26 | Bajo | Legal | Falta opt-out del OCR en la nube |

### 2.2 Fichas de los hallazgos

---

#### S-01 · Crítico · El rate limit de login es un cubo global

**Dónde:** `stockhogar/rutas/auth.py:136`, `stockhogar/servicios/intentos_login.py`,
`next.config.mjs:119-131`

**Qué pasa.** El navegador nunca habla con Flask: Next reescribe `/api/*` hacia
`http://stockhogar:5000` **desde el servidor**. Por tanto, para Flask,
`request.remote_addr` es siempre la IP del contenedor `frontend`. No hay
`ProxyFix` ni lectura de `X-Forwarded-For`/`CF-Connecting-IP` en ningún punto
del backend.

Consecuencias, en orden de gravedad:

1. **Denegación de servicio trivial.** Cinco intentos fallidos desde cualquier
   sitio bloquean el login de **todos los usuarios** durante 10 minutos. Un
   bucle de `curl` mantiene la app cerrada indefinidamente.
2. **El límite no limita a nadie en concreto.** No hay techo por atacante ni por
   cuenta.
3. **Los logs no sirven para nada forense**: todos los eventos comparten IP.
4. El módulo ya advierte en su docstring que con `--workers 2` los contadores
   son por proceso; sumado a lo anterior, el comportamiento real es
   impredecible.

**Propuesta.**
- Envolver la app con `werkzeug.middleware.proxy_fix.ProxyFix` y, cuando el
  tráfico venga del túnel, tomar la IP de `CF-Connecting-IP`. Confiar solo en
  las cabeceras cuando el salto anterior sea conocido.
- Cambiar la clave del contador a `(cuenta, IP)` y añadir bloqueo por cuenta con
  retroceso exponencial, no un corte binario.
- Persistirlo (tabla SQLite o Redis) para que sea consistente entre workers y
  sobreviva a un reinicio.
- Verificar el mismo problema en `StockHogar-Panel/panel_servidor/intentos_login.py`.

---

#### S-02 · Crítico · El SSE de mantenimiento bloquea un hilo por cliente

**Dónde:** `stockhogar/rutas/paginas.py:24`,
`stockhogar/servicios/mantenimiento.py:52`, `Dockerfile.raspbian:141`

**Qué pasa.** `/api/mantenimiento/stream` es público (está en `RUTAS_PUBLICAS`),
exento de CSRF, no tiene límite de conexiones y se queda en
`threading.Condition.wait()`, bloqueando el hilo de gunicorn que lo atiende.
El contenedor corre con `--workers 2 --threads 4`: **8 hilos en total**.

El frontend abre este stream **al cargar la app**. Es decir: no hace falta un
atacante. Con 8 pestañas abiertas —ocho usuarios normales, o un usuario con
varios dispositivos— el backend deja de atender peticiones. Desde Internet, ocho
`EventSource` tumban el servicio y no hay nada que lo impida.

**Propuesta.**
- Corto plazo: sustituir el SSE por *polling* ligero (cada 30–60 s sobre un
  endpoint que responde en microsegundos), o mover el stream a un worker
  asíncrono (`gevent`/`eventlet`) donde una conexión ociosa no cueste un hilo.
- Limitar conexiones SSE simultáneas por IP y cerrar el stream tras N minutos
  forzando reconexión.
- Recalcular el dimensionado de gunicorn para el objetivo de usuarios
  concurrentes y documentarlo.

---

#### S-03 · Crítico · `docker exec` permitido en el "terminal seguro"

**Dónde:** `StockHogar-Panel/panel_servidor/terminal_seguro.py:11-29`

**Qué pasa.** La lista blanca incluye `"exec": []`. El validador de argumentos
rechaza metacaracteres de shell y flags no reconocidas, pero **no** rechaza
palabras normales. Por tanto:

```
docker exec stockhogar-app cat /app/data/secret.json
```

pasa la validación entera. Con esa clave se firman cookies de sesión válidas
para cualquier `usuario_id`, sin contraseña y sin dejar rastro. Lo mismo sirve
para leer `/app/.env` o la base de datos completa. `git show` y `docker inspect`
tampoco tienen restricciones de argumentos.

Esto no es una vulnerabilidad remota (hay que estar autenticado en el panel),
pero convierte el panel en un objetivo de máximo valor y anula la separación
entre "administrar el servidor" y "leer los datos de los usuarios".

**Propuesta.**
- Quitar `exec` de `COMANDOS_PERMITIDOS`. Si hace falta, exponer acciones
  concretas y cerradas (p. ej. "ver versión de la app") en vez de un terminal.
- Restringir `inspect`/`show`/`logs` a nombres de contenedor o referencias de
  una lista conocida.
- Registrar cada comando ejecutado en un log de auditoría inmutable (hoy solo se
  hace `logger.warning`, en el mismo fichero que el panel puede vaciar).

---

#### S-04 · Crítico (revisado al alza) · El panel corre en un servidor de desarrollo y con una contraseña única, ahora expuesto por Cloudflare

**Dónde:** `StockHogar-Panel/run.py`, `StockHogar-Panel/panel_servidor/__init__.py:40-45`,
`StockHogar-Panel/panel_servidor/config.py:88-91`

**Decisión confirmada:** el panel sigue publicándose por Cloudflare Tunnel con
HTTPS, igual que la app principal. Eso resuelve el problema de "viaja en claro
por la WiFi" (el Tunnel termina TLS), pero **empeora todo lo demás**: el panel
que borra usuarios, descarga la base de datos completa, edita el `.env` y
ejecuta comandos (S-03) ya no es "solo alcanzable en mi LAN" — es alcanzable
por cualquiera en Internet que adivine o consiga la contraseña única. Con
registro abierto (decisión 1), el panel pasa a ser el objetivo más valioso de
toda la superficie.

**Qué pasa.**
- `app.run(host="0.0.0.0", port=5001)`: es el servidor de desarrollo de
  Werkzeug, no apto para producción (así lo dice su propia documentación) ni
  para tráfico de Internet.
- No se fija `SESSION_COOKIE_SECURE`; aunque el Tunnel entregue HTTPS al
  navegador, si algún día el panel se sirve también en HTTP interno (o el
  Tunnel se reconfigura) la cookie de administrador queda expuesta.
- Autenticación por **una sola contraseña compartida**, sin usuario, sin 2FA y
  sin caducidad. `PANEL_SECRET_KEY` cae a `os.urandom(32)` si no está en el
  `.env`, así que cada reinicio invalida las sesiones (síntoma, no problema).
- Se sigue aceptando contraseña en claro en el `.env` para instalaciones
  antiguas (`cuenta_panel.parece_hash`).
- Nada impide fuerza bruta remota contra `/login` salvo el mismo contador en
  memoria de intentos_login.py (mismo problema de fondo que S-01).

Desde ese panel se puede: descargar la base de datos entera, editar el `.env`
(secretos de OAuth, SMTP y Groq), cambiar la contraseña de cualquier usuario de
la app, borrar usuarios, reiniciar y apagar el sistema operativo, y conectar la
Pi a una WiFi. Todo eso, ahora, desde cualquier lugar del mundo.

**Propuesta (adaptada a "sigue por Cloudflare").**
- Poner el hostname del panel **detrás de Cloudflare Access** (o al menos
  restringir por regla de Cloudflare a un rango de IP/país si Access no es
  viable): así la autenticación de un solo secreto de la app deja de ser la
  única puerta — hay una capa de identidad delante que Cloudflare ya resuelve
  sin tocar código.
- Servir el panel con gunicorn (no el dev server de Werkzeug) aunque el TLS lo
  siga terminando el Tunnel.
- `SESSION_COOKIE_SECURE=True`, `SAMESITE=Strict`, vida de sesión de horas y no
  de días.
- Contraseña obligatoriamente hasheada (retirar el modo legado) + 2FA TOTP
  como segunda capa además de Cloudflare Access.
- Re-autenticación para las acciones destructivas (restaurar backup, editar
  `.env`, apagar, terminal).
- Rate limit de `/login` corregido igual que S-01 (misma causa: sin IP real no
  hay límite real).

---

#### S-05 · Crítico · Registro abierto sin cuotas ni CAPTCHA

**Dónde:** `stockhogar/rutas/auth.py:94`

**Qué pasa.** `/api/auth/registrar` es público y no tiene límite de frecuencia,
CAPTCHA, verificación de email ni lista de invitación. Una vez dentro, un
usuario puede crear hogares, artículos y gastos sin techo, subir recibos de
hasta 20 MB (`MAX_CONTENT_LENGTH`) y lanzar OCR contra **tu** clave de Groq
(1000 peticiones/día en el plan gratuito).

En una Raspberry Pi con tarjeta SD, esto no es un problema teórico: es la vía
más rápida de dejar el aparato inservible.

**Propuesta.**
- Interruptor `REGISTRO_ABIERTO` (env) con tres modos: cerrado, por invitación,
  abierto. Empezar por invitación.
- Cuotas por usuario y por hogar: nº de hogares, artículos, gastos, MB de
  recibos, escaneos OCR/día. Devolver 429 con mensaje claro.
- Rate limit por IP real en registro, login, OCR, subida de recibos y envío de
  emails.
- Cloudflare Turnstile en el registro (gratis y encaja con el túnel que ya usas).

---

#### S-06 · Alto · Contenedores como root y sin límites de recursos

**Dónde:** `Dockerfile.raspbian`, `Dockerfile.frontend`, `docker-compose.yml`

**Qué pasa.** Ningún `Dockerfile` define `USER`, así que gunicorn corre como
root dentro del contenedor, con `./data`, `./logs` y `./uploads` montados en
escritura. En `docker-compose.yml` no hay `read_only`, `cap_drop`,
`security_opt: no-new-privileges`, `mem_limit` ni `cpus`. Cualquier fallo de
memoria en OpenCV/Tesseract procesando una imagen manipulada escala a control
total del volumen de datos, y un OCR pesado puede consumir toda la RAM de la Pi
y arrastrar al sistema entero.

**Propuesta.**
- `USER` no privilegiado en ambas imágenes, con los volúmenes con el propietario
  correcto.
- En compose: `read_only: true` + `tmpfs` para lo escribible,
  `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]`,
  `mem_limit`, `cpus`, `pids_limit`.
- No publicar el puerto 5000 en el host: el backend solo necesita ser visible
  desde la red interna del compose.

---

#### S-07 · Alto · Sin recuperación de contraseña; el email nunca se verifica

**Dónde:** `stockhogar/rutas/auth.py` (no existe el flujo), `auth.py:154`

**Qué pasa.**
- No hay "he olvidado mi contraseña". El único remedio es que tú entres al panel
  y la cambies a mano (`/api/usuarios/<id>/password`). Con registro público eso
  no escala y, además, te obliga a manipular cuentas ajenas.
- El campo `email` solo se rellena por OAuth o desde el panel: **la app nunca
  verifica un email**. Aun así, el segundo factor se envía a esa dirección
  (`_generar_y_enviar_codigo`). Un email erróneo deja al usuario fuera de su
  cuenta de forma permanente.

**Propuesta.**
- Verificación de email con token de un solo uso y caducidad; email
  obligatorio para activar el 2FA.
- Restablecimiento de contraseña con token de un solo uso, caducidad corta,
  invalidación de todas las sesiones al usarlo, y respuesta idéntica exista o no
  la cuenta (para no permitir enumeración).
- Ligar la baja del 2FA a re-autenticación.

---

#### S-08 · Alto · Sesiones de un año, sin revocación

**Dónde:** `stockhogar/config.py:28`, `stockhogar/__init__.py:72-81`

**Qué pasa.** `DIAS_SESION = 365` con cookie firmada sin identificador de sesión
en servidor. Consecuencias: no se puede cerrar sesión en otros dispositivos; un
cambio de contraseña no invalida las sesiones ya abiertas; un móvil perdido
mantiene acceso un año; y si `secret.json` se filtra (ver S-03), las cookies
falsificadas son válidas para siempre.

El comentario del código justifica la decisión por ser *"un dispositivo
doméstico compartido"*. Es coherente con el escenario antiguo, no con el nuevo.

**Propuesta.**
- Tabla `sesiones` (id, usuario, dispositivo, IP, alta, último uso, revocada) y
  guardar solo el id en la cookie. Pantalla "Dispositivos conectados" con botón
  de revocar.
- Alternativa mínima si no quieres tabla: columna `session_version` en
  `usuarios`, incluida en la cookie e incrementada al cambiar contraseña, al
  activar/desactivar 2FA y al pulsar "cerrar todas las sesiones".
- Caducidad por inactividad (p. ej. 90 días) además de la absoluta.

---

#### S-09 · Alto · Sin registro de auditoría

**Dónde:** todo el backend

**Qué pasa.** No hay traza de: logins correctos y fallidos, cambios de
contraseña o de email, activación de 2FA, altas y bajas de miembros de un hogar,
invitaciones emitidas y aceptadas, bajas de cuenta, ni acciones del panel. Existe
`movimientos_stock`, que es auditoría **funcional** de inventario, no de
seguridad.

Con usuarios reales esto significa: no puedes responder "¿quién borró esto?",
no detectas fuerza bruta en curso y no puedes cumplir la obligación de
documentar un incidente.

**Propuesta.**
- Tabla `eventos_seguridad` (fecha, usuario, evento, IP real, user-agent,
  resultado, metadatos JSON), con retención definida y sin datos sensibles.
- Vista en el panel + alerta por email ante patrones (N fallos, login desde
  país nuevo, cambio de contraseña).

---

#### S-10 · Alto · Enumeración de usuarios y alta sin consentimiento

**Dónde:** `stockhogar/rutas/permisos.py:106-150`

**Qué pasa.** Compartir un hogar por nombre de usuario devuelve
`err_usuario_no_encontrado` (404) si no existe: eso permite comprobar qué
nombres de usuario están registrados, uno a uno y sin límite. Además, si existe,
se hace `INSERT OR REPLACE INTO permisos_hogar` **de inmediato**: el destinatario
se encuentra dentro de un hogar ajeno sin haber aceptado nada, y el propietario
puede llenar la app de gente sin su permiso.

**Propuesta.**
- Respuesta uniforme ("si ese usuario existe, recibirá una invitación").
- Unificar los dos caminos (usuario y email) en **una invitación que hay que
  aceptar**, con caducidad, como ya se hace en el flujo por email.
- Bandeja de invitaciones pendientes en la app y posibilidad de rechazar y
  bloquear.

---

#### S-11 · Alto · Backups sin cifrar, descargables y sin copia externa

**Dónde:** `StockHogar-Panel/panel_servidor/backups.py`,
`StockHogar-Panel/panel_servidor/rutas.py:623`

**Qué pasa.** Los backups son ficheros `.db` en claro en `data/backups/`,
descargables desde el panel. Si el panel cae (S-04), el atacante se lleva toda
la base de datos en una petición GET. Y al revés: todas las copias viven en la
misma tarjeta SD que la base de datos original, así que un fallo de la SD —el
modo de fallo más probable en una Raspberry Pi— lo pierde todo a la vez. No hay
regla 3-2-1 ni prueba de restauración.

**Propuesta.**
- Cifrar los backups (age/GPG con clave fuera del dispositivo) antes de
  escribirlos.
- Copia automática a destino externo (S3/B2/otro equipo) con retención.
- Prueba de restauración periódica y automática, con resultado visible en el
  panel.
- Descarga desde el panel con re-autenticación y registrada en auditoría.

---

#### S-12 · Alto · CSP con `unsafe-inline` y `unsafe-eval`

**Dónde:** `next.config.mjs:60`

**Qué pasa.** `script-src 'self' 'unsafe-inline' 'unsafe-eval'` deja la CSP casi
sin capacidad de contener un XSS. Está justificado en el comentario por el
script anti-FOUC de `app/layout.tsx:51`, pero es exactamente el caso que resuelve
un nonce.

**Propuesta.** Nonce por respuesta para el script inline y retirar
`unsafe-inline`; comprobar si la build de producción de Next todavía necesita
`unsafe-eval` (normalmente no) y quitarlo. Añadir `report-uri`/`report-to` para
detectar lo que se rompa antes de apretar del todo.

---

#### S-13 · Alto · CI sin tests ni escaneo de seguridad

**Dónde:** `.github/workflows/docker-build.yml`, `.github/workflows/docker-publish.yml`

**Qué pasa.** Los dos workflows construyen imágenes y publican en GHCR. No
ejecutan `pytest` (hay 41 ficheros de test en el repo), ni `jest`, ni
`pip-audit`, ni `npm audit`, ni escaneo de imagen (Trivy/Grype), ni análisis
estático (CodeQL/Bandit/Semgrep), ni detección de secretos (Gitleaks). Tampoco
hay Dependabot. Las imágenes que se despliegan solas en la Pi mediante
`auto_update.sh` nunca han pasado por una puerta de calidad.

**Propuesta.** Workflow `ci.yml` con: pytest + jest, `pip-audit` y `npm audit`,
Gitleaks, Bandit o Semgrep, y Trivy sobre la imagen construida. Que el push a
GHCR dependa de que ese workflow pase. Activar Dependabot para `pip`, `npm` y
`docker`.

---

#### S-14 · Medio · `/api/log/client`: inyección y saturación del log

**Dónde:** `stockhogar/rutas/paginas.py:63`

**Qué pasa.** Endpoint público, exento de CSRF, que escribe el `mensaje` y el
`contexto` recibidos **tal cual** en el log de la aplicación. Sin autenticación,
sin límite de tamaño y sin límite de frecuencia. Un atacante puede: (a) inundar
el log (2 MB × 4 rotaciones) y borrar así la evidencia real, (b) inyectar saltos
de línea para fabricar entradas de log falsas que el panel muestra como
auténticas, (c) llenar el disco de la Pi si el volumen de logs crece.

**Propuesta.** Limitar tamaño (p. ej. 2 KB), sanear saltos de línea, rate limit
por IP real, y considerar exigir sesión salvo en la pantalla de login.

---

#### S-15 · Medio · Autorización reimplementada en cada blueprint

**Dónde:** `stockhogar/rutas/articulos_compra.py:26` y `:348`,
`stockhogar/rutas/gastos.py:33` y `:153`, `stockhogar/rutas/permisos.py`,
`stockhogar/rutas/hogares.py` (63 referencias sueltas a `permisos_hogar` /
`usuario_propietario_id` en las rutas)

**Qué pasa.** Cada blueprint tiene su propio helper privado con su propia
noción de "puede ver" y "puede editar". No hay un decorador común ni una matriz
de tests que cubra el cruce completo (rol × recurso × acción). El aislamiento
funciona hoy —los tests de `test_aislamiento_*` lo demuestran para casos
concretos—, pero cada endpoint nuevo es una oportunidad de IDOR y el coste de
revisarlo crece con cada módulo.

**Propuesta.**
- Un único módulo `stockhogar/autorizacion.py` con
  `@requerir_hogar(nivel="ver"|"editar"|"propietario")` que resuelva el hogar,
  compruebe el permiso y lo deje en `g`.
- Migrar los blueprints uno a uno, sin cambiar comportamiento.
- Test parametrizado que recorra **todos** los endpoints por rol y exija 403/404
  donde toca. Es el test que más incidentes evita por línea escrita.

---

#### S-16 · Medio · Subidas validadas solo por extensión

**Dónde:** `stockhogar/rutas/ocr_tickets.py:22`, `stockhogar/rutas/gastos.py:527-563`

**Qué pasa.** Se comprueba la extensión del nombre de fichero, no el contenido.
El MIME con el que luego se sirve el recibo se deduce de esa misma extensión.
Las respuestas de Flask no llevan `X-Content-Type-Options: nosniff` propio
(hoy lo aporta Next porque todo pasa por su proxy, pero es una dependencia
frágil), ni `Content-Disposition`. Además el contenido llega intacto a OpenCV,
Pillow y Tesseract, que son precisamente donde aparecen los CVE de parsing de
imagen.

**Propuesta.** Validar magic bytes, **recodificar** la imagen con Pillow antes
de almacenarla o mandarla al OCR (elimina metadatos y polyglots de una vez),
servir siempre con `nosniff` y `Content-Disposition: inline; filename=...`, y
mantener las dependencias de imagen al día vía Dependabot.

---

#### S-17 · Medio · Sin cabeceras de seguridad en Flask

**Dónde:** `stockhogar/__init__.py`

Toda la defensa de cabeceras vive en `next.config.mjs`. Si algún día el backend
queda accesible directamente (un puerto publicado, un túnel de depuración, un
segundo frontend), no hay nosniff, ni HSTS, ni CSP, ni `frame-ancestors`.
**Propuesta:** `after_request` que añada el mínimo en Flask también. Defensa en
profundidad barata.

---

#### S-18 · Medio · `secret.json` sin rotación

**Dónde:** `stockhogar/seguridad.py`

Clave única, generada una vez, en el volumen montado, sin rotación y sin
soporte para varias claves simultáneas. Su filtración es irreversible mientras
no se cambie a mano (y cambiarla echa a todo el mundo). **Propuesta:** soportar
lista de claves (una activa + N de verificación) para poder rotar sin cerrar
todas las sesiones; documentar el procedimiento de rotación de emergencia.

---

#### S-19 · Medio · La caché del cliente sobrevive al logout

**Dónde:** `lib/dataCache.ts`, `lib/api.ts:170`

`dataCache` guarda stock y gastos en `localStorage`; el logout solo llama a
`/api/auth/logout`. En un móvil compartido, prestado o robado, el siguiente que
abra la app ve los datos del anterior aunque no pueda hacer peticiones.
**Propuesta:** limpiar todas las claves del prefijo (y las traducciones cacheadas
si contienen algo del usuario) en el logout y ante cualquier 401.

---

#### S-20 · Medio · Política de contraseñas mínima

**Dónde:** `stockhogar/rutas/auth.py:102`, `:329`, `:392`

Solo se exige longitud ≥ 8. No hay comprobación contra contraseñas filtradas ni
bloqueo por cuenta. **Propuesta:** seguir NIST SP 800-63B — longitud mínima 10,
sin reglas de composición absurdas, comprobación contra Have I Been Pwned por
k-anonymity (solo se envía un prefijo de 5 caracteres del hash, no la
contraseña), medidor de fortaleza en el frontend, y bloqueo temporal por cuenta
además del de IP (S-01).

---

#### S-21 · Medio · Sin límite en operaciones caras

**Dónde:** `stockhogar/rutas/ocr_tickets.py`, `stockhogar/rutas/tickets.py`,
`stockhogar/rutas/gastos.py` (recibos), `stockhogar/servicios/email_service.py`

Un usuario autenticado puede encadenar escaneos OCR (25 s de timeout contra Groq
o Tesseract local en una Pi), subir recibos de MB, y disparar invitaciones por
email en bucle —esto último puede además hacer que tu remitente SMTP acabe en
listas de spam. **Propuesta:** cuota diaria por usuario en OCR, cola con
concurrencia 1 para el pipeline local, límite de invitaciones por hogar y día.

---

#### S-22 · Medio · Sin exportación de datos personales

Existe borrado de cuenta y exportación de gastos a CSV (`gastos.py:364`), pero
no una exportación completa de los datos del usuario. El RGPD (arts. 15 y 20) lo
exige y para un servicio público es una petición que llegará.
**Propuesta:** endpoint que genere un ZIP con JSON de perfil, hogares,
inventario, listas, gastos, liquidaciones y los binarios de recibos.

---

#### S-23 · Medio · `ignoreBuildErrors: true`

**Dónde:** `next.config.mjs:3-5`

Se despliega a producción con errores de TypeScript silenciados. Es deuda de
calidad que también es de seguridad: los errores de tipos en el manejo de
respuestas de API son una fuente clásica de fallos de control de acceso en el
cliente. **Propuesta:** arreglar los errores pendientes y quitar la bandera;
si son muchos, ponerla en falso en CI antes que en local.

---

#### S-24 · Bajo · Cookie del panel sin `Secure`, 7 días de vida

Ver S-04. Se lista aparte porque es un cambio de dos líneas
(`panel_servidor/__init__.py:40-45`) que se puede hacer ya.

---

#### S-25 · Bajo · Base de datos sin cifrar en reposo

`data/stock.db` es un fichero SQLite plano. Quien tenga la tarjeta SD en la mano
tiene los datos. Es un riesgo aceptable en una vivienda, pero conviene decidirlo
explícitamente. **Propuesta:** cifrado del volumen (LUKS) o SQLCipher, y en
cualquier caso cifrar los backups (S-11), que es donde el riesgo es mayor porque
salen del dispositivo.

---

#### S-26 · Bajo · Falta opt-out del OCR en la nube

La política de privacidad ya declara correctamente a Groq como encargado y la
transferencia internacional. Falta la otra mitad: un ajuste por usuario del tipo
"no enviar mis tickets a la nube, usar solo el reconocimiento local", que ya es
técnicamente posible porque el pipeline Tesseract existe como respaldo.
También conviene revisar la redacción del apartado de gastos compartidos
("no se comparten con ningún tercero"), que hoy es cierta —los recibos de gastos
no pasan por Groq, solo los tickets escaneados— pero dejaría de serlo en cuanto
se conecte el OCR a los recibos.

---

## 3. Funcionalidades que faltan antes de abrir al público

No son mejoras: son piezas que un servicio con registro abierto da por hechas.

| ID | Funcionalidad | Por qué es bloqueante |
|---|---|---|
| F-01 | Verificación de email en el registro | Sin ella no hay 2FA fiable, ni recuperación, ni forma de contactar |
| F-02 | Recuperación de contraseña | Cada olvido es hoy una intervención manual tuya |
| F-03 | Gestión de sesiones y dispositivos | Cerrar sesión en un móvil perdido; ver S-08 |
| F-04 | Cuotas y planes de uso | Protege la Pi y tu clave de Groq; ver S-05 |
| F-05 | Invitaciones que se aceptan | Nadie debe entrar en un hogar sin decir que sí; ver S-10 |
| F-06 | Exportación completa de datos | RGPD art. 20; ver S-22 |
| F-07 | Registro de consentimiento | `VERSION_TERMINOS` ya existe; falta guardar cuándo y desde dónde se aceptó |
| F-08 | Canal de incidencias y aviso de estado | Un servicio público necesita un sitio donde decir "está caído" |

Además, dos consecuencias de abrir el registro que conviene decidir ya:

- **Rol de administrador dentro de la app.** Hoy la administración de usuarios
  está solo en el panel del servidor, que es el activo más sensible (S-04). Con
  usuarios reales harán falta acciones de soporte que no impliquen dar acceso a
  la Pi.
- **Multi-tenancy real.** El aislamiento actual es por hogar y funciona, pero
  el catálogo (`historial_articulos`) y las traducciones han dado ya problemas
  de aislamiento (hay tests dedicados a eso y una corrección de julio de 2026).
  Con usuarios ajenos, cualquier fuga ahí es un incidente notificable.

---

## 4. Roadmap de producto

Ordenado por relación valor/esfuerzo, no por atractivo.

| ID | Mejora | Notas |
|---|---|---|
| P-01 | **Notificaciones push (PWA)** | Caducidades y stock mínimo dejan de depender de que abras la app. Es la funcionalidad que más engancha en apps de despensa |
| P-02 | **Modo offline real** | Hoy no hay `service worker` (`public/` no tiene `sw.js`); la PWA es instalable pero no funciona sin red, aunque ya existe caché en cliente. En un supermercado con mala cobertura esto se nota |
| P-03 | **Escaneo de código de barras (EAN)** | Alta de producto en un gesto; complementa el OCR de tickets y no depende de terceros |
| P-04 | **Historial de precios por producto** | Los importes ya llegan en el OCR; permite "esto está más caro que el mes pasado" y comparativa por supermercado. Es diferencial frente a la competencia |
| P-05 | **Presupuesto mensual y alertas de gasto** | Cierra el círculo con el módulo de gastos ya rediseñado |
| P-06 | **Recetas → lista de la compra** | Alta demanda en apps de despensa; se apoya en el catálogo que ya tienes |
| P-07 | **Caducidades con recordatorio** | `DIAS_AVISO_DEFECTO` ya existe; falta el recordatorio proactivo (depende de P-01) |
| P-08 | **Roles más finos en el hogar** | Hoy solo `ver`/`editar` + propietario. Falta "administrador" y permisos por módulo (p. ej. ver inventario pero no gastos) |
| P-09 | **Importar/exportar listas e inventario** | Facilita la migración desde otras apps, que es la mayor fricción de entrada |
| P-10 | **Widget / accesos rápidos** | Añadir a la lista sin abrir la app |
| P-11 | **Estadísticas de consumo** | `movimientos_stock` ya guarda el histórico: "compras leche cada 5 días" habilita sugerencias automáticas |
| P-12 | **QA de accesibilidad e i18n** | Ya hay 8+ idiomas; falta revisión de contraste, foco visible y lectores de pantalla |

---

## 5. Plan por fases

### Fase 0 — Antes de tocar nada más (1–2 semanas)

Objetivo: que la app aguante estar en Internet.

| Orden | Tarea | Hallazgo | Esfuerzo |
|---|---|---|---|
| 1 | `ProxyFix` + IP real de Cloudflare + rate limit por cuenta e IP, persistido | S-01 | M |
| 2 | Quitar el SSE bloqueante o pasar a worker asíncrono | S-02 | M |
| 3 | Quitar `docker exec` del terminal del panel | S-03 | S |
| 4 | Panel: gunicorn + Cloudflare Access delante + `SESSION_COOKIE_SECURE` + 2FA | S-04, S-24 | M |
| 5 | Interruptor de registro + cuotas básicas + Turnstile | S-05 | M |
| 6 | Contenedores sin root + límites de recursos | S-06 | S |
| 7 | Límite y saneado en `/api/log/client` | S-14 | S |

### Fase 1 — Requisitos para abrir el registro (2–4 semanas)

| Orden | Tarea | Hallazgo / ID | Esfuerzo |
|---|---|---|---|
| 1 | Verificación de email + recuperación de contraseña | S-07, F-01, F-02 | L |
| 2 | Tabla de sesiones + revocación + pantalla de dispositivos | S-08, F-03 | M |
| 3 | Auditoría de eventos de seguridad + vista en el panel | S-09 | M |
| 4 | Invitaciones con aceptación y sin enumeración | S-10, F-05 | M |
| 5 | Backups cifrados + copia externa + prueba de restauración | S-11 | M |
| 6 | CI con tests + `pip-audit`/`npm audit` + Trivy + Gitleaks | S-13 | M |
| 7 | Política de contraseñas NIST + HIBP | S-20 | S |

### Fase 2 — Endurecimiento y cumplimiento (1–2 meses)

| Tarea | Hallazgo / ID | Esfuerzo |
|---|---|---|
| Módulo único de autorización + matriz de tests por rol | S-15 | L |
| CSP con nonce, sin `unsafe-inline`/`unsafe-eval` | S-12 | M |
| Recodificación de imágenes + validación por magic bytes | S-16 | S |
| Cabeceras de seguridad también en Flask | S-17 | S |
| Rotación de clave de sesión | S-18 | M |
| Limpieza de caché en logout | S-19 | S |
| Cuotas en OCR, recibos y emails | S-21 | M |
| Exportación completa de datos (RGPD) | S-22, F-06 | M |
| Quitar `ignoreBuildErrors` | S-23 | M |
| Opt-out del OCR en la nube | S-26 | S |

### Fase 1.5 — Migración a PostgreSQL (decisión 4)

Se descarta seguir en SQLite. Con registro abierto, escrituras concurrentes de
varios hogares y el volumen de OCR/gastos previsto, el umbral de dolor de
SQLite (bloqueos de escritor único incluso en WAL, sin réplicas, backup solo
por copia de fichero) se alcanza pronto y es mejor migrar con margen que en
caliente con la app ya poblada.

| Paso | Detalle |
|---|---|
| 1. Capa de acceso a datos | Antes de tocar el motor: revisar los ~89 usos de sintaxis específica de SQLite (`INSERT OR REPLACE`, `INSERT OR IGNORE`, `lastrowid`, `COLLATE NOCASE`, `PRAGMA table_info`, `strftime`) repartidos en `stockhogar/db.py` y los blueprints, y decidir equivalentes en Postgres (`ON CONFLICT`, `RETURNING id`, `COLLATE "und-x-icu"` o `ILIKE`, `information_schema`, funciones de fecha nativas) |
| 2. Docker Compose | Añadir servicio `postgres` con volumen propio; mantener SQLite como *fallback* de solo lectura hasta confirmar la migración en producción |
| 3. Script de migración de datos | Volcado tabla a tabla con conversión de tipos (BLOB de recibos/tickets, timestamps ISO), verificado con un `diff` de recuentos y sumas de control antes de cortar el tráfico |
| 4. Panel de Gestión | `StockHogar-Panel/panel_servidor/db.py` y `backups.py` asumen SQLite (copiar el fichero); hay que rehacerlos para `pg_dump`/`pg_restore` |
| 5. Corte | Ventana de mantenimiento (ya existe el flag), migración, verificación, vuelta a servicio. Backups de ambos lados conservados hasta confirmar estabilidad |

Esfuerzo estimado: **L** (2-3 semanas), en paralelo con la Fase 1 una vez que
el interruptor de registro (S-05) ya esté controlando el volumen de escritura.

### Fase 3 — Producto

P-01 → P-12 según prioridad de negocio. Recomendación: **P-01 + P-07** juntos
(notificaciones y caducidades son la misma pieza) y luego **P-02** (offline),
que es lo que más se nota en uso real.

---

## 6. Verificación y pruebas

La regla 10 del proyecto ya exige tests con cada cambio y hay 41 ficheros en
`tests/`. Lo que falta es la capa de seguridad:

1. **Matriz de autorización.** Test parametrizado sobre todos los endpoints ×
   roles (anónimo, usuario sin acceso, `ver`, `editar`, propietario) que exija el
   código de estado correcto. Es el que más protege contra IDOR y el que hace
   barato añadir módulos nuevos.
2. **Tests de sesión y CSRF.** Que un POST sin `X-CSRFToken` falle; que una
   cookie de un usuario borrado no sirva (ya cubierto por `requerir_sesion`, pero
   sin test); que cambiar la contraseña invalide las sesiones (tras S-08).
3. **Tests de rate limit** con IP simulada vía `X-Forwarded-For`, para que S-01
   no vuelva.
4. **Test de que las rutas públicas son exactamente las esperadas**: comparar
   `RUTAS_PUBLICAS` con una lista fija. Cualquier endpoint que se haga público
   por error rompe el test.
5. **Escaneo automático en CI** (S-13) y prueba de restauración de backup
   automatizada (S-11).

---

## 7. Decisiones tomadas

### 7.1 Registro abierto de verdad

Sin fase de invitación previa. Consecuencia directa: **S-05 (cuotas y
CAPTCHA) no tiene margen** — debe entrar en la Fase 0, no después. Si el
interruptor `REGISTRO_ABIERTO` se implementa igualmente (recomendado como red
de seguridad operativa, para poder cerrar el grifo sin desplegar código si algo
se descontrola), su valor por defecto es "abierto".

### 7.2 Se acepta depender de Cloudflare

WAF, Turnstile en el registro y rate limiting de borde donde Cloudflare lo
ofrezca, en vez de reconstruir esas capas en la app. Reduce el alcance real de
S-01 y S-05: aunque el arreglo de código (IP real + límite por cuenta) sigue
haciendo falta como segunda línea, Cloudflare puede absorber gran parte del
tráfico abusivo antes de que llegue al túnel.

### 7.3 El panel sigue por Cloudflare Tunnel con HTTPS, como ahora

No se mueve a VPN. Esto **no reduce** la prioridad de S-04 — la sube, porque
un panel con contraseña única y sin 2FA que antes solo era alcanzable desde la
LAN ahora es alcanzable desde cualquier sitio (ver ficha de S-04 revisada en
§2.2 y la tarea correspondiente en la Fase 0). La mitigación recomendada que
mejor aprovecha lo ya decidido en 7.2 es poner **Cloudflare Access** delante
del hostname del panel: añade una capa de identidad gestionada por Cloudflare
sin depender solo del secreto compartido de la app.

### 7.4 Migración a PostgreSQL

Se descarta seguir en SQLite a medio plazo. Ver el plan detallado como
**Fase 1.5** en la sección 5: inventario de sintaxis específica de SQLite (~89
usos), servicio Postgres en el compose, script de migración verificado y
adaptación del Panel (que hoy asume que un backup es "copiar el fichero .db").

### 7.5 Titular legal: se mantiene, se revisa la redacción

Alejandro Paz Silva sigue siendo el titular (`TITULAR_LEGAL`,
`EMAIL_CONTACTO_LEGAL` en `stockhogar/config.py:913-914`) — es correcto seguir
como persona física mientras el proyecto no se estructure como empresa, y no
hay nada que cambiar en el dato en sí. Repasando `app/legal/` con esa premisa,
lo que conviene ajustar **al abrir el registro** no es el titular, sino:

- **`app/legal/privacidad/page.tsx`**: el apartado "Con quién compartimos tus
  datos" (línea 59) ya cubre Google, Apple y Groq correctamente. Con registro
  público hay que añadir explícitamente que el hosting corre en infraestructura
  propia (la Raspberry Pi) detrás de **Cloudflare**, que por tanto actúa como
  encargado del tratamiento para el tráfico en tránsito (terminación TLS,
  mitigación de DDoS) aunque no almacene los datos de la aplicación. Hoy no se
  menciona en ningún punto de `app/legal/`.
- **`app/legal/cookies/page.tsx`**: si se activa Cloudflare Turnstile (decisión
  7.2, propuesto en S-05) o Cloudflare Access (decisión 7.3, panel), ambos
  pueden fijar sus propias cookies/tokens de sesión de borde — hay que
  documentarlas cuando se activen.
- **`stockhogar/config.py:919`**: subir `VERSION_TERMINOS` en el mismo cambio
  que actualice los textos legales, para forzar la re-aceptación de todos los
  usuarios existentes (regla 11 del proyecto).
- Nada de esto bloquea la Fase 0; entra de forma natural en la Fase 0 (tarea de
  cuotas/Turnstile) y en la Fase 1 (Cloudflare Access del panel): actualizar el
  texto legal en el mismo commit que active cada pieza, no por separado.
