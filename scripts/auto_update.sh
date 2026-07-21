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

if ! git fetch origin "$BRANCH" --quiet 2>/tmp/auto_update_fetch_err; then
    echo "[$(ts)] [ERROR] Fallo al hacer git fetch: $(cat /tmp/auto_update_fetch_err)"
    exit 1
fi

LOCAL_REV="$(git rev-parse HEAD)"
REMOTE_REV="$(git rev-parse "origin/$BRANCH")"

if [[ "$LOCAL_REV" == "$REMOTE_REV" ]]; then
    # Sin cambios; no se escribe nada para no ensuciar el log en cada ejecución.
    exit 0
fi

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
