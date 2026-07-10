#!/bin/bash
################################################################################
# StockHogar - Instalador Docker (Raspberry Pi / Debian / Ubuntu)
#
# Uso:
#   ./install.sh            Instala o actualiza StockHogar
#   ./install.sh --update   Además hace `git pull` antes de reconstruir
#
# Seguro de re-ejecutar: no pisa un .env existente, hace backup de la base de
# datos antes de reconstruir contenedores, y detecta si Docker Compose está
# disponible como plugin v2 (`docker compose`) o binario v1 (`docker-compose`).
################################################################################

set -uo pipefail

# --- Rutas: el script funciona sin importar desde dónde se invoque ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STEPS_COMPLETED=0
STEPS_TOTAL=11
LOG_FILE="$SCRIPT_DIR/install.log"
: > "$LOG_FILE"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

step_start() {
    STEPS_COMPLETED=$((STEPS_COMPLETED + 1))
    echo ""
    echo -e "${BLUE}=== PASO $STEPS_COMPLETED/$STEPS_TOTAL: $1 ===${NC}"
}
step_end() { log_success "Paso completado"; }

check_cmd() { command -v "$1" &> /dev/null; }

handle_error() {
    log_error "Fallo en la línea $1 (código $2)"
    log_error "Log completo: $LOG_FILE"
    exit 1
}
trap 'handle_error ${LINENO} $?' ERR

run() {
    # Ejecuta un comando y aborta con handle_error si falla, registrando qué
    # comando fue (trap ERR por sí solo no dice CUÁL comando reventó).
    log_info "\$ $*"
    if ! "$@" >> "$LOG_FILE" 2>&1; then
        log_error "Comando falló: $*"
        log_error "Log completo: $LOG_FILE"
        exit 1
    fi
}

UPDATE_MODE=0
if [[ "${1:-}" == "--update" ]]; then
    UPDATE_MODE=1
fi

################################################################################
step_start "Detectar sistema y Docker"
################################################################################

if [[ -f /etc/os-release ]] && grep -qiE "raspbian|debian|ubuntu" /etc/os-release; then
    log_success "OS compatible: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
else
    log_warning "SO no reconocido como Debian/Ubuntu/Raspbian; se continúa igualmente"
fi

ARCH="$(uname -m)"
log_info "Arquitectura: $ARCH"

MEMORY_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "")
if [[ -n "$MEMORY_MB" ]]; then
    if [[ "$MEMORY_MB" -lt 512 ]]; then
        log_warning "Memoria: ${MEMORY_MB}MB (recomendado: 1GB+; la app puede ir lenta o el build fallar por OOM)"
    else
        log_success "Memoria: ${MEMORY_MB}MB"
    fi
fi

