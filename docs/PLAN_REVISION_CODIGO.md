# Plan de revisión y reorganización del código

Estado: fases 1-8 y primera pasada automática de la fase 9 hechas; la revisión manual línea a línea sigue en la sección 6.
Rollback: rama `backup/dev2-produccion-pre-reorganizacion-promo-20261015` (= `produccion` antes de
empezar, `db607776`). Para volver: `git reset --hard origin/backup/dev2-produccion-pre-reorganizacion-promo-20261015`
en la rama que haga falta. Cada fase es un commit propio y se puede revertir sola con `git revert`.

## 0. Reglas de la reorganización

1. **Sin cambios de comportamiento.** Mover, extraer y quitar duplicados; nada de funciones nuevas.
2. **Una fase = un commit = batería completa en verde** (pytest, tsc, eslint, jest, build, bandit).
3. Los movimientos se hacen con `git mv` (se conserva el historial) y se corrigen **todas** las
   referencias (código, tests, Docker, CI, scripts, docs) en el mismo commit.
4. No se dejan ficheros "puente" que reexporten desde la ruta antigua, salvo `__init__.py` de un
   paquete que define su API pública.
5. Codificación y finales de línea de los ficheros existentes no se tocan.

## 1. Diagnóstico (medido)

| Dato | Valor |
|---|---|
| Código de aplicación (py/ts/tsx) | ~37.000 líneas, 142 ficheros |
| Duplicación exacta (jscpd, ≥8 líneas) | 0,8 % (16 clones, 234 líneas) |
| Ficheros > 900 líneas | `db.py` 1.542, `gastos/page.tsx` 1.169, `shopping/page.tsx` 1.132, `parser_mejorado.py` 1.120, `dashboard/page.tsx` 1.095, `auth.py` 1.047, `settings/page.tsx` 1.020, `gastos.py` 982, `config.py` 968 |
| Código muerto confirmado | `components/ui/button.tsx`, `lib/utils.ts`, `hooks/useFetch.ts`, `components.json` (shadcn sin uso) y 8 dependencias npm que solo ellos usan; `babel.cfg`; `server.log` versionado; submódulo `StockHogar-Panel` sin `.gitmodules`; 3 imports y 1 variable sin usar |
| Raíz del repositorio | 25 ficheros/carpetas mezclados (config de build, Docker, scripts, docs) |
| `rutas/` | 21 módulos planos sin agrupar por dominio |
| `scripts/` | 28 ficheros mezclados (instalación, mantenimiento, desarrollo, migraciones de una sola vez) |
| `tests/` | 118 ficheros planos |

Los clones exactos son pocos; el problema real es de **tamaño y mezcla de responsabilidades**
(ficheros monolíticos) más duplicación *semántica* (misma lógica con distinto nombre).

## 2. Árbol objetivo

```
stockhogar/
  __init__.py            # create_app (solo composición)
  nucleo/                # config, db (paquete), seguridad, cifrado, red, autorizacion, translator
  api/                   # APIResponse, decoradores, validación
  rutas/
    cuenta/              # auth, oauth
    hogar/               # hogares, permisos
    inventario/          # productos, categorias, historial, consumo, recetas
    compra/              # articulos_compra
    gastos/              # gastos, categorias_gasto
    escaner/             # tickets, ocr_tickets
    sistema/             # paginas, legal, version, idiomas, formularios, push
  servicios/
    cuenta/              # auditoria, intentos_login, password_pwned, email_service
    notificaciones/      # push_service
    traduccion/          # traductor_argos, traductor_auto, diccionario_gallego
    ocr/ ...             # lector (ya agrupado)
  integraciones/         # ocr_rapid, ticket_ocr
  utils/
scripts/
  instalacion/ mantenimiento/ desarrollo/ i18n/ ci/ pruebas_multiusuario/
docs/                    # vigentes en la raíz; histórico en HISTORICO/
```

