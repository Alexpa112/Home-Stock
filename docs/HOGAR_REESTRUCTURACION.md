# Reestructuracion "Listas" -> "Hogar" (Stock + Lista de la compra)

Objetivo: el concepto "Listas" no tiene sentido para el usuario. El concepto real es
**Hogar**: unidad editable y compartible entre usuarios. Dentro de un Hogar hay dos cosas:
**Stock** (inventario) y **Lista de la compra**.

Decisiones ya validadas con el usuario:
- Menu: "Hogar" pasa a ser una seccion padre con submenu (Stock / Lista de la compra / Compartir).
- Alcance: se renombra tambien en backend/BD (tablas, rutas, mensajes de error), no solo UI/i18n.
- Migracion de BD: NO destructiva. Se crean tablas/columnas nuevas y se copian los datos;
  las tablas viejas (`listas`, `permisos_lista`, `invitaciones_lista`, `articulos_lista`,
  `stock_lista`) se mantienen como backup hasta confirmar que todo funciona en produccion,
  y se eliminan en un punto posterior explicito (punto 8).

Reglas de trabajo (pedidas por el usuario):
- Se avanza punto por punto. Cada punto se verifica (compila / tests pasan) antes de darlo
  por hecho.
- Al terminar un punto: commit en `dev2` + push a `origin/dev2`.
- Este fichero se actualiza tras cada punto completado, para poder retomar el trabajo aunque
  se pierda el contexto de la conversacion (pasar solo este arbol basta para continuar).

Estado global: **EN CURSO** — Puntos 1-7 completados (Punto 5 con pendiente de traduccion en
6 idiomas, ver detalle; delegado como tarea aparte). Siguiente: Punto 8 (limpieza final),
que solo debe hacerse tras validar en produccion con datos reales durante un tiempo — NO
hacerlo todavia sin confirmacion explicita del usuario.

---

## Arbol de desarrollo

### 1. Migracion de base de datos (stockhogar/db.py) — COMPLETADO 2026-07-30
- [x] Migracion anadida al final de `_init_db_impl` (stockhogar/db.py), despues de
      que `articulos_lista` ya tiene su forma final (columna `articulo_personalizado_id`
      incluida) y antes del `DROP TABLE espacios`
- [x] Crear tabla `hogares` (copia de `listas`) + copiar datos
- [x] Crear tabla `permisos_hogar` (copia de `permisos_lista`, FK `hogar_id`) + copiar datos
- [x] Crear tabla `invitaciones_hogar` (copia de `invitaciones_lista`, FK `hogar_id`) + copiar datos
- [x] Crear tabla `articulos_compra` (copia de `articulos_lista`, FK `hogar_id`) + copiar datos
- [x] Crear tabla `stock_hogar` (copia de `stock_lista`, FK `hogar_id`) + copiar datos
- [x] `movimientos_stock`: anadida columna `hogar_id` (via `asegurar_columna`), copiado
      valor de `lista_id`, nuevo indice `idx_movimientos_stock_hogar_fecha`
- [x] Migracion idempotente: usa `INSERT ... WHERE id NOT IN (SELECT id FROM <tabla_nueva>)`,
      igual que el patron `INSERT OR IGNORE` ya usado en el resto del fichero
- [x] Tablas viejas (`listas`, `permisos_lista`, `invitaciones_lista`, `articulos_lista`,
      `stock_lista`) se mantienen intactas, sin DROP ni ALTER
- [x] Verificado: `python -m pytest tests/ -q` -> 66 passed, 1 skipped (corre contra
      `data/stock.db` real, tal como esta configurado el proyecto)
- [x] Verificado contra `data/stock.db` real: recuentos identicos entre tabla vieja y
      nueva (listas=76/hogares=76, permisos_lista=0/permisos_hogar=0,
      invitaciones_lista=1/invitaciones_hogar=1, articulos_lista=4/articulos_compra=4,
      stock_lista=9421/stock_hogar=9421); estable tras multiples arranques de la app
      (create_app se llamo varias veces durante los tests sobre el mismo fichero)
- Nota: no se ha anadido backup automatico separado porque la migracion es aditiva
  (solo CREATE TABLE + INSERT, nunca toca las tablas viejas), asi que el riesgo de
  perdida de datos es minimo; si se quiere backup extra antes de desplegar a
  produccion, hacerlo a nivel de operacion (copiar el fichero .db) antes del deploy.

