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

Estado global: **EN CURSO** — ver progreso por punto abajo.

---

## Arbol de desarrollo

### 1. Migracion de base de datos (stockhogar/db.py)
- [ ] Nueva migracion versionada (patron incremental ya existente en `_init_db_impl`)
- [ ] Crear tabla `hogares` (copia de `listas`) + copiar datos
- [ ] Crear tabla `permisos_hogar` (copia de `permisos_lista`, FK `hogar_id`) + copiar datos
- [ ] Crear tabla `invitaciones_hogar` (copia de `invitaciones_lista`, FK `hogar_id`) + copiar datos
- [ ] Crear tabla `articulos_compra` (copia de `articulos_lista`, FK `hogar_id`) + copiar datos
- [ ] Crear tabla `stock_hogar` (copia de `stock_lista`, FK `hogar_id`) + copiar datos
- [ ] `movimientos_stock`: anadir columna `hogar_id`, copiar valor de `lista_id`
- [ ] Migracion idempotente (comprobar si `hogares` ya existe antes de repetir)
- [ ] Backup automatico antes de aplicar (patron ya usado en el proyecto)
- [ ] Tablas viejas (`listas`, etc.) se mantienen sin tocar por ahora
- [ ] Verificar: tests de BD pasan, migracion se puede ejecutar dos veces sin error

### 2. Backend Flask
- [ ] `stockhogar/rutas/listas.py` -> `stockhogar/rutas/hogares.py`, prefijo `/api/hogares`
      (mantener alias `/api/listas` temporalmente por PWA offline con peticiones en cola)
- [ ] `stockhogar/rutas/articulos_lista.py` -> `stockhogar/rutas/articulos_compra.py`,
      prefijo `/api/hogares/<id>/compra`
- [ ] `stockhogar/rutas/permisos.py` — renombrar funciones/claves de error
      (`err_no_salir_propia_lista` -> `err_no_salir_propio_hogar`, etc.)
- [ ] `session['lista_actual_id']` -> `session['hogar_actual_id']`
- [ ] `stockhogar/i18n.py` — claves de error/mensajes que se refieran al hogar
- [ ] Verificar: `python -m pytest tests/ -q` pasa completo

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