Frontend: `app/` (rutas Next), `components/<dominio>/`, `lib/`, `contexts/`, `hooks/` — las páginas de
más de 900 líneas se parten en componentes y hooks por pantalla.

## 3. Fases

| # | Fase | Contenido | Riesgo |
|---|---|---|---|
| 1 | Limpieza | Quitar código muerto, deps npm huérfanas, ficheros versionados por error, imports sin usar | bajo |
| 2 | Duplicación backend | Un solo importador/exportador CSV, un CRUD de categorías, una validación de reparto de gastos, helper de permisos de hogar | medio |
| 3 | Paquete `db` | `db.py` (1.542 líneas) → `db/` con conexión, esquema y migraciones por tema | medio |
| 4 | `rutas/` por dominio | 7 subpaquetes; mismas rutas y endpoints | medio |
| 5 | `servicios/` y núcleo | Agrupar servicios y módulos transversales | medio |
| 6 | Partir ficheros grandes | `auth.py`, `gastos.py`, `parser_mejorado.py` | medio |
| 7 | Frontend | Partir páginas > 900 líneas; extraer lo repetido (formularios de alta, tarjetas, modales) | medio |
| 8 | `scripts/` y `tests/` | Agrupar por finalidad, corregir referencias en Docker/CI/docs | bajo |
| 9 | Revisión línea a línea | Ver sección 4 | — |
| 10 | Batería final | Ver sección 5 | — |

## 4. Revisión línea a línea (checklist por fichero)

Se recorre cada módulo (orden: seguridad → datos → rutas → OCR → frontend) con esta lista; cada
hallazgo se corrige con su test o se anota aquí.

1. **Contrato**: ¿cada ruta valida entrada, comprueba sesión/permiso/hogar y devuelve el formato
   que el frontend espera? (`lib/api.ts` ↔ `url_map`).
2. **Datos**: SQL parametrizado, transacciones cortas (nada lento con la BD bloqueada), índices
   para cada filtro, sin N+1.
3. **Errores**: nada de `except: pass` sin motivo, mensajes traducibles, sin detalles internos al cliente.
4. **Seguridad**: IDOR por hogar, límites de tamaño/cantidad, secretos y PII en logs.
5. **Concurrencia**: lecturas-modificaciones-escrituras atómicas (`UPDATE ... SET x = x + ?`).
6. **Duplicación**: ¿existe ya un helper? (`jscpd` y revisión manual).
7. **Código muerto**: `vulture`/`knip`.
8. **Tipos y nombres**: `tsc` estricto, nombres en español coherentes, docstrings que explican el *porqué*.
9. **Rendimiento**: peticiones del frontend por pantalla, tamaño de respuestas, tiempos del escáner.
10. **Accesibilidad e i18n**: objetivos táctiles 44 px, claves de traducción en 7 idiomas.

## 5. Batería final

- `pytest tests/` completo, `tsc`, `eslint`, `jest`, `npm run build`, `bandit -ll`, `jscpd`, `vulture`, `knip`.
- Escenarios multiusuario (`scripts/pruebas_multiusuario/`): hogar compartido, 30 usuarios, 3 usuarios en navegador, rol de solo lectura.
- Escáner: sintético (216 casos) y recibos reales (100) sin regresión.
- Comprobación de contrato: todas las llamadas de `lib/api.ts` existen en `app.url_map`.
- Arranque en limpio (BD nueva) y sobre BD existente (migraciones idempotentes).

## Registro de ejecución

(se rellena al terminar cada fase)

### Fase 1 — Limpieza (hecha)
- Eliminados `server.log` (versionado pese a estar ignorado), el submódulo huérfano `StockHogar-Panel`, `babel.cfg`,
  `components.json`, `components/ui/button.tsx`, `lib/utils.ts`, `hooks/useFetch.ts` (nadie los importaba).
- 8 dependencias npm sin uso quitadas (`@base-ui/react`, 4 × `@radix-ui/*`, `class-variance-authority`, `clsx`,
  `tailwind-merge`): 913 líneas menos en `package-lock.json`, instalación más ligera en la Raspberry.
