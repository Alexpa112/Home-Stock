# Estructura del proyecto

Un único repositorio con backend Flask (`stockhogar/`) y frontend Next.js (`app/`, `components/`, `lib/`).
Cada carpeta agrupa por **tema**, no por tipo de fichero.

```
stockhogar/                       backend (Flask + SQLite)
  __init__.py                     create_app(): solo composición (blueprints, cabeceras, mantenimiento)
  config.py  translator.py  translations.json      configuración y textos de interfaz (7 idiomas)
  nucleo/                         primitivas transversales: seguridad (claves), cifrado en reposo, red (IP real,
                                  límites), autorizacion
  api/                            APIResponse, decoradores (requerir_sesion, manejo_errores), cuerpo_json
  db/                             conexion.py (get_db), esquema/ (tablas por tema), migraciones.py, iconos.py,
                                  inicializacion.py (init_db), backend_postgres.py (opcional)
  rutas/                          endpoints, un subpaquete por dominio (comparten Blueprint dentro de cada uno)
    cuenta/      sesion, doble_factor, perfil, credenciales, datos_personales (RGPD), oauth, comunes
    hogar/       hogares, permisos (compartir, invitaciones, roles)
    inventario/  productos, categorias, historial (catálogo por hogar), consumo, recetas
    compra/      lista, importacion (CSV), personalizados
    finanzas/    registro_gastos, saldos, recibos, recurrentes, categorias_gasto, comunes
    escaner/     tickets (analizar/confirmar), ocr_tickets (diagnóstico)
    sistema/     paginas, legal, version, idiomas, formularios, push
  servicios/                      lógica de negocio reutilizable
    cuenta/ notificaciones/ traduccion/   auditoría, intentos de login, push, traductores
    ocr/                          lector de tickets
      parser/                     ParserMejorado en módulos (secciones, líneas, cantidades, nombres, patrones)
      diccionario/                identificación de artículos (curado + Open Food Facts)
      ...                         cuadre con el total, procesado de imagen, matcher, cliente de Claude Vision
    stock.py  catalogo_categorias.py  mantenimiento.py
  integraciones/                  motores de OCR (RapidOCR neuronal y Tesseract)
  utils/                          validación, conversores, imágenes, CSV seguro

app/  components/  contexts/  hooks/  lib/    frontend Next.js (pantallas, componentes por dominio, API cliente)
  lib/api.ts                      un objeto por dominio; leerRespuesta() unifica errores/sesión/mantenimiento
  lib/tipos.ts                    tipos compartidos entre pantallas
  components/shared|dashboard|legal   piezas reutilizables (AvisoError, ListaSugerencias, selector de hogar...)

tests/                            pytest, agrupado por área (mismas carpetas que describe esta lista)
  escaner/ seguridad/ hogares/ inventario/ gastos/ frontend/ plataforma/   + datos/ datos_ocr/ fixtures/
scripts/                          ver scripts/README.md (operativos que invoca el cron: no se mueven)
docs/                             documentación vigente; docs/HISTORICO/ conserva lo antiguo
```

## Reglas para añadir código

1. Un endpoint nuevo va en el subpaquete de su dominio y **reutiliza** `comunes.py` de ese paquete antes de
   escribir otra validación.
2. Lo que usen dos dominios sube a `servicios/` o `utils/`; nunca se copia.
3. Si mueves un fichero: `git mv`, corrige imports **y** los `patch("...")` de los tests, y ejecuta
   `tests/plataforma/test_mapa_de_rutas.py` y `test_imports_relativos.py`.
4. Las rutas de `scripts/` que usa el cron de los servidores ya instalados no se cambian.
