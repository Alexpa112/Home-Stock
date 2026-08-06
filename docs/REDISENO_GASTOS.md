# 🧾 Rediseño del front de Gastos compartidos

**Estado:** implementado (8 fases) · **Rama:** `dev2` · **Fecha:** 2026-08-05
**Alcance:** `app/dashboard/gastos/page.tsx` (770 líneas, todo en un fichero) y componentes nuevos asociados.
**Referencia visual:** Tricount / Splitwise, adaptado a los tokens y componentes ya existentes en el proyecto.

> **Nota de integración (2026-08-05):** entre la aprobación de este plan y su
> implementación, otra sesión añadió en paralelo, directamente sobre el
> monolito de `page.tsx`: gastos recurrentes, foto de recibo, filtros
> (fecha/categoría/miembro), reparto por partes (4º modo) y un sistema propio
> de sugerencias de pago + historial de liquidaciones (`GET /api/gastos/simplificar`,
> `GET`/`DELETE /api/gastos/liquidaciones`). Este documento se rehízo sobre
> esa base: se **reutilizan** esos endpoints en vez de duplicarlos (por eso
> `lib/gastosStats.ts` ya no tiene `simplificarDeudas` — el backend lo
> resuelve mejor, con un heap) y se conservan íntegras esas funciones
> (recurrentes, recibo, filtros, partes), solo con el envoltorio visual de
> las opciones aprobadas más abajo.

---

## 1. Punto de partida y carencias detectadas

| # | Carencia actual | Consecuencia |
|---|---|---|
| 1 | La tarjeta «Saldo neto» lista a todos los miembros por igual, sin distinguir al usuario | No se responde de un vistazo a «¿debo o me deben?» |
| 2 | La tarjeta de gasto no muestra la fecha | El backend la guarda y ordena por ella, pero no se ve |
| 3 | El alta no envía `fecha`; siempre es hoy | Imposible apuntar un gasto de ayer |
| 4 | La tarjeta no muestra la parte que te toca | El dato ya viene en `participantes[]`, se descarta |
| 5 | Lista plana, sin agrupar ni subtotales | Ilegible pasados ~30 gastos |
| 6 | Lápiz + papelera fijos en cada tarjeta, con confirmación «¿Sí/No?» en línea | Ruido visual y ancho perdido en móvil |
| 7 | Tres botones apretados en la cabecera (Exportar / Registrar pago / Nuevo gasto) | En móvil pierden el texto y compiten entre sí |
| 8 | «Registrar pago» pide origen y destino con etiquetas `Pagado por` / `Le deben` | Semántica confusa; el usuario decide a mano quién paga a quién |
| 9 | No hay cálculo de deudas simplificadas | El usuario tiene que resolver los pagos mentalmente |
| 10 | La gestión de categorías está incrustada dentro del formulario de alta | Formulario con scroll dentro de un modal ya limitado en altura |
| 11 | Las liquidaciones se guardan pero no se listan ni se pueden deshacer | Un pago mal registrado es irreparable desde la UI |
| 12 | El estado vacío es un párrafo gris sin salida a la acción | El usuario busca el botón |

Lo que **sí** está bien y se conserva: caché optimista (`dataCache`), `usePollingRefresh` con suspensión durante la edición, `SkeletonCards`, `formatImporte` con el símbolo del hogar, agregaciones puras en `lib/gastosStats.ts`, exportación CSV y el modelo de datos del backend (no se toca esquema).

---

## 2. Decisiones visuales aprobadas

Elegidas por el usuario sobre el catálogo de opciones renderizado.

| Bloque | Opción | Decisión |
|---|---|---|
| 1. Resumen de balance | **1A** | *Hero personal*: «Tu balance» con cifra grande en verde/rojo, desglose por persona en chips y un único CTA «Liquidar cuentas» |
| 2. Navegación de vistas | **2A** | *Segmented control* de 3 posiciones a ancho completo: Gastos · Balances · Resumen |
| 3. Tarjeta de gasto | **3C** | *Densa con chips*: título + importe grande en la primera línea; categoría, pagador y fecha como chips en la segunda |
| 4. Orden de la lista | **4A** | Cabecera de mes *sticky* con subtotal del mes |
| 5. Acciones sobre un gasto | **5A** | Pulsar la tarjeta abre el *detalle* con el reparto real y los botones Editar / Eliminar |
| 6. Acceso a nuevo gasto | **6A** | *FAB* «+» flotante; Exportar CSV y Registrar pago pasan a un menú «⋯» en la cabecera |
| 7. Formulario de alta | **7A** | *Hoja a pantalla completa*: importe protagonista, categoría en chips, sin scroll anidado |
| 8. Reparto | **8B** | *Filas con interruptor*: una fila por miembro con avatar, nombre e importe; los excluidos al 45 % |
| 9. Balances y liquidación | **9A** | *Deudas simplificadas*: «X paga a Y — importe» con botón «Saldar» que prerrellena el pago |
| 10. Resumen | **10A** | Dos KPIs (gasto del mes con % vs mes anterior, tu parte) + los gráficos actuales |
| 11. Categorías | **11A** | Icono dentro de un cuadro de color determinista por nombre de categoría |
| 12. Estado vacío | **12A** | Icono + titular + frase de valor + CTA «Añadir gasto» |