### 2. Backend Flask — COMPLETADO 2026-07-30 (alcance ampliado a 8 ficheros)
Descubrimiento durante el trabajo: el plan original solo contaba 3 ficheros
(`listas.py`, `articulos_lista.py`, `permisos.py`), pero 8 ficheros de rutas
dependian del modelo antiguo. Se decidio con el usuario ampliar el alcance a
los 8 para no dejar el backend con dos fuentes de verdad divergentes.

- [x] `stockhogar/rutas/listas.py` -> `stockhogar/rutas/hogares.py` (git mv),
      Blueprint `hogares`, prefijo `/api/hogares`
- [x] Alias `/api/listas` registrado en `stockhogar/__init__.py` reutilizando el
      mismo blueprint (`register_blueprint(hogares.bp, name="hogares_alias_legado",
      url_prefix="/api/listas")`) para no romper peticiones de PWA offline en cola
- [x] `stockhogar/rutas/articulos_lista.py` -> `stockhogar/rutas/articulos_compra.py`
      (git mv), Blueprint `articulos_compra`, sigue en `/api/articulos` (sin cambio
      de prefijo, solo de tabla interna: `articulos_lista` -> `articulos_compra`)
- [x] `stockhogar/rutas/permisos.py` — usa `hogares`/`permisos_hogar`/
      `invitaciones_hogar`, prefijo ya era `/api/hogares`
- [x] `stockhogar/servicios/stock.py` — logica central de stock (`sumar_stock`,
      `revisar_stock_bajo`, `registrar_movimiento`, `crear_producto_nuevo`) migrada
      a `stock_hogar`/`articulos_compra`/`hogares`; `lista_actual_con_permiso` ->
      `hogar_actual_con_permiso`
- [x] `stockhogar/rutas/productos.py`, `tickets.py`, `consumo.py`, `historial.py`,
      `auth.py` — actualizados a `hogar_id`/`stock_hogar`/`articulos_compra`/
      `hogares`/`permisos_hogar`
- [x] `session['lista_actual_id']` -> `session['hogar_actual_id']` en todos los sitios
- [x] `stockhogar/utils/converters.py` — sin cambios necesarios (no referenciaba
      nombres de tabla directamente)
- [x] `stockhogar/translations.json` — claves renombradas en los 7 idiomas:
      `recurso_lista`->`recurso_hogar`, `err_no_hay_lista_activa`->
      `err_no_hay_hogar_activo`, `err_sin_permiso_editar_lista`->
      `err_sin_permiso_editar_hogar`, `err_no_salir_propia_lista`->
      `err_no_salir_propio_hogar` (solo las claves; el texto traducido se revisa
      en el Punto 5)
- [x] Corregido un falso positivo del renombrado automatico: la ruta
      `/api/auth/preferencias-listas` (preferencia de vista lista/recuadros de la
      lista de la compra, sin relacion con el hogar como contenedor) se habia
      renombrado por error a `preferencias-hogares`; revertida a su nombre original
- [x] Corregidos 2 mensajes de error en `articulos_compra.py` que el renombrado
      automatico dejo con sentido incorrecto ("en uso en hogares activas" ->
      "en uso en la lista de la compra")
- [x] Tests (`tests/*.py`) actualizados en la misma tanda (se adelanta parte del
      Punto 7 porque los tests insertan datos directamente en las tablas viejas
      via SQL y no podian verificar el Punto 2 sin este cambio): 13 ficheros de
      test migrados a `hogares`/`permisos_hogar`/`articulos_compra`/`stock_hogar`/
      `hogar_actual_id`
- [x] Verificado: `python -m pytest tests/ -q` -> 66 passed, 1 skipped
- Hallazgo aparte (no relacionado con esta tarea, reportado como tarea suelta):
  `tests/test_historial_catalogo.py` no limpia una fila fija de
  `historial_articulos` en tearDown; si la suite corre dos veces seguidas contra
  la BD real sin reiniciarla, falla por UNIQUE constraint. Prexistente, no
  causado por esta migracion.

