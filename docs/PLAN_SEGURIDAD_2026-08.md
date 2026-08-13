# Plan de seguridad — auditoría completa 2026-08-11

Auditoría de toda la aplicación (backend Flask, frontend Next.js, infraestructura,
CI/CD e instalador) con seis revisiones paralelas independientes. Todos los
hallazgos de este documento están verificados sobre el código (`fichero:línea`) o
reproducidos localmente; los que no se han podido confirmar están al final, en
"Sospechas no confirmadas".

Complementa a `PROPUESTA_SEGURIDAD_Y_FUNCIONALIDADES.md` (taxonomía S-01…S-26),
cuyo estado real se re-verifica en la sección 6.

Resumen: **1 crítico, 11 altos, 20 medios, 14 bajos**. El crítico es una fuga ya
publicada y sigue viva en `origin`.

---

## 1. FASE 0 — Contención inmediata (hoy, antes de cualquier otra cosa)

### C-1 [CRÍTICO] La clave de firma de sesión, la base de datos de usuarios y los logs están publicados en una rama remota

**Ubicación**: commit `d3cb82d26f6aa921af24435745bd68966d2a9f14` ("chore: track data
logs y caches de ejecucion", 2026-07-23), alcanzable desde
`origin/backup/dev2-produccion-pre-dev-promo-20260724`.

**Verificado**:

```
$ git show origin/backup/dev2-produccion-pre-dev-promo-20260724:data/secret.json
{"flask_secret_key": "<REDACTADO - ver S-18 sobre si se rotó o no>"}

$ git ls-tree -r --name-only origin/backup/dev2-produccion-pre-dev-promo-20260724
data/secret.json
data/stock.db
```

La `data/stock.db` commiteada NO es de prueba: tabla `usuarios` con tres filas
reales (`alexpa112`, `testinvitado`, `elamigo`) y sus `password_hash`
(`scrypt:32768:8:1$…`), más una fila en `invitaciones_lista` con su
`codigo_invitacion`. Se publicaron además 4.904 líneas de `logs/stockhogar.log`.

De las 11 ramas `origin/backup/*` solo esa contiene la fuga (comprobado una por una).

**Impacto**: esa clave firma las cookies de sesión. Quien la tenga fabrica la
cookie de cualquier usuario y entra sin contraseña, indefinidamente
(`DIAS_SESION = 365`, `stockhogar/config.py:40`). Es exactamente el escenario S-08,
pero sin necesidad de comprometer nada: ya está publicado. Además se filtran tres
hashes scrypt (crackeables offline sin límite de intentos), los nombres de usuario
y un código de invitación válido.

**La clave de este checkout (`852bb32d…`) ya no coincide con la filtrada, pero este
no es el dispositivo de producción.** Lo primero es comprobar
`data/secret.json` en la Raspberry Pi: si empieza por `6def2a03`, la explotación es
inmediata y trivial.

**Plan, en este orden**:

1. En la Pi: `cat data/secret.json`. Rotar con `seguridad.rotar_clave()` y reiniciar
   gunicorn (invalida sesiones abiertas; es el precio).
2. Cambiar la contraseña de los tres usuarios: sus hashes son públicos.
3. Invalidar el código de invitación filtrado
   (`DELETE FROM invitaciones_hogar WHERE codigo_invitacion = …`).
4. Borrar la rama remota: `git push origin --delete backup/dev2-produccion-pre-dev-promo-20260724`.
   Si se quiere borrar del histórico por completo:
   `git filter-repo --path data/secret.json --path data/stock.db --path logs/ --invert-paths`
   y force-push. Ojo: el commit puede seguir accesible por su SHA en la API de
   GitHub hasta que se pida un GC; conviene abrir un ticket de soporte si se
   considera necesario.
5. `.gitignore`: sustituir los patrones por extensión (`data/secret.json`,
   `data/*.db`) por los directorios completos `data/`, `logs/`, `__pycache__/`, para
   que un `git add -A` no pueda repetirlo. Nótese que
   `data/stock.db.backup.*` (que genera `scripts/maintenance.sh:32`) **no lo cubre
   ningún patrón actual**.
6. Regla nueva: prohibir ramas `backup/*` en `origin`. El respaldo de una promoción
   es el propio historial de `produccion`, no una rama con el árbol de trabajo.

---

## 2. FASE 1 — Alto (esta semana)

### A-1 El catálogo `productos` de TODA la instalación se filtra entre hogares y se envía a Anthropic

**Ubicación**: `stockhogar/rutas/tickets.py:251`, `stockhogar/servicios/ocr/gestor_ocr.py:55`,
`stockhogar/servicios/ocr/matcher_inteligente.py:138`, `stockhogar/servicios/ocr/matcher_productos.py:33`,
`stockhogar/servicios/ocr/claude_ocr.py:482-485`

`productos` no tiene columna de hogar (`db.py:460-468`); el aislamiento vive en
`stock_hogar`. Todo el resto del backend lo respeta (`productos.py:181,387,447`
siempre hacen `JOIN stock_hogar … AND sl.hogar_id = ?`; también
`auth.py:570` en la exportación RGPD). **Las cuatro consultas del escáner son las
únicas del backend que leen `productos` sin ese filtro.**

Tres consecuencias, todas verificadas:

1. **Fuga entre hogares por la respuesta HTTP.** `_normalizar_producto_id`
   (`claude_ocr.py:301`) valida el id devuelto por el modelo contra el catálogo
   global, así que un id de otro hogar **pasa la validación** — su propio docstring
   afirma lo contrario ("Un id inventado (o de otro hogar) … aquí se descarta").
   `tickets.py:65-68` sustituye entonces el nombre leído del ticket por el
   `nombre`/`categoria`/`icono` del hogar ajeno y lo devuelve. Lo mismo por otra
   vía: `matcher_inteligente.py:182-189` publica hasta 3 `alternativas` con
   `{id, nombre}` del catálogo global por línea (umbral 0.4), y eso sale al cliente
   vía `procesador_tickets_v2.py:114-119`. **Activar el opt-out de OCR local no
   cierra esta fuga**, porque el pipeline local hace lo mismo.
2. **Transferencia a un tercero no declarada.** En cada escaneo salen hacia EEUU los
   nombres de producto de todos los hogares — texto libre tecleado por otros
   usuarios ("Pañales talla 2", "Metformina"…). `app/legal/privacidad` declara solo
   el envío de "la foto (o el PDF) del ticket". El prompt lo llama "Catálogo del
   hogar" (`claude_ocr.py:178`), lo cual es falso.
3. **Enumeración activa.** Basta subir una imagen con texto genérico y repetir con
   distintas sílabas para volcar el catálogo de todas las familias. Un ticket con
   texto de inyección de prompt lo convierte en un volcado dirigido.

**Arreglo**: filtrar por el hogar activo en las cuatro consultas, con el estilo de
join implícito ya presente en el repo:

```sql
SELECT p.id, p.nombre, p.categoria, p.icono
  FROM productos p, stock_hogar sh
 WHERE sh.producto_id = p.id AND sh.hogar_id = ?
 ORDER BY p.nombre
```

`analizar_ticket` debe empezar por `hogar_id = hogar_actual_con_permiso(db, session)`
(403 si `None`, como ya hace `confirmar_ticket:331`). `gestor_ocr.procesar_ticket()`
necesita recibir `hogar_id`; la caché de `matcher_inteligente` debe llevarlo en la
clave. Añadir además un tope de entradas y truncar cada línea del prompt. Corregir
el docstring de `_normalizar_producto_id` y el literal "Catálogo del hogar".
**Impacto legal**: hay que declarar en `app/legal/privacidad` que junto a la imagen
se envía la lista de nombres del inventario (REGLA 11).

### A-2 `GET /api/hogares/buscar-usuarios` expone nombre de usuario y email de cualquier usuario

**Ubicación**: `stockhogar/rutas/permisos.py:19-50` (verificado íntegro)

`SELECT id, nombre_usuario, email FROM usuarios WHERE (nombre_usuario LIKE ? OR
email LIKE ?) AND id != ? LIMIT 10` con `%q%` de 2 caracteres. Sin `hogar_id`, sin
nivel, sin cuota: solo sesión válida. Con ~1.300 bigramas más sufijos de dominio se
recolecta la tabla `usuarios` casi completa (id + email), lista para phishing
dirigido o credential stuffing. Contrasta con `auth.py:798-831`, cuyo docstring dice
"nunca todos los usuarios de la instalación". Es el residuo de S-10.

**Arreglo**: borrar el endpoint. Tras el arreglo de S-10, `/compartir` ya acepta
`nombre_usuario` y responde con el mensaje genérico (`permisos.py:134`), así que el
buscador no aporta nada al flujo. Si se conserva: quitar `email`, match exacto en vez
de `LIKE %…%`, respuesta `{"existe": bool}` sin `id`, y cuota diaria.

### A-3 `PUT /api/auth/perfil` cambia la contraseña sin pedir la actual

**Ubicación**: `stockhogar/rutas/auth.py:374-386` (verificado)

Compárese con `/api/auth/cambiar-password` (`auth.py:476`), que sí exige
`password_actual`. Quien tenga una sesión válida sin conocer la contraseña (cookie
robada, navegador dejado abierto — la cookie dura 365 días) hace
`PUT /api/auth/perfil {"password":"nueva"}`: se cambia, se incrementa
`session_version` y **se refresca su propia sesión** (`auth.py:383`), expulsando al
dueño legítimo. Como el dueño no tiene email asociado (ver A-3b), no hay
recuperación: la cuenta queda tomada de forma permanente. En la misma petición puede
renombrar el login (`auth.py:350-363`, tampoco reautenticado). Esta rama esquiva
además la comprobación HIBP, y **el frontend nunca la usa** (`lib/api.ts:239` solo se
invoca con `usuario`/`nombre`): es superficie de ataque sin uso legítimo.

**Arreglo**: eliminar la rama `password` de `actualizar_perfil`. Exigir
reautenticación también para el cambio de `nombre_usuario`.

### A-3b No existe ningún endpoint para fijar el email de una cuenta creada con usuario+contraseña

**Ubicación**: `auth.py:332-390` frente a `auth.py:638-766`

Los flujos de verificación de email y de reset de contraseña están implementados y
bien construidos (token de 256 bits, hash en BD, un solo uso, expiración), pero
`actualizar_perfil` solo acepta `usuario`/`nombre`/`password`, y el único
`UPDATE … email` del proyecto es `SET email_verificado = 1` (`auth.py:685`). Es decir:
**quien se registra con usuario+contraseña nunca puede tener email, así que no puede
recuperar la contraseña ni activar 2FA.** La funcionalidad de S-07 solo alcanza a
cuentas OAuth. Esto es lo que convierte A-3 en toma de cuenta irreversible.

**Arreglo**: añadir email a `actualizar_perfil` con envío de verificación al nuevo
email y confirmación desde el antiguo si ya había uno.

### A-4 El límite de intentos de login se puede resetear, y no hay cubo por cuenta

**Ubicación**: `stockhogar/servicios/intentos_login.py:21-22, 60-68` (verificado)

```python
def _clave_cuenta(ip, cuenta):
    return f"{ip}:{cuenta.strip().lower()}" if cuenta else None

def limpiar_exito(ip, cuenta=None):
    db.execute("DELETE FROM intentos_login WHERE clave = ?", (ip,))   # borra TODO lo de esa IP
```

Dos fallos: **(a)** el atacante se registra una cuenta propia (registro abierto, sin
cuota) y hace el bucle `4 intentos contra la víctima → 1 login correcto contra su
propia cuenta → contador a cero`. Fuerza bruta ilimitada desde una sola IP sin
ninguna espera. `tests/test_intentos_login.py:36-39` documenta ese borrado como
comportamiento esperado. **(b)** El cubo "por cuenta" lleva la IP delante, así que
no protege una cuenta atacada desde varias IPs — que es justo lo que su docstring
afirma hacer, y lo que S-01 daba por resuelto.

**Arreglo**: tercer cubo con clave = solo la cuenta, con backoff exponencial; en
`limpiar_exito`, borrar únicamente la clave por cuenta del usuario que acaba de
autenticarse, nunca el cubo de IP entero.

### A-5 El código 2FA por email admite intentos ilimitados

**Ubicación**: `auth.py:202-210, 236-243, 257-270` (verificado)

`_generar_y_enviar_codigo` hace `ON CONFLICT(usuario_id) DO UPDATE SET … intentos = 0`
(`auth.py:206`), y `/api/auth/reenviar-codigo` lo llama sin ninguna cuota. El
atacante que ya tiene la contraseña prueba 5 códigos, llama a `/reenviar-codigo`
—que resetea el contador— y repite, indefinidamente. Ni `/reenviar-codigo` ni
`/verificar-codigo` pasan por `intentos_login` ni por `limite_por_ip`. De paso inunda
el buzón de la víctima, ocultando el aviso real. Añadido: `/verificar-codigo` compara
con `!=` en vez de `hmac.compare_digest` (`auth.py:240`), y `codigo_hash` es un
SHA-256 sin salt de 6 dígitos (`auth.py:213`), invertible al instante si se lee
`data/`.

**Arreglo**: contador acumulado por `usuario_id` independiente del código (máx. 10
intentos y 3 reenvíos/hora, persistido como `intentos_login`), bloqueo temporal al
superarlo, `hmac.compare_digest`, y purgar `pendiente_2fa_usuario_id` al agotar
intentos.

### A-6 `LIMITE_OCR_DIARIO` protege el endpoint que nadie usa

**Ubicación**: `tickets.py:175-178` (sin cuota) frente a `ocr_tickets.py:83`

Verificado: `uso_ocr_diario` solo se lee/escribe en `ocr_tickets.py`, y el frontend
escanea por `/api/tickets/analizar` (`lib/api.ts:504`). El test que cubre la cuota
(`tests/test_registro_y_cuotas.py:106`) parchea `ocr_tickets.LIMITE_OCR_DIARIO` y
ataca la ruta que no se usa: **pasa en verde sin cubrir nada**.

Cada llamada usa `_MAX_TOKENS = 16000` con `effort: "high"` y hasta 10 imágenes de
2576 px, o un PDF de 10 MB. Un bucle agota la cuota de la `ANTHROPIC_API_KEY` del
despliegue (denegación de servicio del escáner **para todos**, la clave es global) y
genera coste directo. Cada petición retiene además un worker hasta 180 s: con 2
workers × 4 hilos, ~8 peticiones concurrentes tumban el backend.

**Arreglo**: mover la comprobación e incremento de `uso_ocr_diario` a
`analizar_ticket()` (incrementar solo si se llamó al motor de nube), añadir
`limite_por_ip`, y reapuntar el test a la ruta real.

### A-7 El opt-out de OCR en la nube se puede saltar por `/api/ocr/procesar-ticket`

**Ubicación**: `ocr_tickets.py:47-87`, `gestor_ocr.py:52-61`

Verificado: `usuario_ocr_local` solo se consulta en `tickets.py:238`. El blueprint
`ocr` está registrado (`__init__.py:158`) y `/api/ocr/procesar-ticket` solo pide
sesión, así que un usuario que marcó "escanear solo en local" y sube la foto por esa
ruta (PWA en caché con frontend antiguo, cliente propio) manda su ticket y el
catálogo global a Anthropic contra su voluntad expresa. La app declara ese control
como el mecanismo de oposición del art. 21 RGPD (`privacidad/page.tsx:68-71`), así que
un opt-out con bypass es un incumplimiento, no solo un bug. La misma ruta valida el
fichero **solo por extensión** (`ocr_tickets.py:26`, `archivo.read()` en la 86 sin
`validar_y_recodificar`): regresión abierta de S-16.

**Arreglo**: dejar de registrar el blueprint `ocr` y borrar la ruta — el frontend no
la usa. Si se conserva: comprobar el opt-out **dentro de `ClaudeOCR.procesar()`** (un
solo sitio, no en cada llamante) y llamar a `validar_y_recodificar` antes del `read()`.

### A-8 `.env` no está excluido de la imagen: los builds locales en la Pi hornean todos los secretos en una capa

**Ubicación**: `.dockerignore` (verificado: solo `env/` y `venv/`, ningún patrón
cubre el fichero `.env`), con `Dockerfile:21` (`COPY . .`) y
`Dockerfile.raspbian:90` (`COPY . /app/`).

`install.sh` compila localmente en la Pi cuando `docker compose pull` falla
(`install.sh:706-712`) y con `--reinstall`. En ese build el contexto sí tiene el
`.env` real, así que `GOOGLE_CLIENT_SECRET`, `APPLE_CLIENT_SECRET`, `SMTP_PASSWORD`,
`ANTHROPIC_API_KEY` y `POSTGRES_PASSWORD` quedan escritos en una capa, extraíbles con
`docker save`, y sobreviven aunque se cambie el `.env` del host. Las imágenes de GHCR
**no** están afectadas (el runner no tiene `.env`): es riesgo local del dispositivo.

**Arreglo**: añadir `.env`, `.env.*` (con `!.env.example`), `install.log`,
`.install.lock`, `.git`, `node_modules/`, `.next/` al `.dockerignore`.

### A-9 `install.sh` deja copias en claro del `.env` en la carpeta que el panel expone para descarga

**Ubicación**: `install.sh:631-632` (verificado)

```bash
cp ".env" "data/backups/env-$(date +%Y%m%d-%H%M%S).bak"
```

`data/backups/` es el directorio que el Panel sirve por HTTP para descargar backups
(S-11). Hasta ahora el peor caso de esa descarga era la base de datos; con esto se
lleva también las credenciales OAuth, la contraseña SMTP y la API key de Anthropic en
texto plano, por un panel que la auditoría previa clasifica como Crítico sin TLS ni
2FA (S-04). Sin `chmod 600` posterior. Se conservan 5 copias, así que sobreviven
credenciales ya rotadas.

**Arreglo**: mover esos respaldos a un directorio no servido y fuera del volumen del
contenedor, con `install -m 600`; mejor, cifrarlos con `age`/GPG. Y en el Panel,
filtrar la descarga a `*.db.age` en vez de listar el directorio.

### A-10 Cadena de despliegue sin ninguna verificación de integridad

**Ubicación**: `docker-compose.yml:7,41` (`…:latest`), `install.sh:903-909` (cron cada
5 min), `.github/workflows/docker-publish.yml:7-27` (verificado: **no tiene `needs:`**)

La Pi descarga `:latest` por tag mutable, sin digest fijado ni firma (no hay cosign;
`install.sh:711` pasa `BUILDX_NO_DEFAULT_ATTESTATIONS=1`), y el cron reevalúa cada 5
minutos aplicando el cambio sin intervención humana. Y el único gate posible no
existe: `docker-publish.yml` se dispara por `push` a `produccion` **en paralelo** a
`ci.yml`, así que publica aunque los tests fallen. Resultado: quien consiga empujar a
`produccion` o publicar en ese paquete de GHCR obtiene ejecución de código en la Pi en
menos de 5 minutos, automáticamente. El repo tiene ramas `origin/copilot/*` y
`origin/claude/*`: más de un actor automatizado puede abrir cambios.

**Arreglo**: fijar las imágenes por digest (`image: …@sha256:…`) y actualizarlo como
parte del commit de release; `cosign sign` en el publish y `cosign verify` en
`auto_update.sh` antes de arrancar; `needs:` real en `docker-publish.yml` (o
`workflow_run` con `conclusion == 'success'`); proteger la rama `produccion` con
revisión obligatoria.

### A-11 Dependencias vulnerables, con las puertas de CI en verde falso

**Backend** (`pip-audit` ejecutado sobre `requirements.txt`): 12 vulnerabilidades en
4 paquetes.

| Paquete | Versión | Vulns | Arreglo | Bloqueo |
|---|---|---|---|---|
| `cryptography` | 42.0.8 | 8 | 43.0.1 → 49.0.0 | **`requirements.txt:17` pinea `>=42,<43`** |
| `flask` | 3.0.3 | 1 | 3.1.3 | — |
| `gunicorn` | 21.2.0 | 2 | 22.0.0 | `requirements.txt:14` pinea `>=21.2,<22` |
| `stanza` | 1.10.1 | 1 | 1.12.2 | — |

**Frontend** (`npm audit`): 6 vulnerabilidades de severidad alta, incluidas `next`
y cuatro CVE de libvips vía `sharp`.

**Y las puertas no bloquean nada**: `ci.yml:52` pone `continue-on-error: true` en
`audit-deps`; `docker-build.yml:31,75` pone `exit-code: "0"` en Trivy. Los escaneos
existen, pero ninguno puede impedir un despliegue — y el despliegue es automático
(A-10).

**Arreglo**: levantar los tres pines, `npm audit fix`, y quitar
`continue-on-error`/`exit-code: 0` al menos para severidad Crítica y Alta. Hay que
probar el salto de `cryptography` en armv7 antes de promocionar: es la dependencia
que motivó el pin.

---

## 3. FASE 2 — Medio (dos o tres semanas)

Agrupados por tema. Todos con ubicación verificada.

### Aislamiento multi-hogar (el eje más débil de la app)

| # | Hallazgo | Ubicación |
|---|---|---|
| M-1 | `productos` sin `hogar_id`: `PATCH`/`DELETE` escriben la fila global. En BD migradas, `db.py:540-562` sembró todas las listas con todos los productos, así que dos hogares comparten fila: cambiar `nombre`/`icono`/`dias_aviso` afecta al inventario y a los avisos de caducidad del otro, y el `DELETE` puede borrar la fila en cascada. Mismo bug ya corregido en `articulos_personalizados`. | `db.py:458-481`, `productos.py:423-427,482-486` |
| M-2 | `historial_articulos` es global (`UNIQUE(nombre COLLATE NOCASE)`) y se alimenta con todo lo que crea cada hogar (`stock.py:220`). `GET /api/historial` lo devuelve completo a cualquier usuario. Y el `ON CONFLICT … DO UPDATE` permite sobrescribir el icono/categoría que verá otro hogar. | `historial.py:70-79`, `stock.py:220` |
| M-3 | `categorias` y `categorias_gasto` son globales y **cualquier usuario autenticado puede crear y borrar**, sin hogar ni nivel. El guardián `en_uso` solo mira `productos`, ignorando `articulos_compra`, `articulos_personalizados`, `historial_articulos` y `gastos_recurrentes`: se puede borrar una categoría que solo usa otro hogar y dejar sus artículos apuntando a la nada. | `categorias.py:19-72`, `categorias_gasto.py:24-77` |
| M-4 | Los artículos personalizados se autorizan **por el dueño, no por el hogar**: con `editar` en un hogar de Alicia se leen, modifican y borran los artículos de otro hogar de Alicia al que no se tiene acceso. El `DELETE FROM articulos_compra WHERE articulo_personalizado_id = ?` no lleva `hogar_id`. | `articulos_compra.py:471-493,652-693` |

Arreglo común: dar propietario real (`hogar_id`) a `productos` e
`historial_articulos`, decidir explícitamente el modelo de `categorias`, y cambiar la
unidad de aislamiento de "dueño" a "hogar" en `articulos_personalizados`. Mientras no
haya migración, condicionar el `UPDATE` a que la fila no esté compartida y clonarla si
lo está (la "bifurcación" que ya hace `articulos_compra.py:386-421`).

**S-15 sigue parcial**: 11 de los 13 blueprints de datos resuelven autorización a
mano (`productos.py` ×9, `gastos.py` ×14, `articulos_compra.py` ×6 más dos helpers
propios), y `tests/test_matriz_autorizacion.py` **no cubre ninguno** de esos
endpoints, solo las rutas `/api/hogares/…`. Ampliar la matriz es la tarea de mayor
retorno de toda la fase.

### Autenticación y sesiones

| # | Hallazgo | Ubicación |
|---|---|---|
| M-5 | El 2FA **no se exige en el camino OAuth**: los callbacks nunca consultan `doble_factor_activo` (verificado: `grep` no encuentra ni una referencia en `oauth.py`). Quien comprometa la cuenta de Google del usuario entra sin código, pese a tener el 2FA activado. | `oauth.py:160-170,289-298` |
| M-6 | Cuentas OAuth sin `password_hash`: `check_password_hash(None, "x")` lanza `AttributeError` (verificado empíricamente) **antes** de `registrar_fallo()`. Resultado: evasión total del rate limit para esas cuentas, 500 en vez de 401 (oráculo de enumeración) y un traceback por petición. Nombre de usuario predecible (`oauth.py:133` usa la parte local del email). | `auth.py:180`, `oauth.py:145` |
| M-7 | La revocación de sesiones no se aplica en el guardián global ni en `/api/auth/estado` (ruta pública que devuelve email, nombre y estado de 2FA). Y la condición `"session_version" in session` (`api/base.py:83`) exime **para siempre** a las cookies emitidas antes del despliegue: cambiar la contraseña no las invalida. `DIAS_SESION = 365`. | `__init__.py:187-197`, `auth.py:63-113`, `api/base.py:83` |
| M-8 | `ip_cliente()` confía a ciegas en `CF-Connecting-IP` sin comprobar el peer. Con el puerto 5000 publicado en el host (M-13), cada petición cae en un cubo distinto de `intentos_login` y de `limite_por_ip`: el rate limit deja de existir y `eventos_seguridad` queda envenenado con IPs falsas (destruye el valor forense de S-09). | `red.py:12-13` |
| M-9 | Enumeración de usuarios por tres oráculos: el registro responde `err_usuario_duplicado`; el login solo paga scrypt (~116 ms medidos, más en una Pi) si el usuario existe; `/solicitar-reset-password` envía el SMTP **de forma síncrona** dentro de la petición, así que el tiempo de respuesta revela "existe y tiene email verificado". | `auth.py:136-140,180,691-728` |
| M-10 | La comprobación HIBP no cubre **ninguno** de los dos endpoints de cambio de contraseña, solo registro y reset. El usuario se registra con una contraseña que pasa el filtro y acto seguido la cambia por `Password1234`. Añadido: `es_password_filtrada` falla abierto, sin ninguna regla compensatoria. | `auth.py:374-378,459-461` |
| M-11 | **S-05 sin hacer**: `registrar()` no llama a `intentos_login`, ni a `limite_por_ip`, ni valida CAPTCHA, ni pide email, y autentica automáticamente. Un script crea cuentas ilimitadas — que es lo que habilita A-4(a). | `auth.py:116-161` |

### Borde web

| # | Hallazgo | Ubicación |
|---|---|---|
| M-12 | Open redirect por `?next=`: el valor no se valida como ruta relativa del propio origen. | `app/page.tsx:50,71,117,135` |
| M-13 | Puertos publicados en `0.0.0.0`. Docker inserta sus reglas **antes** de `ufw`, así que un firewall en la Pi no las tapa: cualquier dispositivo de la LAN (incluido el IoT doméstico) llega a `http://<ip-pi>:5000` en HTTP plano y se salta por completo Cloudflare (Access, WAF, rate limiting, TLS) y toda la CSP que fija el frontend. En HTTP plano la cookie no lleva `Secure`. `install.sh:940-941` imprime esas URLs como forma normal de acceso. Postgres, en cambio, está bien: sin `ports:`. | `docker-compose.yml:12-13,50-51` |
| M-14 | Inyección de HTML en los emails salientes: `nombre_lista` y `nombre_remitente` se interpolan sin escapar. Un hogar llamado `<a href="https://phishing…">Verifica tu cuenta</a>` genera un correo desde el SMTP y el dominio legítimos, con SPF/DKIM válidos, a direcciones arbitrarias — 20 invitaciones/día × 5 hogares = 100 correos/día/cuenta. (La inyección de **cabeceras** por esa vía está descartada: la stdlib la rechaza, verificado.) | `email_service.py:43,49,129,163` |
| M-15 | Bypass de S-16 por nombre de fichero tipo dotfile: `gastos.py:604` usa `rsplit` y `:639` usa `Path().suffix`, que discrepan. **Verificado**: `.png` pasa la whitelist y llega con extensión derivada vacía, sin validar; `recibo.png` se rechaza. | `gastos.py:604,639` |
| M-16 | Sin defensa frente a bomba de píxeles: `Image.MAX_IMAGE_PIXELS` no se fija en ningún punto, y `verify()` no decodifica. Un PNG de pocos cientos de KB a 12000×12000 pasa los límites de bytes y reserva ~400 MB al recodificar → OOM del contenedor en una Pi. `DecompressionBombError` no es `OSError` ni `ValueError`, así que escapa del `except` y sube como 500. | `utils/imagenes.py:42-57`, `claude_ocr.py:231-236` |
| M-17 | SSRF autenticado ciego: el `endpoint` de la suscripción push no se valida (ni esquema, ni host, ni lista de servicios conocidos) y `webpush` no lleva `timeout`. El servidor hace un POST desde dentro de la LAN doméstica al destino elegido. Condicional: `pywebpush`/`py-vapid` están comentados en `requirements.txt:24-26` pero documentados como instalados en producción. | `push.py:26-42`, `push_service.py:73-81` |
| M-18 | `confirmar_ticket` acepta `nombre` sin límite de longitud (`productos.py:159` sí acota a 80). Con `MAX_CONTENT_LENGTH = 20 MB` se inserta en `productos.nombre` una cadena de megabytes que, por A-1, **se concatena en el prompt de cada escaneo de cada usuario** hasta que toda llamada excede el contexto: DoS persistente del escáner con una sola petición, más inyección de prompt. `unidad` y `precio_unitario` tampoco se validan. | `tickets.py:342-348` |
| M-19 | Metadatos salientes: el PDF se envía a Anthropic **íntegro y sin tocar** (todas las páginas, autor, software, rutas incrustadas); y si Pillow falla al decodificar una imagen, se manda el original **con su EXIF**, que en fotos de móvil incluye coordenadas GPS del domicilio. El camino normal sí descarta EXIF (`_a_jpeg` no pasa `exif`). | `claude_ocr.py:460-468,231-236` |

### Infraestructura y suministro

| # | Hallazgo | Ubicación |
|---|---|---|
| M-20 | Sin lockfile de Python y rangos abiertos por arriba (`anthropic>=0.69`, `Pillow>=10.0`, `requests>=2.28.0`). Los builds no son reproducibles y **una versión maliciosa publicada en PyPI entra sola en el siguiente build automático** — que se dispara cada 5 minutos. Agravado por `--extra-index-url` de piwheels (`Dockerfile.raspbian:88`): pip elige por versión, no por prioridad de índice, que es el patrón de *dependency confusion*. Y `pip-audit` audita el rango, no lo instalado. | `requirements.txt`, `Dockerfile.raspbian:88` |
| M-21 | `ci.yml` y `docker-build.yml` no declaran `permissions:`, así que el `GITHUB_TOKEN` hereda el ajuste del repo (que sigue siendo "read and write" por defecto en repos antiguos) y se pasa a una acción de terceros (`gitleaks-action@v2`). Con `produccion` auto-desplegada, escritura sobre el repo = ejecución en la Pi. | `ci.yml:1-9,72-74`, `docker-build.yml:1-12` |
| M-22 | Acciones de terceros sin fijar por SHA, y `aquasecurity/trivy-action@master` es una referencia **mutable a la rama de desarrollo de un tercero**: lo que se ejecuta en CI cambia sin que nadie lo apruebe. | `docker-build.yml:24,71` |
| M-23 | `install.sh` descarga `https://get.docker.com` a una **ruta fija en `/tmp`** y lo ejecuta como root, sin checksum ni firma. Ruta predecible en directorio world-writable + ejecución privilegiada. Mismo patrón en `auto_update.sh:60`. | `install.sh:395-397` |
| M-24 | `install.sh` invoca el `install.sh` del Panel (código externo no auditado, ni en el repo) **con la caché de sudo ya caliente** (`sudo -v` en `:371`) y le pasa la ruta del proyecto: obtiene root y la ubicación de `.env` y `data/secret.json`. | `install.sh:951-958` |

---

## 4. FASE 3 — Bajo / higiene

| # | Hallazgo | Ubicación |
|---|---|---|
| B-1 | Inyección de fórmulas en CSV (`=`, `+`, `-`, `@` al inicio de celda) en las tres exportaciones. | `gastos.py:479-486`, `productos.py:52-56`, `articulos_compra.py:99-102` |
| B-2 | Emails completos de destinatarios y hasta 300 caracteres de la respuesta del modelo (= nombres de artículos comprados) en `logs/stockhogar.log`, que **lo lee un proyecto externo en vivo**. Sin retención más allá de la rotación, y no declarado en la política de privacidad. | `email_service.py:214`, `claude_ocr.py:403,561` |
| B-3 | Fragmento de la cookie de sesión en el log a nivel WARNING (los 20 primeros caracteres del payload, no la firma: no permite suplantar, pero no aporta nada — el `usuario_id` ya se registra al lado). | `__init__.py:113-120` |
| B-4 | `POST /api/push/suscribir` permite apropiarse de la suscripción de otro usuario: `ON CONFLICT(endpoint) DO UPDATE SET usuario_id = excluded.usuario_id` sin comprobar el dueño anterior. | `push.py:35-41` |
| B-5 | Invitaciones y enlaces: nivel **forzado a `editar`** en el enlace compartible, 30 días de vigencia, sin revocación, y en la vía email `email_destino` nunca se compara con el email de quien acepta — cualquier usuario con el código entra. | `permisos.py:261-297,300-357` |
| B-6 | `heic`/`heif` se acepta como recibo y se guarda **sin ninguna validación de contenido** (a diferencia del escáner, que los convierte con `heif-convert`). Almacenamiento arbitrario en la BD, que además viaja en el ZIP de exportación RGPD. | `gastos.py:26,640`, `imagenes.py:36-40` |
| B-7 | Tres `requests` sin `timeout` en el callback OAuth y `webpush` sin `timeout`: un proveedor que no responda cuelga el worker indefinidamente. | `oauth.py:92,99,223`, `push_service.py:76` |
| B-8 | Apple OAuth: sin `nonce`; la identidad se toma del `id_token` del form POST y **no del intercambio del `code`** (cuyo resultado se descarta); y el callback POST no está exento de CSRF, así que **el login con Apple no puede funcionar hoy** (falla cerrado, pero indica que el flujo no está probado). Retirar el fallback `APPLE_CLIENT_SECRET or APPLE_CLIENT_ID`. | `oauth.py:183-237,194` |
| B-9 | `GroqOCR` es código muerto exportado en `ocr/__init__.py:11` y listo para funcionar: activaría una transferencia a un cuarto proveedor no declarado, sin opt-out y sin cuota. Además apunta a un modelo sin visión. Borrar (con `tests/test_groq_ocr.py`). | `groq_ocr.py:27`, `ocr/__init__.py:11` |
| B-10 | `fuzzywuzzy` está archivado desde 2021 y no recibe parches, en el camino que procesa texto no confiable de tickets. Migrar a `rapidfuzz` (API compatible, más rápido, y elimina una extensión C del build ARM). | `requirements.txt:11-12` |
| B-11 | `scripts/maintenance.sh` hace backup de `data/stockhogar.db`, **que no existe** (la BD es `data/stock.db`): la opción "Backup" no copia nada e imprime "completado" en verde. El `VACUUM` de la opción 3 crea una BD vacía. Y `docker system prune -f` contradice la política de `docker_cache_prune.sh` y convierte la siguiente actualización en 45-60 min de recompilación. | `scripts/maintenance.sh:32-34,40,49` |
| B-12 | S-25 sin hacer: SQLite en claro, `data/stock.db` en `-rw-r--r--`, bind mount de escritura sobre el mismo `data/` que contiene `secret.json` (un compromiso de la app puede **reescribir** la clave de firma, no solo leerla). La SD de una Pi es trivialmente extraíble. | `docker-compose.yml:23-26`, `config.py:14` |
| B-13 | Cookie de sesión sin `Secure` por defecto (depende de que `APP_URL` sea https), `WTF_CSRF_SSL_STRICT = False` y `WTF_CSRF_TIME_LIMIT = None`. | `__init__.py:96,102-103`, `config.py:44` |
| B-14 | S-06 parcial: `Dockerfile` (el x86) **no tiene ninguna directiva `USER`** → corre como root; no hay `cap_drop: [ALL]`, `read_only` ni `pids_limit` en ningún servicio. | `Dockerfile:1-46`, `docker-compose.yml:32-88` |

---

## 5. Superficie que NO se ha podido auditar

**`StockHogar-Panel` está vacío y no hay `.gitmodules`** (verificado). No hay gitlink,
ni URL, ni commit esperado: desde este repositorio **no existe forma de recuperar ese
código**. Y es el componente más peligroso del despliegue:

- Los dos hallazgos **Críticos vigentes** de la auditoría previa viven ahí: S-03
  (`docker exec` permitido desde el "terminal seguro" → RCE en el contenedor) y S-04
  (servidor de desarrollo, sin TLS, contraseña única sin usuario ni 2FA).
- Todo el código de backups (S-11), incluida la ruta de descarga de la que depende el
  alcance real de A-9.
- Está expuesto por el mismo Cloudflare Tunnel, tiene acceso de escritura al volumen
  `data/` (donde vive `secret.json`), **puede pausar y reanudar el auto-despliegue**
  (`auto_update.sh:23-27`) y forma parte de la cadena de instalación con sudo caliente
  (M-24).

Cualquier afirmación sobre la seguridad del despliegue en su conjunto es incompleta
mientras siga así. **Acción**: registrarlo como submódulo con su commit fijado, o
documentar su URL y el commit desplegado y auditarlo en su propio repositorio. Un
directorio vacío sin `.gitmodules` es lo peor de las dos opciones.

---

## 6. Estado real de la taxonomía S-01…S-26

| ID | Declarado | Real | Nota |
|---|---|---|---|
| S-01 | rate limit login | **PARCIAL** | El cubo "por cuenta" lleva la IP dentro y se resetea (A-4) |
| S-05 | anti-abuso registro | **SIN HACER** | Solo se añadió el interruptor `REGISTRO_ABIERTO` (M-11) |
| S-06 | endurecer contenedores | **PARCIAL** | `Dockerfile` x86 sin `USER`; sin `cap_drop`/`read_only`/`pids_limit` (B-14) |
| S-07 | verificación email / reset | **PARCIAL** | Los flujos son correctos, pero **no hay forma de fijar el email** (A-3b) |
| S-08 | revocación de sesiones | **PARCIAL** | No se aplica en el guardián global; cookies legacy exentas para siempre; 365 días (M-7) |
| S-10 | invitaciones sin enumeración | **PARCIAL** | El alta ya requiere consentimiento, pero `buscar-usuarios` sigue abierto (A-2) |
| S-11 | backups cifrados | **SIN HACER** | Y este repo lo empeora: `.db` y `.env` en claro en `data/backups/` (A-9) |
| S-12 | CSP con nonce | **HECHO** | `middleware.ts:38-58` |
| S-13 | CI con escaneo | **PARCIAL** | Los escaneos existen pero **ninguno bloquea**, y el publish no depende de ellos (A-10, A-11) |
| S-14 | — | **HECHO** | |
| S-15 | autorización centralizada | **PARCIAL** | 11 de 13 blueprints a mano; la matriz de tests no los cubre |
| S-16 | validar ficheros por contenido | **PARCIAL** | Bypass por dotfile (M-15), `heic` sin validar (B-6), `/api/ocr/*` solo por extensión (A-7) |
| S-17 | — | **PARCIAL** | |
| S-18 | rotación de clave | **HECHO** | Con salvedad: es manual, y la clave filtrada de C-1 nunca se rotó |
| S-19 | — | **HECHO** | |
| S-20 | política de contraseñas | **PARCIAL** | HIBP no cubre los cambios de contraseña (M-10) |
| S-21 | cuotas | **PARCIAL** | La cuota de OCR está en el endpoint que no se usa (A-6) |
| S-22 | exportación RGPD | **HECHO** | `auth.py:532-635` |
| S-23 | — | **HECHO** | |
| S-25 | cifrado en reposo | **SIN HACER** | (B-12) |
| S-26 | opt-out OCR nube | **PARCIAL** | Esquivable por `/api/ocr/procesar-ticket` (A-7) |

S-02, S-03, S-04, S-09, S-24 dependen del Panel (sección 5) y no son verificables.

---

## 7. Falsos positivos descartados (no tocar)

- **No hay inyección SQL en ninguna parte.** Las 10 alertas B608 de bandit son falsos
  positivos: los fragmentos interpolados son claves de diccionario hardcodeadas o
  `",".join("?" …)`. El `sast-python` en rojo es ruido de configuración.
- `subprocess` se usa correctamente en todos los casos (argumentos en lista, sin
  `shell=True`, rutas de `tempfile`). No hay path traversal, ni `pickle`, ni `eval`,
  ni `render_template_string`.
- **Inyección de cabeceras SMTP**: no explotable. `email.generator` de la stdlib
  rechaza el valor con `HeaderParseError` (verificado).
- **XSS con nombres devueltos por el modelo**: no explotable en el frontend actual.
  React escapa por defecto y el único `dangerouslySetInnerHTML` (`app/layout.tsx:60`)
  tiene contenido estático. Queda latente para consumidores no-React de la API.
- `#nosec` de `password_pwned.py:21` es legítimo (SHA-1 lo exige el protocolo de HIBP,
  y el k-anonymity está bien implementado: solo se envía el prefijo de 5).
- `SMTP_USER=AKIAIOSFODNN7EXAMPLE` en `docs/HISTORICO/SETUP_EMAIL.md:120` es la clave
  de ejemplo de la documentación de AWS. Los valores de `.env.example` son
  placeholders. **No son fugas.** `.env` nunca ha estado en el índice.
- **Escritura de stock entre hogares** vía `producto_id` ajeno en `/confirmar`:
  bloqueada por `sumar_stock` (`stock.py:161-164`). Solo `registrar_precio` inserta
  basura en `historial_precios`, que la lectura filtra por `hogar_id`.

---

## 8. Sospechas no confirmadas (requieren acceso al dispositivo o prueba)

1. **¿La clave filtrada sigue activa en la Pi?** Determina si C-1 es explotable ahora
   mismo. `cat data/secret.json` en la Pi.
2. **¿`gitleaks` habría detectado C-1?** Una cadena de 64 hex en un JSON no encaja en
   las reglas de proveedor conocido y no hay `.gitleaks.toml` propio. Probar:
   `gitleaks detect --log-opts d3cb82d2^..d3cb82d2`. Aparte, `gitleaks-action@v2`
   exige `GITLEAKS_LICENSE` en repos de organización.
3. **¿El rewrite de Next añade su entrada a `X-Forwarded-For` o la reenvía tal cual?**
   Si la reenvía, `request.remote_addr` pasa a ser elegido por el atacante, lo que
   afecta a la excepción de mantenimiento `remote_addr not in ("127.0.0.1","::1")`
   (`__init__.py:183`). Se confirma con un test que mande
   `X-Forwarded-For: 127.0.0.1` a través del frontend.
4. **¿Está el puerto 5000 alcanzable desde fuera de la LAN?** Si sí, M-8 y M-13 pasan
   de Medio a Alto.
5. **Permisos efectivos de `data/`, `logs/` y `data/vapid_private_key.pem` en la Pi.**
   `install.sh:568-570` hace `chown` al usuario del host, no al UID 1000 del
   contenedor: si no coinciden, o `appuser` no puede escribir, o los directorios
   acabaron con permisos amplios para compensarlo.
6. **`limite_por_ip` es un dict en memoria del proceso** (`red.py:19-29`): con
   `--workers 2` el límite real es el doble del declarado. Conviene persistirlo como
   `intentos_login`.
7. **Rama Postgres**: toda la revisión de autorización se hizo sobre el SQL de `db.py`
   (sintaxis SQLite). No se ha auditado si `db_backend.py` reescribe alguna consulta
   de forma que cambie el filtrado por `hogar_id`.
8. **`docker-build.yml` construye y ejecuta Dockerfiles de PRs de forks.** Es
   `pull_request` (sin secretos, token de solo lectura), así que el riesgo es abuso de
   cómputo. Depende del ajuste "Require approval for fork pull requests", que no se ve
   desde el repo.

---

## 9. Impacto en textos legales (REGLA 11)

Los arreglos de A-1, A-7 y M-19 y la auditoría de datos salientes obligan a revisar
`app/legal/privacidad`:

- **No declarado hoy**: que junto a la imagen se envía a Anthropic la lista de nombres
  del inventario; que el PDF viaja íntegro con todas sus páginas y metadatos.
- **Encargados del tratamiento ausentes de la lista**: el proveedor SMTP configurado
  (recibe email destino, nombre de usuario, nombre del hogar, y el código 2FA en el
  asunto), los servicios push del navegador (FCM/Mozilla/Apple, como transporte — hoy
  Google y Apple solo figuran "si inicias sesión con…"), y Have I Been Pwned.
- **Retención de logs**: `logs/stockhogar.log` guarda direcciones de email completas y
  fragmentos de nombres de artículos comprados, y lo lee un proceso externo (B-2). No
  se menciona.

Si se corrige la declaración de terceros, el cambio es sustancial: subir
`VERSION_TERMINOS` en `stockhogar/config.py` para forzar la re-aceptación.

---

## 10. Orden de ejecución propuesto

1. **Hoy**: C-1 completo (rotar, cambiar contraseñas, borrar la rama, arreglar
   `.gitignore`). Es la única cosa que un atacante puede usar **ahora mismo** sin
   ninguna condición previa.
2. **Mismo día, es barato**: A-8 (`.dockerignore`), A-9 (mover los `.env.bak`), A-2
   (borrar `buscar-usuarios`), A-3 (quitar la rama `password`), A-7 (dejar de
   registrar el blueprint `ocr`). Cinco arreglos de pocas líneas que cierran una fuga
   de credenciales, una de datos personales y dos bypasses.
3. **Esta semana**: A-1 (aislamiento del catálogo, el que más superficie cierra), A-6
   (cuota real), A-4 y A-5 (rate limit y 2FA), A-3b (email en el perfil), A-10 y A-11
   (integridad del despliegue y dependencias).
4. **Fase 2**, empezando por ampliar `tests/test_matriz_autorizacion.py` a los 11
   blueprints que hoy no cubre: sin esa red, los arreglos de M-1…M-4 no son
   verificables.
5. **Fase 3** e higiene, con el Panel (sección 5) como decisión aparte: mientras siga
   sin auditarse, S-03 y S-04 son los dos hallazgos más graves del sistema y no están
   en este plan.

Cada fase debe cerrar con la suite completa en verde (`python -m pytest tests/ -q`) y
con test de regresión propio por hallazgo, en particular para A-1, A-3, A-4, A-6 y
A-7, donde los tests actuales pasan en verde sin cubrir el camino real.