FREE_DISK_MB=$(df -Pm "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "")
if [[ -n "$FREE_DISK_MB" && "$FREE_DISK_MB" -lt 2048 ]]; then
    log_warning "Espacio libre en disco: ${FREE_DISK_MB}MB (recomendado: 2GB+ para construir la imagen)"
fi

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
    if ! check_cmd sudo; then
        log_error "Se necesita 'sudo' (o ejecutar este script como root)"
        exit 1
    fi
    if ! sudo -n true 2>/dev/null; then
        log_info "Se pedirá contraseña de sudo para instalar paquetes del sistema"
        sudo -v || { log_error "No se obtuvieron permisos de sudo"; exit 1; }
    fi
    SUDO="sudo"
fi

for c in curl git; do
    if ! check_cmd "$c"; then
        log_info "Instalando $c..."
        run $SUDO apt-get update -qq
        run $SUDO apt-get install -y -qq "$c"
    fi
done
log_success "curl y git disponibles"

step_end

################################################################################
step_start "Instalar Docker"
################################################################################

if check_cmd docker; then
    log_success "Docker ya instalado: $(docker --version)"
else
    log_info "Instalando Docker (script oficial get.docker.com)..."
    run curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    run $SUDO sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
    if [[ -n "$SUDO" ]]; then
        run $SUDO usermod -aG docker "$(id -un)"
        log_warning "Se añadió tu usuario al grupo 'docker'. Si los siguientes pasos fallan por" \
                     "permisos, cierra sesión y vuelve a entrar (o ejecuta: newgrp docker) y relanza este script."
    fi
    log_success "Docker instalado"
fi

if ! $SUDO systemctl is-active --quiet docker 2>/dev/null && ! docker info &> /dev/null; then
    log_info "Arrancando el servicio de Docker..."
    run $SUDO systemctl enable --now docker || run $SUDO service docker start
fi

if ! docker info &> /dev/null; then
    if ! $SUDO docker info &> /dev/null; then
        log_error "El daemon de Docker no responde. Revisa: sudo systemctl status docker"
        exit 1
    fi
    log_warning "Docker solo responde con sudo (el usuario aún no tiene el grupo 'docker' activo en esta sesión)"
    DOCKER="$SUDO docker"
else
    DOCKER="docker"
fi
log_success "Docker operativo"

step_end

################################################################################
step_start "Detectar Docker Compose"
################################################################################

COMPOSE=""
if $DOCKER compose version &> /dev/null; then
    COMPOSE="$DOCKER compose"
    log_success "Docker Compose (plugin v2): $($DOCKER compose version --short 2>/dev/null)"
elif check_cmd docker-compose; then
    COMPOSE="docker-compose"
    log_warning "Usando docker-compose v1 (binario independiente). Se recomienda migrar al plugin v2."
else
    log_info "Instalando el plugin docker-compose-plugin vía apt..."
    run $SUDO apt-get update -qq
    if $SUDO apt-get install -y -qq docker-compose-plugin 2>>"$LOG_FILE"; then
        COMPOSE="$DOCKER compose"
        log_success "Docker Compose (plugin v2) instalado"
    else
        log_error "No se pudo instalar docker-compose-plugin."
        log_error "Instálalo manualmente: https://docs.docker.com/compose/install/linux/"
        exit 1
    fi
fi

step_end

################################################################################
step_start "Verificar estructura del proyecto"
################################################################################

MISSING=0
for FILE in "Dockerfile.raspbian" "docker-compose.yml" "requirements.txt" "stockhogar/__init__.py" "run.py"; do
    if [[ ! -f "$FILE" ]]; then
        log_error "Falta: $FILE"
        MISSING=1
    fi
done

if [[ $MISSING -eq 1 ]]; then
    log_error "Estructura del proyecto incompleta. ¿Se ejecutó el script dentro del repo clonado?"
    exit 1
fi
log_success "Proyecto verificado"

step_end

################################################################################
step_start "Actualizar código (git pull)"
################################################################################

if [[ $UPDATE_MODE -eq 1 ]]; then
    if [[ -d .git ]]; then
        run git pull --ff-only
        log_success "Código actualizado"
    else
        log_warning "No es un repositorio git; se omite git pull"
    fi
else
    log_info "Modo instalación (usa --update para además hacer git pull)"
fi

step_end

################################################################################
step_start "Crear directorios de datos"
################################################################################

mkdir -p data logs uploads stockhogar/servicios/ocr data/backups
if [[ -n "$SUDO" ]]; then
    $SUDO chown -R "$(id -u):$(id -g)" data logs uploads 2>/dev/null || true
fi
log_success "Directorios listos: data/, logs/, uploads/"

step_end

################################################################################
step_start "Backup de la base de datos"
################################################################################

if [[ -f "data/stock.db" ]]; then
    TS="$(date +%Y%m%d-%H%M%S)"
    cp "data/stock.db" "data/backups/stock-${TS}.db"
    log_success "Backup creado: data/backups/stock-${TS}.db"
    # Nos quedamos con las 10 copias más recientes para no llenar el disco.
    ls -1t data/backups/stock-*.db 2>/dev/null | tail -n +11 | xargs -r rm -f
else
    log_info "No hay base de datos previa; se creará una nueva al arrancar"
fi

step_end

################################################################################
step_start "Configurar variables de entorno (.env)"
################################################################################

# El .env real del usuario NUNCA se sobrescribe. Si no existe, se crea a partir
# de .env.example (con valores de ejemplo, el usuario debe rellenarlos luego
# para OAuth/email). Si ya existe, se completan solo las claves que falten,
# sin tocar las que el usuario ya haya configurado.
REQUIRED_VARS=(
    GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET
    APPLE_CLIENT_ID APPLE_CLIENT_SECRET APPLE_TEAM_ID
    SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_FROM
    APP_URL
    STOCKHOGAR_PORT
    FLASK_ENV
)
DEFAULT_VALUE() {
    case "$1" in
        SMTP_SERVER) echo "smtp.gmail.com" ;;
        SMTP_PORT) echo "587" ;;
        SMTP_FROM) echo "noreply@homestock.local" ;;
        APP_URL) echo "http://localhost:5000" ;;
        STOCKHOGAR_PORT) echo "5000" ;;
        FLASK_ENV) echo "production" ;;
        *) echo "" ;;
    esac
}

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp ".env.example" ".env"
    else
        : > ".env"
    fi
    log_success ".env creado a partir de .env.example"
