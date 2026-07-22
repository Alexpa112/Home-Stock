#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}StockHogar - Verificacion de Instalacion${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

PASSED=0
FAILED=0

# Docker Compose puede estar como plugin v2 ("docker compose") o binario v1
# independiente ("docker-compose"); install.sh detecta esto mismo al instalar,
# así que aquí replicamos la misma lógica para no dar falsos [FAIL] cuando solo
# está disponible el plugin v2 (caso más común hoy en día).
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    COMPOSE="docker compose"
fi

check() {
    local desc=$1
    local cmd=$2

    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} $desc"
        ((PASSED++))
    else
        echo -e "${RED}[FAIL]${NC} $desc"
        ((FAILED++))
    fi
}

echo -e "${BLUE}Verificaciones de Sistema:${NC}"
check "Docker instalado" "command -v docker"
check "Docker Compose instalado" "docker compose version || command -v docker-compose"
check "Archivo docker-compose.yml" "test -f docker-compose.yml"
check "Archivo Dockerfile.raspbian" "test -f Dockerfile.raspbian"
check "Directorio stockhogar" "test -d stockhogar"
check "Directorio data" "test -d data"

echo ""
echo -e "${BLUE}Verificaciones de Docker:${NC}"
check "Demonio Docker activo" "docker ps > /dev/null 2>&1"
check "Imagen construida" "docker images | grep -q stockhogar"
check "Contenedor ejecutando" "docker ps | grep -q stockhogar-app"

echo ""
echo -e "${BLUE}Verificaciones de Aplicacion:${NC}"
check "Puerto 5000 abierto" "curl -s http://localhost:5000 > /dev/null 2>&1"
check "Base de datos existe" "test -f data/stock.db"
check "Python en contenedor" "$COMPOSE exec -T stockhogar python3 --version > /dev/null 2>&1"

echo ""
echo -e "${BLUE}Verificaciones de Dependencias Python:${NC}"
check "Flask instalado" "$COMPOSE exec -T stockhogar python3 -c 'import flask' 2>&1"
check "OpenCV instalado" "$COMPOSE exec -T stockhogar python3 -c 'import cv2' 2>&1"
check "Pytesseract instalado" "$COMPOSE exec -T stockhogar python3 -c 'import pytesseract' 2>&1"
check "Fuzzywuzzy instalado" "$COMPOSE exec -T stockhogar python3 -c 'import fuzzywuzzy' 2>&1"

echo ""
echo -e "${BLUE}Verificaciones de Sistema en Contenedor:${NC}"
check "Tesseract instalado" "$COMPOSE exec -T stockhogar which tesseract > /dev/null 2>&1"
check "Tesseract OCR español" "$COMPOSE exec -T stockhogar tesseract --list-langs 2>/dev/null | grep -q spa"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Resumen:${NC}"
echo -e "${GREEN}[PASADOS: $PASSED]${NC} ${RED}[FALLIDOS: $FAILED]${NC}"

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  TODAS LAS VERIFICACIONES PASARON - LISTO PARA USAR   ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Accede a: ${YELLOW}http://localhost:5000${NC}"
    exit 0
else
    echo -e "${RED}═════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}ADVERTENCIA: Algunas verificaciones fallaron${NC}"
    echo ""
    echo -e "Para ver logs: ${YELLOW}$COMPOSE logs stockhogar${NC}"
    echo -e "Para reiniciar: ${YELLOW}$COMPOSE restart${NC}"
    exit 1
fi