- 3 imports sin usar quitados.
- `scripts/i18n/` (22 scripts de migraciones ya aplicadas, uno con ruta de Windows fija) → `docs/HISTORICO/scripts_i18n/`.
- Batería: pytest 855 OK, tsc, eslint, jest 57, build.

### Fase 2 — Duplicación backend (hecha)
- `_validar_reparto()` sustituye 3 copias del reparto de gastos (alta, edición y recurrentes); de paso la edición
  ahora valida que cada participante sea un objeto (antes daba 500 con un participante que no lo fuera).
- `leer_csv_subido()` (utils/csv_seguro.py): lectura del CSV de las dos importaciones.
- `_producto_del_hogar()`: 3 copias de la misma SELECT en `productos.py`.
- `servicios/catalogo_categorias.py`: el CRUD de categorías de producto y de gasto era el mismo código con otra
  tabla; las dos rutas quedan en ~40 líneas cada una.
- `lib/api.ts`: `leerRespuesta()` unifica la interpretación de respuestas (503/401/error) de apiCall, apiUpload y apiDownload.
- 14 imports y variables sin usar quitados (pyflakes).

### Fase 3 — Paquete `stockhogar/db/` (hecha)
`db.py` (1.542 líneas, con una función `_init_db_impl` de 1.170) → paquete:
`conexion.py` (get_db, ahora, utilidades), `esquema/` (7 módulos por tema: base, catalogo, hogares, gastos,
recetas, seguridad, push; se ejecutan en el mismo orden que antes), `migraciones.py`, `iconos.py`,
`inicializacion.py` (init_db con flock). La API pública (`from ..db import get_db, ahora`) no cambia.
Verificación: esquema recreado en BD vacía y migración sobre una BD existente comparados con el código
anterior → **idénticos** (56 tablas/índices, mismas filas sembradas). `tests/conftest.py` parchea ahora solo `config.DB_PATH`.

### Fase 4 — `rutas/` por dominio (hecha)
21 módulos planos → 7 subpaquetes: `cuenta/` (auth, oauth), `hogar/` (hogares, permisos), `inventario/`
(productos, categorias, historial, consumo, recetas), `compra/` (articulos_compra), `finanzas/` (gastos,
categorias_gasto), `escaner/` (tickets, ocr_tickets), `sistema/` (paginas, legal, version, idiomas, formularios, push).
Movido con `git mv` y una herramienta que reescribe imports relativos/absolutos, cadenas de `patch("...")` y rutas en
docs/Docker/CI en una sola pasada. Mismos 122 endpoints; 855 tests en verde.

### Fase 5 — Núcleo y servicios (hecha)
- `nucleo/`: seguridad, cifrado, red, autorizacion (primitivas transversales que antes estaban sueltas en la raíz).
- `servicios/cuenta/` (auditoria, intentos_login, password_pwned, email_service), `servicios/notificaciones/`
  (push_service), `servicios/traduccion/` (traductor_argos, traductor_auto, diccionario_gallego), `servicios/ocr/cuota_ocr.py`.
- `db_backend.py` (Postgres opcional) → `db/backend_postgres.py`.
- `config.py`, `translator.py` y `translations.json` se quedan en la raíz del paquete (los usa casi todo el código y
  el frontend genera `traduccionesBase.ts` desde el JSON).

### Fase 6 (parcial) — `rutas/cuenta/auth.py` (1.047 líneas) partido en 6 módulos (hecha)
`blueprint` (Blueprint + rutas públicas), `comunes` (tokens, validaciones, reautenticación), `sesion`, `doble_factor`,
`perfil`, `credenciales`, `datos_personales` (RGPD). Los nombres compartidos pierden el guion bajo. Se añade
`tests/plataforma/test_mapa_de_rutas.py`, que fija las 122 rutas/endpoints para que ninguna reorganización pueda perder o renombrar una.

