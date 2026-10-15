# scripts/

| Carpeta / fichero | Para qué sirve |
|---|---|
| `auto_update.sh`, `enviar_avisos_caducidad.py`, `maintenance.sh`, `verify.sh`, `docker_cache_prune.sh`, `install.sh` (envoltorio) | **Operativos.** Los invocan el cron de los servidores ya instalados, el instalador y el Panel de Gestión **por esta ruta**: no se mueven ni se renombran. |
| `setup_ocr.py`, `migrar_a_postgres.py` | Utilidades de instalación/migración que se lanzan a mano. |
| `generadores/` | Regeneran ficheros derivados: diccionario de Open Food Facts, `lib/traduccionesBase.ts`, iconos, logos y el GIF de mantenimiento. |
| `desarrollo/` | Ejecutar la batería de pruebas y promover `dev2` → `produccion`. |
| `evaluacion/` | Medir el lector de tickets con recibos reales. |
| `ci/` | Lanzador de pytest que usa GitHub Actions. |
| `pruebas_multiusuario/` | Escenarios con varios usuarios a la vez (API y navegador). |