### 3. Frontend — API y contexto — COMPLETADO 2026-07-30
- [x] `lib/api.ts`: `export const listas` -> `export const hogares`, endpoints
      `/api/listas` -> `/api/hogares` (listar/crear/actualizar/eliminar/seleccionar/
      salir); `permisos` (buscarUsuarios/miembros/compartir/generarEnlace/
      actualizarPermiso/revocar/aceptarInvitacion) tambien apuntan a `/api/hogares`
      (coincide con el prefijo real de `permisos.py`, sin cambios en el backend)
- [x] `contexts/HogarContext.tsx` — import `hogares as hogaresApi`, y
      `data.hogar_actual_id` (antes `data.lista_actual_id`, coincide con la
      respuesta de `GET /api/hogares` tras el Punto 2)
- [x] `components/shared/SelectorHogarPantallaCompleta.tsx` — import actualizado a
      `hogaresApi`
- [x] `app/dashboard/listas/page.tsx` — import actualizado a `hogaresApi` (la
      pagina en si, su ruta `/dashboard/listas` y sus textos `t('...')` se dejan
      para el Punto 4, este cambio es solo para que compile con la nueva API)
- [x] `localStorage`: `CLAVE_LISTA_ACTIVA` -> `CLAVE_HOGAR_ACTIVO`, con migracion de
      la clave vieja (`stockhogar-lista-activa-ui`) una sola vez si no existe la
      nueva, sin desloguear ni perder seleccion en usuarios con la PWA instalada
- [x] `app/aceptar-invitacion/[codigo]/page.tsx` — revisado, no usaba `listasApi`
      directamente (solo `permisos.aceptarInvitacion`), sin cambios necesarios aqui
- [x] Verificado: `npx tsc --noEmit` limpio, sin referencias residuales a
      `listasApi`/`export const listas` en todo el frontend (grep completo)

### 4. Frontend — navegacion y pantallas — COMPLETADO 2026-07-30
- [x] `app/dashboard/layout.tsx`: sidebar desktop rehecho con grupo desplegable
      "Hogar" (boton con chevron, `hogarMenuAbierto` en estado, abierto por defecto)
      que contiene Stock (`/dashboard`), Lista de la compra (`/dashboard/shopping`) y
      Compartir (`/dashboard/hogar`); el resto (Escanear ticket, Historial, Ajustes)
      queda a primer nivel, separado por un divisor
- [x] Bottom tab bar movil: se mantiene Stock y Compra como pestañas directas (un
      toque, convencion de tab bar movil); la pestaña "Listas" se sustituye por
      "Hogar" apuntando a `/dashboard/hogar` (gestion/compartir/cambiar de hogar)
- [x] `app/dashboard/listas/` -> `app/dashboard/hogar/` (git mv), componente
      `ListasPage` -> `GestionHogarPage`, interfaz `Lista` -> `Hogar`
- [x] `app/aceptar-invitacion/[codigo]/page.tsx` — redirect tras aceptar apunta a
      `/dashboard/hogar` (antes `/dashboard/listas`)
- [x] `components/shared/SelectorHogarPantallaCompleta.tsx` — ya actualizado a
      `hogaresApi` en el Punto 3, sin cambios adicionales aqui
- [x] Traducciones: añadidas claves `hogar` y `compartir` (esta ultima ya existia)
      en los 7 idiomas para el nuevo grupo de menu, via insercion quirurgica de texto
      (NO usar `json.load`+`json.dump` en este fichero: el JSON de origen tiene
      claves duplicadas dentro de cada bloque de idioma —p.ej. `cambiar_icono`
      aparece 2 veces por idioma— y un roundtrip por `json` de Python las
      colapsa/pierde silenciosamente; hubo que revertir un primer intento que hizo
      exactamente eso)
- [x] Verificado: `npx tsc --noEmit` limpio, `python -m pytest tests/ -q` -> 66
      passed 1 skipped (backend no tocado en este punto), sin rutas residuales a
      `/dashboard/listas` en todo el frontend
- Pendiente (no bloqueante): no se pudo verificar visualmente en el navegador de
  esta sesion (el servidor de previsualizacion no cargaba, conflicto con otro
  servidor de otra sesion activo en la misma carpeta); revisar a mano en un
  servidor propio antes de subir a `produccion`

