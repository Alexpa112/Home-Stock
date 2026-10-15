# Plan de revisión y reorganización del código

Estado: en ejecución (ver "Registro de ejecución" al final).
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