**Consecuencias de estas elecciones**

- **8B** no introduce lógica de reparto nueva: se conservan los tres modos actuales (`igual`, `porcentaje`, `personalizado`). Se descarta el modo «partes/shares» (8C).
- **3C** + **11A** implican que la tarjeta muestra categoría con nombre; se reutiliza el criterio de color de `CategoryBadge` (`hashIndex`) para que una categoría tenga el mismo color en toda la app.
- **5A** elimina los botones por tarjeta: el borrado deja de ser un «¿Sí/No?» en línea y pasa a confirmarse dentro del detalle.
- **9A** requiere un algoritmo de simplificación de deudas en cliente (a partir del saldo que ya devuelve el backend).
- **1A**, **3C** y **9A** necesitan saber **quién es el usuario actual**: ver Fase 0.

---

## 3. Alcance añadido (a validar)

| Tema | Coste | Propuesta |
|---|---|---|
| **Fecha editable en el alta** | Bajo. El backend ya acepta `fecha` en POST y PATCH; solo falta el campo en el formulario | **Dentro** del rediseño (Fase 3). Sin ella, 4A agrupa por mes con todos los gastos en el mes en curso |
| **Listado / deshacer liquidaciones** | Medio. Requiere `GET /api/gastos/liquidaciones` y `DELETE /api/gastos/liquidaciones/<id>` nuevos, con permisos y tests de backend | **Fase 7, separada y opcional.** No bloquea nada de lo anterior |

---

## 4. Arquitectura propuesta

`page.tsx` pasa de 770 líneas monolíticas a un contenedor de estado + componentes presentacionales, siguiendo el patrón ya usado en el dashboard.

```
app/dashboard/gastos/page.tsx          orquesta datos, caché, polling y modales (~250 líneas)

components/dashboard/gastos/
  BalanceHero.tsx          1A  — «Tu balance» + chips por persona + CTA
  GastoCard.tsx            3C  — tarjeta densa con chips
  GastoDetalle.tsx         5A  — detalle en Modal: reparto + editar/eliminar
  ListaGastos.tsx          4A  — agrupación por mes con cabecera sticky y subtotal
  FormularioGasto.tsx      7A  — hoja a pantalla completa (alta y edición)
  RepartoParticipantes.tsx 8B  — filas con interruptor + modos igual/%/importes
  BalancesPanel.tsx        9A  — deudas simplificadas + «Saldar»
  ResumenPanel.tsx        10A  — KPIs + BarraHorizontal/GraficoColumnas actuales
  CategoriaIcono.tsx      11A  — icono en cuadro de color determinista
  GastosVacio.tsx         12A  — estado vacío con CTA

components/dashboard/HojaCompleta.tsx   contenedor a pantalla completa (hermano de Modal,
                                        misma suspensión de refrescos)

lib/gastosStats.ts        + simplificarDeudas(saldo)  → [{ de, para, importe }]
                          + totalMes(gastos, ym), variacionMensual(gastos)
                          + agruparPorMes(gastos)     → [{ ym, etiqueta, total, gastos }]
                          + parteDeUsuario(gasto, usuarioId)
```

Reutilizaciones explícitas (no se duplica nada): `Modal`, `IconRenderer`, `IconPicker`, `SkeletonCards`, `BarraHorizontal`, `GraficoColumnas`, `CategoryBadge`/`hashIndex`, `formatImporte`, `dataCache`, `usePollingRefresh`, `editSuspension`.

**Gestión de categorías de gasto:** sale del formulario de alta y se mueve a la pantalla de ajustes, donde ya vive la gestión equivalente de otras entidades. En el formulario queda solo un chip «+» que abre esa gestión.

---

## 5. Plan de implementación por fases

Cada fase es un commit coherente en `dev2`, con la suite de tests verde antes de pasar a la siguiente.

### Fase 0 — Identidad del usuario actual (habilitador)
- `GET /api/auth/estado` devuelve además `usuario_id` (hoy solo devuelve `usuario`, el nombre).
- El front lo consume para resolver «Tú» en 1A / 3C / 9A sin comparar por nombre.
- Test: `tests/test_auth_estado_usuario_id.py`.