### 5. Traducciones (todas las i18n) — COMPLETADO 2026-07-30 (solo texto en español)
- [x] 24 claves renombradas en los 7 bloques de idioma de `stockhogar/translations.json`:
      `mis_listas`->`mis_hogares`, `subtitulo_mis_listas`->`subtitulo_mis_hogares`,
      `compartir_lista`->`compartir_hogar`, `cargando_listas`->`cargando_hogares`,
      `sin_listas_crea_una_nueva`->`sin_hogares_crea_uno_nuevo`,
      `nombre_nueva_lista`->`nombre_nuevo_hogar`, `usar_esta_lista`->`usar_este_hogar`,
      `eliminar_lista`->`eliminar_hogar`, `err_error_al_crear_lista`->
      `err_error_al_crear_hogar`, `err_seleccionar_lista`->`err_seleccionar_hogar`,
      `err_renombrar_lista`->`err_renombrar_hogar`, `err_eliminar_lista`->
      `err_eliminar_hogar`, `err_error_al_salir_lista`->`err_error_al_salir_hogar`,
      `email_asunto_invitacion_lista`->`email_asunto_invitacion_hogar`,
      `email_cuerpo_invitacion_lista`->`email_cuerpo_invitacion_hogar`,
      `whatsapp_mensaje_compartir_lista`->`whatsapp_mensaje_compartir_hogar`,
      `aria_renombrar_lista`->`aria_renombrar_hogar`, `redirigiendo_a_tus_listas`->
      `redirigiendo_a_tu_hogar`, mas correccion de genero gramatical (masculino,
      concuerda con "el hogar"): `propias`->`propios`, `compartidas_conmigo`->
      `compartidos_conmigo`, `compartida_puedes_editar`->`compartido_puedes_editar`,
      `compartida_solo_ver`->`compartido_solo_ver`, `activa`->`activo`,
      `ya_activa`->`ya_activo`
- [x] `app/dashboard/hogar/page.tsx`, `components/shared/SelectorHogarPantallaCompleta.tsx`,
      `app/aceptar-invitacion/[codigo]/page.tsx` — llamadas `t('...')` actualizadas a
      las claves nuevas
- [x] Texto en español (`es`) actualizado para decir "hogar" en vez de "lista" en las
      24 claves (p.ej. `"compartir_hogar": "Compartir hogar"`)
- [ ] **Pendiente**: los 6 idiomas restantes (`gl`, `en`, `pt`, `fr`, `it`, `de`) tienen
      las claves ya renombradas pero el VALOR sigue siendo el texto viejo (equivalente a
      "lista") heredado del renombrado de clave. Reportado como tarea de seguimiento
      aparte (fuera de esta sesion) porque traducir con calidad en 6 idiomas sin
      verificacion nativa no es razonable hacerlo a ciegas en el mismo golpe
- [x] Verificado: JSON valido, `npx tsc --noEmit` limpio, `python -m pytest tests/ -q`
      -> 66 passed, 1 skipped
- Nota tecnica repetida (importante para quien continue): en este fichero, NUNCA usar
  `json.load`+`json.dump` de Python para editarlo -> hay claves duplicadas dentro de
  cada bloque de idioma (p.ej. `cambiar_icono` x2) y el roundtrip las colapsa
  silenciosamente. Usar siempre reemplazo de texto quirurgico (buscar la clave exacta
  con su valor completo y sustituir solo eso)

### 6. Compatibilidad / despliegue — COMPLETADO 2026-07-30 (sin trabajo manual necesario)
- [x] Investigado: NO existe un service worker clasico con lista de URLs cacheadas
      (no hay `navigator.serviceWorker.register` en toda la app). El mecanismo real
      de cache-busting es `lib/useCacheBuster.ts` (activo en `app/RootLayoutClient.tsx`),
      que cada 15s consulta `GET /api/cache-version` (`stockhogar/rutas/version.py`,
      version = mtime de `docker-compose.yml` o, si no existe, de `stockhogar/__init__.py`)
      y si cambia: desregistra cualquier service worker residual, borra TODO
      `caches.keys()` (Cache Storage API) y recarga la pagina
- [x] Como `stockhogar/__init__.py` ya se modifico en el Punto 2, cualquier despliegue
      a produccion (git pull) cambia su mtime automaticamente -> todos los clientes
      conectados detectan la nueva version en <=15s y purgan cache solos, sin
      necesidad de tocar nada mas para este punto
