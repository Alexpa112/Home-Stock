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
check "Docker Compose instalado" "command -v docker-compose"
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
check "Base de datos existe" "test -f data/stockhogar.db"
check "Python en contenedor" "docker-compose exec stockhogar python3 --version > /dev/null 2>&1"

echo ""
echo -e "${BLUE}Verificaciones de Dependencias Python:${NC}"
check "Flask instalado" "docker-compose exec stockhogar python3 -c 'import flask' 2>&1"
check "OpenCV instalado" "docker-compose exec stockhogar python3 -c 'import cv2' 2>&1"
check "Pytesseract instalado" "docker-compose exec stockhogar python3 -c 'import pytesseract' 2>&1"
check "Fuzzywuzzy instalado" "docker-compose exec stockhogar python3 -c 'import fuzzywuzzy' 2>&1"

echo ""
echo -e "${BLUE}Verificaciones de Sistema en Contenedor:${NC}"
check "Tesseract instalado" "docker-compose exec stockhogar which tesseract > /dev/null 2>&1"
check "Tesseract OCR español" "docker-compose exec stockhogar tesseract --list-langs 2>/dev/null | grep -q spa"

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
    echo -e "Para ver logs: ${YELLOW}docker-compose logs stockhogar${NC}"
    echo -e "Para reiniciar: ${YELLOW}docker-compose restart${NC}"
    exit 1
fi
