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

Estado global: **EN CURSO** — Puntos 1 y 2 completados, siguiente: Punto 3 (frontend API/contexto).

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

### 3. Frontend — API y contexto
- [ ] `lib/api.ts`: `listasApi` -> `hogaresApi`, apuntando a `/api/hogares`
- [ ] `contexts/HogarContext.tsx` — actualizar llamadas internas a la nueva API
- [ ] `localStorage`: `CLAVE_LISTA_ACTIVA` -> `CLAVE_HOGAR_ACTIVO` (migrar clave vieja una vez,
      sin desloguear usuarios con PWA instalada)
- [ ] Verificar: `npx tsc --noEmit` limpio

### 4. Frontend — navegacion y pantallas
- [ ] `app/dashboard/layout.tsx`: menu "Hogar" como padre con submenu (Stock / Lista de la
      compra / Compartir)
- [ ] `app/dashboard/listas/` -> `app/dashboard/hogar/` (pagina de gestion: crear/renombrar/
      eliminar/seleccionar hogar), interfaz `Lista` -> `Hogar`
- [ ] Mover/organizar `app/dashboard/stock/` y `app/dashboard/shopping/` bajo el submenu
      "Hogar" (decidir si cambian de URL o solo de posicion en el menu)
- [ ] `app/aceptar-invitacion/[codigo]/page.tsx` — textos/llamadas a la nueva API
- [ ] `components/shared/SelectorHogarPantallaCompleta.tsx` — actualizar llamadas a `hogaresApi`
- [ ] Verificar: `npx tsc --noEmit` limpio + prueba manual en navegador (crear hogar, compartir,
      aceptar invitacion, cambiar hogar activo, ver stock y compra del hogar correcto)

### 5. Traducciones (todas las i18n)
- [ ] `listas`/`mis_listas`/`compartir_lista`/`lista_actual` -> `hogar`/`mi_hogar`/
      `mis_hogares`/`compartir_hogar`/`hogar_actual` en todos los idiomas soportados
- [ ] Verificar: no quedan claves huerfanas ni textos "lista" referidos al hogar

### 6. Compatibilidad / despliegue
- [ ] Service worker / PWA offline: purgar cache de endpoints `/api/listas` viejos tras el
      despliegue
- [ ] Seguir regla de memoria: solo subir a rama `produccion` cuando el cambio funcional este
      completo y probado en movil

### 7. Tests (tests/)
- [ ] Actualizar tests que usan `/api/listas`, tabla `listas`, `lista_actual_id`
- [ ] Test de regresion de la migracion: BD vieja con datos reales -> tras migrar, `hogares`/
      `stock_hogar`/`articulos_compra` tienen los mismos datos con las FKs correctas
- [ ] Verificar que `test_stock_minimo_lista_compra.py` (regla vital) sigue pasando con los
      nuevos nombres de tabla
- [ ] Verificar: suite completa `python -m pytest tests/ -q` en verde

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