- [x] Regla de memoria confirmada y respetada: NO se ha subido nada a la rama
      `produccion` durante esta tarea; todo el trabajo esta en `dev2`. Solo se debe
      fusionar a `produccion` cuando el usuario lo pida explicitamente, tras revisar
      el cambio funcional completo (incluye el Punto 4 pendiente de verificacion
      visual en movil)

### 7. Tests (tests/) — COMPLETADO 2026-07-30
- [x] Actualizar tests que usan `/api/listas`, tabla `listas`, `lista_actual_id` — hecho
      en el Punto 2 (13 ficheros), no quedaba nada pendiente aqui
- [x] Test de regresion de la migracion (`tests/test_migracion_hogares.py`, nuevo):
      inserta una fila "vieja" directamente en `listas`/`stock_lista`/`articulos_lista`/
      `permisos_lista` con un id explicito muy por encima del maximo actual en ambas
      tablas (evita falsos negativos por desincronizacion de autoincrement entre
      `listas`, congelada desde el Punto 2, y `hogares`, que sigue creciendo), reinicia
      la app (dispara `_init_db_impl` de forma idempotente) y comprueba que aparece la
      fila equivalente en `hogares`/`stock_hogar`/`articulos_compra`/`permisos_hogar`
      con los mismos datos; incluye test de no-duplicacion al reiniciar dos veces
- [x] Verificado que `test_stock_minimo_lista_compra.py` (regla vital, ver memoria)
      sigue en verde con los nombres de tabla nuevos
- [x] Suite completa `python -m pytest tests/ -q` en verde dos veces seguidas sin
      reiniciar la BD entre medias: 71 passed, 1 skipped

### 8. Limpieza final (solo tras validar en produccion con datos reales)
- [ ] Eliminar tablas viejas (`listas`, `permisos_lista`, `invitaciones_lista`,
      `articulos_lista`, `stock_lista`) y el alias `/api/listas`
- [ ] Eliminar columna `lista_id` de `movimientos_stock` si ya no se usa

---

## Log de avance
(añadir una linea por commit con fecha, punto completado y hash)

- 2026-07-30 — Fix suelto previo: logo real del login (`53ddb295`), no forma parte del arbol pero
  quedo commiteado antes de empezar esta tarea.
- 2026-07-30 — Punto 1 completado (migracion BD hogares/permisos_hogar/invitaciones_hogar/
  articulos_compra/stock_hogar/movimientos_stock.hogar_id). Ver hash en el siguiente commit.
- 2026-07-30 — Punto 2 completado (backend Flask, alcance ampliado a 8 ficheros de rutas +
  servicios/stock.py + 13 ficheros de test + translations.json). 66 passed, 1 skipped.
- 2026-07-30 — Punto 3 completado (lib/api.ts, HogarContext, SelectorHogarPantallaCompleta,
  app/dashboard/listas/page.tsx, migracion de localStorage). tsc --noEmit limpio.
- 2026-07-30 — Punto 4 completado (menu Hogar con submenu, app/dashboard/listas ->
  app/dashboard/hogar, redirect de aceptar-invitacion, claves hogar/compartir en 7
  idiomas). tsc --noEmit limpio, 66 passed 1 skipped. Verificacion visual pendiente
  (servidor de preview de esta sesion no cargaba).
- 2026-07-30 — Punto 5 completado con pendiente: 24 claves de traducciones.json
  renombradas en 7 idiomas + texto en espanol corregido; texto de gl/en/pt/fr/it/de
  bajo las claves nuevas sigue siendo el antiguo (traduccion real pendiente, tarea
  de seguimiento creada). tsc --noEmit limpio, 66 passed 1 skipped.
- 2026-07-30 — Punto 6 completado sin cambios de codigo: no hay service worker
  clasico que purgar; el cache-busting existente (useCacheBuster + /api/cache-version
  basado en mtime) ya cubre el caso automaticamente en cualquier despliegue.
- 2026-07-30 — Punto 7 completado: nuevo tests/test_migracion_hogares.py (5 tests) de
  regresion de la migracion aditiva. Suite completa 71 passed, 1 skipped, dos veces
  seguidas sin reiniciar la BD.
