#!/bin/bash

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
        cp data/stockhogar.db data/stockhogar.db.backup.$(date +%Y%m%d-%H%M%S)
        echo -e "${GREEN}Backup completado${NC}"
        ls -lh data/stockhogar.db.backup.*
        ;;
    3)
        echo -e "${YELLOW}Optimizando BD...${NC}"
        docker-compose exec stockhogar python3 << 'SQLITE'
import sqlite3
conn = sqlite3.connect('/app/data/stockhogar.db')
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
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
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
        ls -lh data/stockhogar.db
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
