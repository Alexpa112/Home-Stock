#!/bin/bash
################################################################################
# StockHogar - Purga acotada de la cache de build de Docker
#
# Pensado para cron, una vez al dia. Borra SOLO cache de build de mas de 96h
# (4 dias) y capas de imagen sin usar (dangling); nunca toca imagenes
# etiquetadas (incluidas las ":rollback" que usa install.sh para el rollback
# automatico). Esto evita que la cache crezca sin limite durante meses, sin
# caer en el otro extremo: un `docker system prune` a saco vacia TODA la
# cache de golpe y fuerza que el siguiente build sea desde cero (en esta Pi,
# recompilar el backend en frio puede tardar 45-60+ min en vez de 2-3 min).
################################################################################

set -Eeuo pipefail

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] [INFO] Purga de cache de Docker (>96h)..."
docker builder prune -f --filter until=96h
docker image prune -f
echo "[$(ts)] [OK] Purga completada."