### Fase 1 — Utilidades puras y color de categoría
- `lib/gastosStats.ts`: `simplificarDeudas`, `agruparPorMes`, `totalMes`, `variacionMensual`, `parteDeUsuario`.
- `CategoriaIcono.tsx` reutilizando `hashIndex`.
- Sin cambios de UI todavía → riesgo cero.

### Fase 2 — Lista, tarjeta y navegación (2A · 3C · 4A · 11A · 12A)
- Segmented control de 3 vistas, tarjeta densa, agrupación por mes con sticky, estado vacío con CTA.
- La lista pierde los botones lápiz/papelera (preparando 5A).

### Fase 3 — Alta y edición (7A · 8B · fecha editable)
- `HojaCompleta.tsx` + `FormularioGasto.tsx` + `RepartoParticipantes.tsx`.
- Campo fecha (por defecto hoy) enviado en POST/PATCH.
- Validación en vivo de que el reparto cuadra con el importe total (la tolerancia del backend es 0,01).
- La gestión de categorías de gasto se traslada a ajustes.

### Fase 4 — Detalle del gasto (5A)
- `GastoDetalle.tsx` con reparto por participante y confirmación de borrado explícita.

### Fase 5 — Balance y liquidación (1A · 9A · 6A)
- `BalanceHero.tsx`, `BalancesPanel.tsx` con «Saldar» prerrellenado.
- FAB + menú «⋯» en cabecera (Exportar CSV, Registrar pago).

### Fase 6 — Resumen (10A)
- KPIs sobre los gráficos existentes.

### Fase 7 — Liquidaciones listables y reversibles *(opcional, a confirmar)*
- `GET /api/gastos/liquidaciones` y `DELETE /api/gastos/liquidaciones/<id>` con nivel `editar`.
- Historial de pagos dentro de la vista Balances.
- Tests de backend de permisos y de recálculo del saldo tras deshacer.

---

## 6. Traducciones

Las claves nuevas se añaden a `stockhogar/translations.json` en los **7 idiomas** (es, gl, en, pt, fr, it, de) siguiendo el patrón de `scripts/i18n/merge_gastos_keys.py`.

Claves previstas: `tu_balance`, `te_deben_total`, `debes_total`, `estas_en_paz`, `liquidar_cuentas`, `saldar`, `paga_a`, `balances`, `resumen`, `entre_n`, `pagaste_tu`, `te_toca`, `prestaste`, `total_mes`, `tu_parte`, `vs_mes_anterior`, `sin_gastos_cta`, `anadir_gasto`, `reparto_cuadra`, `reparto_no_cuadra`, `fecha_gasto`, `excluido`, `detalle_gasto`, `historial_pagos` *(Fase 7)*.

---

## 7. Tests (REGLA 10)

| Fase | Tests |
|---|---|
| 0 | `tests/test_auth_estado_usuario_id.py` |
| 1 | `__tests__/gastosStats.test.js`: simplificación de deudas (caso circular A→B→C, saldos que no cuadran por redondeo, hogar en paz), agrupación por mes con meses vacíos, variación mensual sin mes anterior |
| 3 | `tests/test_gastos.py` ampliado: alta con `fecha` explícita y edición de la fecha |
| 7 | `tests/test_liquidaciones.py`: listado, borrado, permisos (`ver` no puede borrar), saldo recalculado |

Verificación final: `python -m pytest tests/ -q` y `npm test` en verde, más comprobación visual de la pantalla en claro y oscuro a 375 px y en escritorio.

---

## 8. Impacto legal (REGLA 11)

Ninguno: no se tratan datos personales nuevos, no entran terceros ni cookies nuevas y no cambia el titular ni el dominio. Todos los datos mostrados (nombres de miembros, importes) ya se tratan hoy en esta misma pantalla. **No procede subir `VERSION_TERMINOS`.**

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Refactor grande de `page.tsx` rompe caché o polling | Se conservan tal cual `CACHE_KEY_*`, `usePollingRefresh` y la suspensión por edición; las fases 2–6 no tocan la capa de datos |
| `HojaCompleta` tapada por la barra inferior en móvil (ya ocurrió con `Modal`) | Reutiliza las mismas variables (`--mobile-toolbar-h`, `100dvh`) y el `z-[60]` de `Modal` |
| Deudas simplificadas que no cuadran por redondeo | Redondeo a 2 decimales con residuo asignado al último pago; cubierto por test |
| Mover la gestión de categorías a ajustes «esconde» una función usada | Chip «+» en el formulario que lleva directo a esa gestión |
| Regresión en la lista de la compra por tocar `hashIndex`/`CategoryBadge` | Solo se importa, no se modifica |
