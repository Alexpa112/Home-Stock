#!/bin/bash
################################################################################
# StockHogar - Auto-actualización desde la rama "produccion"
#
# Pensado para lanzarse por cron cada pocos minutos en la Raspberry Pi.
# Comprueba si hay commits nuevos en origin/produccion; si los hay, hace
# `install.sh --update` (que a su vez hace git pull --ff-only y reconstruye).
# No hace nada si no hay cambios, así que es seguro ejecutarlo a menudo.
#
# Instalación (una sola vez, en la Pi):
#   1. git checkout produccion   (el checkout local debe estar en esta rama)
#   2. crontab -e
#      */5 * * * * /ruta/a/StockHogar/scripts/auto_update.sh >> /ruta/a/StockHogar/logs/auto_update.log 2>&1
################################################################################

set -Eeuo pipefail

BRANCH="produccion"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# Flag que activa/desactiva el Panel de Gestión (StockHogar-Panel) desde
# /api/auto-actualizacion. Vive en data/ porque es la carpeta que ambos
# proyectos comparten a nivel de disco (ver panel_servidor/config.py y
# panel_servidor/auto_actualizacion.py del Panel).
PAUSA_FLAG="$REPO_DIR/data/auto_actualizacion_pausada.flag"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

if [[ ! -d .git ]]; then
    echo "[$(ts)] [ERROR] No es un repositorio git; abortando."
    exit 1
fi

if [[ -f "$PAUSA_FLAG" ]]; then
    # Silencioso: pausada es un estado normal (parada técnica en curso), no
    # queremos ensuciar el log en cada ejecución del cron.
    exit 0
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
    echo "[$(ts)] [WARN] El checkout local está en '$CURRENT_BRANCH', no en '$BRANCH'; se omite la comprobación."
    exit 0
fi

# Mismo lock que usa install.sh: si hay una instalación en curso (lanzada a
# mano o desde el panel), su `git pull` puede pisarse con este `git fetch` y
# dejar el repo en un estado ambiguo ("no se puede hacer fast-forward en
# múltiples ramas"). Si está tomado, no es un error: se reintenta en el
# siguiente tick del cron.
LOCK_FILE="$REPO_DIR/.install.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    # Ya hay una instalación en curso; sale sin error para reintentar después.
    exit 0
fi

if ! git fetch origin "$BRANCH" --quiet 2>/tmp/auto_update_fetch_err; then
    echo "[$(ts)] [ERROR] Fallo al hacer git fetch: $(cat /tmp/auto_update_fetch_err)"
    exit 1
fi

LOCAL_REV="$(git rev-parse HEAD)"
REMOTE_REV="$(git rev-parse "origin/$BRANCH")"

if [[ "$LOCAL_REV" == "$REMOTE_REV" ]]; then
    # Mismo commit: el CODIGO no cambia, pero las IMAGENES si pueden haber
    # cambiado. Las publica .github/workflows/docker-publish.yml DESPUES del push
    # (CI + compilacion para ARM tardan ~15-30 min), de modo que una
    # actualizacion disparada nada más el push bajaba la imagen ":latest" antigua,
    # y como el commit ya coincidia, esta rama no volvia a mirar: la Pi se
    # quedaba semanas con una version vieja. Se comprueba el registro en cada
    # pasada (un pull sin novedades solo consulta manifiestos) y, si hay imagen
    # nueva, se recrea el stack con el mismo install.sh --update.
    refrescar_imagenes() {
        local arch; arch="$(uname -m)"
        # docker-publish.yml solo publica linux/arm/v7; en otras arquitecturas se
        # compila en local y no hay nada que descargar.
        [[ "$arch" == armv7l || "$arch" == armv6l ]] || return 0
        command -v docker >/dev/null 2>&1 || return 0
        local imagenes=(ghcr.io/alexpa112/home-stock-backend:latest ghcr.io/alexpa112/home-stock-frontend:latest)
        local antes="" despues="" img
        for img in "${imagenes[@]}"; do
            antes+="$(docker image inspect -f '{{.Id}}' "$img" 2>/dev/null || true) "
        done
        # Sin red o registro caido: no es un error, se reintenta en 5 minutos.
        docker compose pull --quiet >/dev/null 2>&1 || return 0
        for img in "${imagenes[@]}"; do
            despues+="$(docker image inspect -f '{{.Id}}' "$img" 2>/dev/null || true) "
        done
        [[ "$antes" != "$despues" ]] || return 0

        echo "[$(ts)] [INFO] Imágenes nuevas en GHCR para el mismo commit $LOCAL_REV. Recreando contenedores..."
        exec 200>&-   # soltar el lock: install.sh toma el suyo (ver más abajo)
        if ./install.sh --update; then
            echo "[$(ts)] [OK] Contenedores actualizados con las imágenes nuevas."
        else
            echo "[$(ts)] [ERROR] install.sh --update falló al aplicar las imágenes nuevas; revisa install.log."
            exit 1
        fi
    }
    refrescar_imagenes
    exit 0
fi

# Soltamos el lock antes de llamar a install.sh: él toma el suyo propio sobre
# el mismo fichero y, si lo mantuviéramos abierto aquí, se bloquearía a sí
# mismo (flock es sobre el descriptor de fichero, no reentrante entre padre
# e hijo). La ventana entre soltar y que install.sh lo retome es la misma
# carrera de siempre, pero ahora la resuelve install.sh con su propio flock
# en vez de fallar a medio "git pull".
exec 200>&-

echo "[$(ts)] [INFO] Nuevos commits en origin/$BRANCH ($LOCAL_REV -> $REMOTE_REV). Actualizando..."

if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    echo "[$(ts)] [ERROR] Hay cambios locales sin commitear; no se puede actualizar automáticamente. Revísalo a mano."
    exit 1
fi

if ./install.sh --update; then
    echo "[$(ts)] [OK] Actualización completada a $REMOTE_REV."
else
    echo "[$(ts)] [ERROR] install.sh --update falló; revisa install.log."
    exit 1
fi