else
    log_info ".env ya existe: se conservan los valores actuales"
fi

for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" ".env" 2>/dev/null; then
        echo "${VAR}=$(DEFAULT_VALUE "$VAR")" >> ".env"
        log_info "Añadida variable faltante: $VAR"
    fi
done

log_warning "Revisa .env y rellena GOOGLE_CLIENT_ID / APPLE_CLIENT_ID / SMTP_* si vas a" \
             "usar login social o invitaciones por email. Sin ellos la app funciona igual" \
             "(login con usuario/contraseña, invitaciones como enlace copiable)."

step_end

################################################################################
step_start "Construir imagen"
################################################################################

log_info "Construyendo imagen Docker (puede tardar varios minutos)..."
log_info "Se descargan también los modelos de traducción (Argos Translate); requiere conexión a internet."
run $COMPOSE build

step_end

################################################################################
step_start "Iniciar contenedores"
################################################################################

run $COMPOSE up -d

log_info "Esperando a que el contenedor arranque..."
sleep 5
$COMPOSE ps | tee -a "$LOG_FILE"

step_end

################################################################################
step_start "Instalación completada"
################################################################################

STOCKHOGAR_PORT="$(grep -m1 '^STOCKHOGAR_PORT=' .env 2>/dev/null | cut -d= -f2)"
STOCKHOGAR_PORT="${STOCKHOGAR_PORT:-5000}"
IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}')
IP_ADDRESS="${IP_ADDRESS:-localhost}"

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  StockHogar instalado${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "  ${YELLOW}Acceso:${NC}"
echo -e "    Local:  http://localhost:${STOCKHOGAR_PORT}"
echo -e "    Red:    http://${IP_ADDRESS}:${STOCKHOGAR_PORT}"
echo ""
echo -e "  ${YELLOW}Comandos útiles:${NC}"
echo -e "    Logs:       $COMPOSE logs -f stockhogar"
echo -e "    Detener:    $COMPOSE down"
echo -e "    Reiniciar:  $COMPOSE restart"
echo -e "    Actualizar: ./install.sh --update"
echo ""

log_info "Comprobando que la aplicación responde..."
READY=0
for i in $(seq 1 15); do
    if curl -fsS "http://localhost:${STOCKHOGAR_PORT}/" > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 4
done

if [[ $READY -eq 1 ]]; then
    log_success "Aplicación respondiendo correctamente en el puerto ${STOCKHOGAR_PORT}"
    exit 0
else
    log_warning "La aplicación aún no responde. Revisa los logs: $COMPOSE logs -f stockhogar"
    exit 0
fi