### Fase 7 — Frontend (parcial, hecha)
`AvisoError` sustituye 6 copias del banner de error; `ListaSugerencias` las 2 del desplegable de autocompletado;
`lib/tipos.ts` unifica `Categoria`/`ArticuloCatalogo`; `leerRespuesta` en `lib/api.ts`. Quitados 8 imports/variables sin usar
y `BgPattern`, `handlePagarSugerencia` (código muerto). **Pendiente** (ver sección 6): partir en componentes
`gastos/page.tsx`, `shopping/page.tsx`, `dashboard/page.tsx` y `settings/page.tsx` (>1.000 líneas).

### Fase 8 — `scripts/` y `tests/` (hecha)
- `scripts/`: generadores, desarrollo y evaluación en subcarpetas. **Los scripts que invocan el cron de los
  servidores ya instalados (`auto_update.sh`, `enviar_avisos_caducidad.py`), el instalador y el Panel no se mueven**
  (romperían la auto-actualización de las instalaciones existentes); ver `scripts/README.md`.
- `tests/`: 118 ficheros planos → 7 carpetas por área. La suite pasa de ~275 s a ~160 s (un test de traducción
  esperaba a Argos sin red durante 2 minutos; ahora usa un traductor determinista).
- Documentación de estructura: `docs/ESTRUCTURA.md`.

### Fase 9 — Primera pasada automática de la revisión (hecha)
- **Contrato frontend↔backend** (`tests/plataforma/test_contrato_api_frontend.py`): las 108 llamadas distintas del
  frontend existen en el backend con su método. Sale como test permanente.
- **Rutas e imports**: `test_mapa_de_rutas` fija las 122 rutas; `test_imports_relativos` detecta imports rotos tras mover
  ficheros (halló un `from .diccionario import ...` dentro de una función que dejaba de funcionar en silencio al mover el parser).
- **Código muerto/limpio**: ruff/pyflakes/vulture/knip. Quitados imports sin usar (≈30), dos claves duplicadas, un parámetro sin
  uso, `StatsCard.tsx`, `components.json` (y su `COPY` en `Dockerfile.frontend`, que habría roto el build de la imagen del frontend).
- **Duplicación exacta (jscpd)**: de 0,80 % (16 clones, 234 líneas) a 0,36 % (8 clones, 103 líneas).
- **Verificaciones de equivalencia**: esquema SQL idéntico en BD vacía y en BD existente; lector idéntico (sintético 216 casos y
  100 recibos reales); build del frontend desde un contexto limpio con solo los ficheros que copia el Dockerfile.

## 6. Pendiente (revisión manual línea a línea)
Se hace por módulos con la checklist de la sección 4; cada módulo sale con tests o con nota aquí.

| Prioridad | Módulo | Qué mirar |
|---|---|---|
| 1 | `rutas/cuenta/perfil.py::actualizar_perfil` (100 líneas) | partir en validar / aplicar; ya mezcla usuario, nombre y email con reautenticación |
| 1 | `rutas/escaner/tickets.py` (556) | `analizar_ticket` es una función de ~200 líneas (archivo, cuota, motores, respuesta): extraer pasos |
| 2 | Páginas > 1.000 líneas (`gastos`, `shopping`, `dashboard`, `settings`) | extraer componentes y hooks por sección; dejar cada página < 400 líneas |
| 2 | `servicios/ocr/claude_ocr.py` (726) | separar prompt/esquema, normalización y cliente (hoy tests tocan sus internos) |
| 3 | `config.py` (968) | agrupar constantes por tema (paquete `config/`) |
| 3 | Endpoints sin uso en el frontend actual | `/api/formularios/crear-lista`, `/api/auth/teclado-virtual`, `/api/productos/traducir`, `/api/idiomas/traducir`, `/api/usuarios`, alias `/api/listas/*` (PWA antigua): decidir retirar o documentar |
| 3 | 86 avisos de eslint (58 `any`, hooks) | tipar las respuestas de `lib/api.ts` |
