#!/bin/bash
# Envoltorio: el instalador real vive en la raíz del proyecto (../install.sh).
# Se mantiene este fichero por compatibilidad con quien lo invoque desde
# scripts/, pero NO duplica lógica para evitar que ambos scripts se
# desincronicen entre sí.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../install.sh" "$@"
