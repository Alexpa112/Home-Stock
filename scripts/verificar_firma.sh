#!/bin/bash
################################################################################
# StockHogar - Verifica la firma del commit que se va a desplegar (opt-in)
#
# Uso: scripts/verificar_firma.sh [referencia]      (por defecto origin/produccion)
#
# La Pi se actualiza sola desde la rama `produccion` y ejecuta lo que llegue
# (install.sh --update, como un usuario del grupo docker = root en la práctica).
# Quien robase un token de GitHub, o consiguiera empujar a esa rama, tendría
# ejecución de código en todas las Pi a los pocos minutos. Con la verificación
# activada, un commit que no esté firmado por una clave de confianza NO se despliega.
#
# Activación: crear el fichero de firmantes permitidos (formato de
# `ssh-keygen -Y verify`) en uno de estos sitios, FUERA del repositorio y del
# volumen data/ (a los que puede escribir el contenedor):
#   /etc/dreame/allowed_signers          (recomendado: solo escribe root)
#   ~/.config/dreame/allowed_signers
#   o la ruta que diga DREAME_ALLOWED_SIGNERS
# Ejemplo (una línea por clave de quien firma los commits):
#   alejandro.paz@edisa.com ssh-ed25519 AAAAC3Nza...
# y en el equipo de desarrollo: git config gpg.format ssh;
#   git config user.signingkey ~/.ssh/id_ed25519.pub; git config commit.gpgsign true
# (los merges que hace la web de GitHub los firma GitHub, no tú: haz los merges a
# `produccion` en local con commit firmado).
#
# Sin ese fichero no se verifica nada (el comportamiento de siempre).
#
# Salida: 0 = verificado, o verificación no activada; 1 = firma ausente o inválida.
################################################################################
set -u

REF="${1:-origin/produccion}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

FIRMANTES=""
for CANDIDATO in "${DREAME_ALLOWED_SIGNERS:-}" /etc/dreame/allowed_signers "${HOME:-/nonexistent}/.config/dreame/allowed_signers"; do
    if [[ -n "$CANDIDATO" && -s "$CANDIDATO" ]]; then FIRMANTES="$CANDIDATO"; break; fi
done

if [[ -z "$FIRMANTES" ]]; then
    exit 0
fi

# Un fichero de firmantes escribible por otros anularía el propósito: cualquiera podría añadir su clave.
if [[ -n "$(find "$FIRMANTES" -perm /022 2>/dev/null)" ]]; then
    echo "[ERROR] $FIRMANTES es escribible por otros usuarios: no es de fiar. chmod 644 y propietario root." >&2
    exit 1
fi

cd "$REPO_DIR" || exit 1
if git -c gpg.format=ssh -c "gpg.ssh.allowedSignersFile=$FIRMANTES" verify-commit "$REF" >/dev/null 2>&1; then
    exit 0
fi

echo "[ERROR] El commit $(git rev-parse --short "$REF" 2>/dev/null) de $REF NO tiene una firma válida de un firmante de $FIRMANTES: no se despliega." >&2
exit 1
