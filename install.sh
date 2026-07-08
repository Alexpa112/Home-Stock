#!/bin/bash

################################################################################
# StockHogar Docker Installer para Raspbian
################################################################################

set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STEPS_COMPLETED=0
STEPS_TOTAL=10
LOG_FILE="/tmp/stockhogar-install.log"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

step_start() {
    STEPS_COMPLETED=$((STEPS_COMPLETED + 1))
    echo ""
    echo -e "${BLUE}═══ PASO $STEPS_COMPLETED/$STEPS_TOTAL: $1 ═══${NC}"
}

step_end() { log_success "Paso completado"; }

check_cmd() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 disponible"; return 0
    else
        log_error "$1 no encontrado"; return 1
    fi
}

handle_error() {
    log_error "Error en linea $1"
    log_error "Ver log: $LOG_FILE"
    exit 1
}

trap 'handle_error ${LINENO}' ERR

################################################################################
# PASO 1: VALIDACION DE SISTEMA
################################################################################

step_start "Validar Sistema Operativo"

if grep -qi "raspbian\|debian" /etc/os-release 2>/dev/null; then
    log_success "OS compatible detectado"
else
    log_warning "Este script esta optimizado para Raspbian/Debian"
fi

step_end

################################################################################
# PASO 2: VALIDACION DE REQUISITOS
################################################################################

step_start "Validar Requisitos Minimos"

MEMORY_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "1024")
if [[ $MEMORY_MB -lt 512 ]]; then
    log_warning "Memoria: ${MEMORY_MB}MB (recomendado: 1GB+)"
else
    log_success "Memoria: ${MEMORY_MB}MB"
fi

if ! sudo -n true 2>/dev/null; then
    log_error "Se requieren permisos de sudo"
    exit 1
fi
log_success "Permisos de sudo OK"

step_end

################################################################################
# PASO 3: ACTUALIZAR SISTEMA
################################################################################

step_start "Actualizar Sistema"

log_info "apt update..."
sudo apt-get update -qq 2>/dev/null || true

log_info "apt upgrade (puede tomar tiempo)..."
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq 2>/dev/null || true

log_success "Sistema actualizado"

step_end

################################################################################
# PASO 4: INSTALAR DOCKER
################################################################################

step_start "Instalar Docker"

if check_cmd docker; then
    log_success "Docker $(docker --version | cut -d' ' -f3)"
else
    log_info "Instalando Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker $USER 2>/dev/null || true
    log_success "Docker instalado"
fi

step_end

################################################################################
# PASO 5: INSTALAR DOCKER COMPOSE
################################################################################

step_start "Instalar Docker Compose"

if check_cmd docker-compose; then
    log_success "Docker Compose $(docker-compose --version | rev | cut -d' ' -f1 | rev)"
else
    log_info "Instalando Docker Compose..."
    sudo apt-get install -y python3-pip -qq
    sudo pip3 install docker-compose --no-cache-dir -q
    log_success "Docker Compose instalado"
fi

step_end

################################################################################
# PASO 6: VERIFICAR PROYECTO
################################################################################

step_start "Verificar Estructura del Proyecto"

MISSING=0
for FILE in "Dockerfile.raspbian" "docker-compose.yml" "stockhogar/__init__.py"; do
    if [[ ! -f "$FILE" ]]; then
        log_error "Falta: $FILE"
        MISSING=1
    fi
done

if [[ ! -d "stockhogar" ]]; then
    log_error "Directorio 'stockhogar' no encontrado"
    MISSING=1
fi

if [[ $MISSING -eq 1 ]]; then
    log_error "Estructura del proyecto incompleta"
    exit 1
fi

log_success "Proyecto verificado"

step_end

################################################################################
# PASO 7: CREAR DIRECTORIOS
################################################################################

step_start "Crear Directorios de Datos"

mkdir -p data logs uploads stockhogar/servicios/ocr
sudo chown -R $USER:$USER . 2>/dev/null || true

log_success "Directorios creados"

step_end

################################################################################
# PASO 8: CONFIGURACION .env
################################################################################

step_start "Configurar Variables de Entorno"

if [[ ! -f ".env" ]]; then
    cat > .env << 'EOF'
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO
STOCKHOGAR_PORT=5000
DATABASE_URL=sqlite:////app/data/stockhogar.db
EOF
    log_success ".env creado"
else
    log_warning ".env ya existe"
fi

step_end

################################################################################
# PASO 9: CONSTRUIR E INICIAR
################################################################################

step_start "Construir e Iniciar Contenedores"

log_info "Construccion de imagen (puede tomar 10-20 minutos)..."
docker-compose build --no-cache 2>&1 | tail -20

log_info "Iniciando servicios..."
docker-compose up -d

log_info "Esperando inicializacion (30 segundos)..."
sleep 30

log_success "Contenedores iniciados"

docker-compose ps

step_end

################################################################################
# PASO 10: RESUMEN FINAL
################################################################################

step_start "Instalacion Completada"

IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  StockHogar Instalado Exitosamente en Docker       ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}Acceso:${NC}"
echo -e "    Local:  http://localhost:5000"
echo -e "    Red:    http://${IP_ADDRESS}:5000"
echo ""
echo -e "  ${YELLOW}Comandos:${NC}"
echo -e "    Logs:       docker-compose logs -f stockhogar"
echo -e "    Detener:    docker-compose down"
echo -e "    Reiniciar:  docker-compose restart"
echo ""

# Health check
log_info "Verificando aplicacion..."
READY=0
for i in {1..10}; do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 5
done

if [[ $READY -eq 1 ]]; then
    log_success "INSTALACION 100% EXITOSA - Aplicacion funcionando"
    exit 0
else
    log_warning "Aplicacion inicializandose. Intenta en 1 minuto: http://localhost:5000"
    exit 0
fi
