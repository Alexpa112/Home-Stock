#!/bin/bash
################################################################################
# StockHogar - ¿existen en GHCR las imágenes publicadas para este commit?
#
# Uso: scripts/imagen_publicada.sh <commit-o-etiqueta>
#
# docker-publish.yml etiqueta cada imagen con el commit EXACTO que pasó el CI
# (además de :latest). Desplegar por commit en vez de por :latest ata el código
# y las imágenes a la misma versión (una :latest secuestrada o pisada por un CI
# posterior ya no se cuela en un despliegue verificado) y evita la carrera de
# siempre: el commit llega a produccion ~15-30 min ANTES que sus imágenes.
#
# Salida (código de retorno):
#   0  las dos imágenes existen
#   1  alguna NO existe todavía (aún se está publicando, o este commit no la publica)
#   2  no se puede saber (sin docker, sin red, registro caído, sin `docker manifest`):
#      quien llama debe caer al comportamiento anterior (:latest), nunca bloquear
################################################################################
set -u

ETIQUETA="${1:-}"
[[ -n "$ETIQUETA" ]] || { echo "uso: $0 <commit>" >&2; exit 2; }
# Solo caracteres de una etiqueta/sha: este valor acaba en una referencia de imagen.
[[ "$ETIQUETA" =~ ^[A-Za-z0-9_.-]{1,128}$ ]] || { echo "etiqueta no válida" >&2; exit 2; }
command -v docker >/dev/null 2>&1 || exit 2

DOCKER=(docker)
"${DOCKER[@]}" info >/dev/null 2>&1 || DOCKER=(sudo -n docker)

for IMAGEN in ghcr.io/alexpa112/home-stock-backend ghcr.io/alexpa112/home-stock-frontend; do
    SALIDA="$(timeout 40 "${DOCKER[@]}" manifest inspect "${IMAGEN}:${ETIQUETA}" 2>&1)"
    RC=$?
    if [[ $RC -eq 0 ]]; then
        continue
    fi
    # "manifest unknown" / "no such manifest" = el registro responde y la etiqueta no existe.
    if grep -qiE 'manifest unknown|no such manifest|not found' <<<"$SALIDA"; then
        exit 1
    fi
    exit 2
done
exit 0
