#!/bin/bash
# Docker Compose v2 ("docker compose") o v1 ("docker-compose")
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}StockHogar - Mantenimiento y Limpieza${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

read -p "Selecciona una opcion:
1) Limpiar logs antiguos
2) Backup de base de datos
3) Optimizar base de datos
4) Limpiar cache Docker
5) Actualizar imagen
6) Ver estadisticas de uso
7) Salir

Opcion: " option

case $option in
    1)
        echo -e "${YELLOW}Limpiando logs...${NC}"
        find logs -name "*.log" -mtime +30 -delete
        echo -e "${GREEN}Hecho${NC}"
        ;;
    2)
        echo -e "${YELLOW}Backup de BD...${NC}"
        cp data/stock.db data/stock.db.backup.$(date +%Y%m%d-%H%M%S)
        echo -e "${GREEN}Backup completado${NC}"
        ls -lh data/stock.db.backup.*
        ;;
    3)
        echo -e "${YELLOW}Optimizando BD...${NC}"
        $DC exec stockhogar python3 << 'SQLITE'
import sqlite3
conn = sqlite3.connect('/app/data/stock.db')
conn.execute('VACUUM')
conn.execute('ANALYZE')
conn.close()
print('Optimizacion completada')
SQLITE
        ;;
    4)
        echo -e "${YELLOW}Limpiando cache Docker...${NC}"
        docker system prune -f
        echo -e "${GREEN}Cache limpiado${NC}"
        ;;
    5)
        echo -e "${YELLOW}Actualizando imagen...${NC}"
        # install.sh --update trae el codigo, descarga la imagen verificada, hace copia de la BD y
        # revierte solo si algo falla (un "build --no-cache" en la Pi tarda decenas de minutos).
        ./install.sh --update
        echo -e "${GREEN}Actualizado${NC}"
        ;;
    6)
        echo -e "${YELLOW}Estadisticas de uso:${NC}"
        docker stats --no-stream stockhogar-app
        echo ""
        echo -e "${YELLOW}Espacio en disco:${NC}"
        du -sh data/ logs/ uploads/
        echo ""
        echo -e "${YELLOW}Tamano base de datos:${NC}"
        ls -lh data/stock.db
        ;;
    7)
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo "Opcion invalida"
        exit 1
        ;;
esac
