#!/bin/bash
################################################################################
# StockHogar - Instalador Docker (Raspberry Pi / Debian / Ubuntu)
#
# Uso:
#   ./install.sh            Instala o actualiza StockHogar
#   ./install.sh --update   Además hace `git pull` antes de reconstruir
#   ./install.sh --help     Muestra esta ayuda
#
# Seguro de re-ejecutar: no pisa un .env existente (y lo respalda antes de
# tocarlo), hace backup de la base de datos antes de reconstruir contenedores,
# detecta si Docker Compose está disponible como plugin v2 (`docker compose`)
# o binario v1 (`docker-compose`), reintenta operaciones de red con backoff,
# valida la configuración antes de construir, y si algo falla deja el sistema
# en un estado conocido (no a medias) y vuelca los logs relevantes.
################################################################################

set -Eeuo pipefail

# --- Rutas: el script funciona sin importar desde dónde se invoque ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STEPS_COMPLETED=0
STEPS_TOTAL=12
LOG_FILE="$SCRIPT_DIR/install.log"
LOCK_FILE="$SCRIPT_DIR/.install.lock"
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

# --- Bloqueo: evita que dos ejecuciones se pisen (cron + manual, doble clic) -
if [[ -e "$LOCK_FILE" ]]; then
    OTHER_PID="$(cat "$LOCK_FILE" 2>/dev/null || echo "")"
    if [[ -n "$OTHER_PID" ]] && kill -0 "$OTHER_PID" 2>/dev/null; then
        log_error "Ya hay una instalación en curso (PID $OTHER_PID). Espera a que termine o borra $LOCK_FILE si sabes que quedó huérfana."
        exit 1
    fi
    log_warning "Se encontró un lock huérfano de una ejecución anterior; se ignora y se continúa."
fi
echo "$$" > "$LOCK_FILE"

CLEANUP_DONE=0
cleanup() {
    [[ "$CLEANUP_DONE" -eq 1 ]] && return
    CLEANUP_DONE=1
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

on_interrupt() {
    echo ""
    log_warning "Instalación interrumpida por el usuario. El sistema puede haber quedado a medias;" \
                "vuelve a ejecutar ./install.sh para reintentar de forma segura."
    exit 130
}
trap on_interrupt INT TERM

ROLLBACK_DONE=0
rollback() {
    # Revierte a la imagen, código y base de datos anteriores. Solo actúa sobre
    # lo que realmente se llegó a respaldar en esta ejecución (variables
    # IMAGE_NAME/PREV_GIT_COMMIT/DB_BACKUP_FILE), así que en una primera
    # instalación (sin "anterior" al que volver) es un no-op seguro.
    [[ "$ROLLBACK_DONE" -eq 1 ]] && return
    ROLLBACK_DONE=1
    log_warning "Iniciando rollback automático a la versión anterior..."

    if [[ -n "${IMAGE_NAME:-}" ]] && $DOCKER image inspect "${IMAGE_NAME}:rollback" &> /dev/null; then
        if $DOCKER tag "${IMAGE_NAME}:rollback" "$IMAGE_NAME" >> "$LOG_FILE" 2>&1 \
           && $COMPOSE up -d --force-recreate >> "$LOG_FILE" 2>&1; then
            log_warning "Imagen Docker revertida a la versión anterior y contenedor recreado."
        else
            log_error "El rollback de la imagen Docker también falló; revisa $LOG_FILE manualmente."
        fi
    else
        log_warning "No había una imagen anterior guardada para revertir (probablemente es la primera instalación)."
    fi

    if [[ -n "${PREV_GIT_COMMIT:-}" ]]; then
        if git reset --hard "$PREV_GIT_COMMIT" >> "$LOG_FILE" 2>&1; then
            log_warning "Código revertido al commit anterior: $PREV_GIT_COMMIT"
        else
            log_error "No se pudo revertir el código a $PREV_GIT_COMMIT; revísalo manualmente con git."
        fi
    fi

    if [[ -n "${DB_BACKUP_FILE:-}" && -f "$DB_BACKUP_FILE" ]]; then
        cp "$DB_BACKUP_FILE" "data/stock.db"
        log_warning "Base de datos restaurada desde el backup: $DB_BACKUP_FILE"
    fi

    log_error "Rollback completado: se ha vuelto a la versión anterior que funcionaba." \
               "Revisa $LOG_FILE para ver qué falló en la actualización antes de reintentar."
}

handle_error() {
    local line="$1" code="$2"
    log_error "Fallo en la línea $line (código $code)"
    log_error "Log completo: $LOG_FILE"
    if [[ -n "${COMPOSE:-}" ]] && $COMPOSE ps &> /dev/null; then
        log_error "Últimas líneas de los contenedores (para diagnóstico):"
        $COMPOSE logs --tail=60 2>&1 | tee -a "$LOG_FILE" || true
    fi
    rollback
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

retry() {
    # Reintenta un comando propenso a fallos de red (apt, curl, docker build)
    # con backoff exponencial en vez de abortar al primer fallo transitorio.
    local max_attempts=3 attempt=1 delay=5
    local desc="$*"
    while true; do
        log_info "\$ $desc (intento $attempt/$max_attempts)"
        if "$@" >> "$LOG_FILE" 2>&1; then
            return 0
        fi
        if [[ "$attempt" -ge "$max_attempts" ]]; then
            log_error "Comando falló tras $max_attempts intentos: $desc"
            log_error "Log completo: $LOG_FILE"
            exit 1
        fi
        log_warning "Falló (intento $attempt/$max_attempts); reintentando en ${delay}s..."
        sleep "$delay"
        delay=$((delay * 2))
        attempt=$((attempt + 1))
    done
}

usage() {
    cat <<EOF
Uso: ./install.sh [--update] [--help]

  (sin flags)  Instala o reconstruye StockHogar en este directorio.
  --update     Además hace 'git pull --ff-only' antes de reconstruir.
  --help       Muestra esta ayuda y sale.
EOF
}

UPDATE_MODE=0
case "${1:-}" in
    --update) UPDATE_MODE=1 ;;
    --help|-h) usage; exit 0 ;;
    "") ;;
    *) log_error "Opción desconocida: ${1}"; usage; exit 1 ;;
esac

################################################################################
step_start "Detectar sistema y Docker"
################################################################################

if [[ -f /etc/os-release ]] && grep -qiE "raspbian|debian|ubuntu" /etc/os-release; then
    log_success "OS compatible: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
else
    log_warning "SO no reconocido como Debian/Ubuntu/Raspbian; se continúa igualmente"
fi

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|aarch64|armv7l|armv6l) log_success "Arquitectura: $ARCH (soportada)" ;;
    *) log_warning "Arquitectura no probada: $ARCH; puede que no existan imágenes base compatibles" ;;
esac

MEMORY_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "")
if [[ -n "$MEMORY_MB" ]]; then
    if [[ "$MEMORY_MB" -lt 512 ]]; then
        log_warning "Memoria: ${MEMORY_MB}MB (recomendado: 1GB+; la app puede ir lenta o el build fallar por OOM)"
    else
        log_success "Memoria: ${MEMORY_MB}MB"
    fi
fi

FREE_DISK_MB=$(df -Pm "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "")
if [[ -n "$FREE_DISK_MB" ]]; then
    if [[ "$FREE_DISK_MB" -lt 800 ]]; then
        log_error "Espacio libre en disco: ${FREE_DISK_MB}MB. Insuficiente para construir la imagen" \
                   "(Python, OpenCV y los modelos de Argos Translate necesitan varios cientos de MB). Libera espacio y reintenta."
        exit 1
    elif [[ "$FREE_DISK_MB" -lt 2048 ]]; then
        log_warning "Espacio libre en disco: ${FREE_DISK_MB}MB (recomendado: 2GB+ para construir la imagen con margen)"
    else
        log_success "Espacio libre en disco: ${FREE_DISK_MB}MB"
    fi
fi

if ! [[ -w "$SCRIPT_DIR" ]]; then
    log_error "No hay permiso de escritura en $SCRIPT_DIR; no se pueden crear data/, logs/, uploads/ ni .env"
    exit 1
fi

log_info "Comprobando conectividad de red (necesaria para Docker, apt y los modelos de traducción)..."
if check_cmd curl && ! curl -fsS --max-time 5 -o /dev/null https://get.docker.com; then
    log_error "Sin conectividad a internet (no se alcanza get.docker.com). Revisa la conexión de red y reintenta."
    exit 1
fi
log_success "Conectividad de red OK"

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
        retry $SUDO apt-get update -qq
        retry $SUDO apt-get install -y -qq "$c"
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
    retry curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
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

DOCKER=""
for i in 1 2 3 4 5; do
    if docker info &> /dev/null; then
        DOCKER="docker"
        break
    elif $SUDO docker info &> /dev/null; then
        DOCKER="$SUDO docker"
        log_warning "Docker solo responde con sudo (el usuario aún no tiene el grupo 'docker' activo en esta sesión)"
        break
    fi
    log_info "Esperando a que el daemon de Docker esté listo (intento $i/5)..."
    sleep 3
done

if [[ -z "$DOCKER" ]]; then
    log_error "El daemon de Docker no responde tras varios intentos. Revisa: sudo systemctl status docker"
    exit 1
fi
log_success "Docker operativo: $($DOCKER version --format '{{.Server.Version}}' 2>/dev/null || echo desconocida)"

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
    retry $SUDO apt-get update -qq
    if retry $SUDO apt-get install -y -qq docker-compose-plugin; then
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
for FILE in "Dockerfile.raspbian" "docker-compose.yml" "requirements.txt" "stockhogar/__init__.py" "run.py" \
            "stockhogar/static/manifest.json" "stockhogar/static/icons/sprite.svg" "stockhogar/static/icons/icon-192.png" \
            "Dockerfile.frontend" "package.json" "next.config.mjs"; do
    if [[ ! -f "$FILE" ]]; then
        log_error "Falta: $FILE"
        MISSING=1
    fi
done

if [[ $MISSING -eq 1 ]]; then
    log_error "Estructura del proyecto incompleta. ¿Se ejecutó el script dentro del repo clonado?"
    log_error "Los iconos y el sprite se generan en desarrollo con 'npm install && node scripts/generar-sprite-iconos.js" \
               "&& node scripts/generar-iconos-png.js' y deben estar ya commiteados en el repo; este script no los genera."
    exit 1
fi
log_success "Proyecto verificado (incluye iconos PWA y manifest)"

step_end

################################################################################
step_start "Actualizar código (git pull)"
################################################################################

if [[ $UPDATE_MODE -eq 1 ]]; then
    if [[ -d .git ]]; then
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            log_error "Hay cambios locales sin commitear en el repo; 'git pull --ff-only' podría fallar o perder trabajo."
            log_error "Guárdalos (git stash) o commitéalos antes de usar --update."
            exit 1
        fi
        PREV_GIT_COMMIT="$(git rev-parse HEAD)"
        log_info "Commit actual (para rollback si algo falla): $PREV_GIT_COMMIT"
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
    DB_BACKUP_FILE="data/backups/stock-${TS}.db"
    cp "data/stock.db" "$DB_BACKUP_FILE"
    if [[ ! -s "$DB_BACKUP_FILE" ]]; then
        log_error "El backup de la base de datos quedó vacío o no se creó; se aborta antes de tocar los contenedores."
        exit 1
    fi
    log_success "Backup creado: $DB_BACKUP_FILE"
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
# sin tocar las que el usuario ya haya configurado, y se respalda antes por
# si el añadido de variables faltantes tuviera que deshacerse a mano.
REQUIRED_VARS=(
    GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET
    APPLE_CLIENT_ID APPLE_CLIENT_SECRET APPLE_TEAM_ID
    SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_FROM
    APP_URL
    STOCKHOGAR_PORT
    STOCKHOGAR_FRONTEND_PORT
    FLASK_ENV
)
DEFAULT_VALUE() {
    case "$1" in
        SMTP_SERVER) echo "smtp.gmail.com" ;;
        SMTP_PORT) echo "587" ;;
        SMTP_FROM) echo "noreply@homestock.local" ;;
        APP_URL) echo "http://localhost:5000" ;;
        STOCKHOGAR_PORT) echo "5000" ;;
        STOCKHOGAR_FRONTEND_PORT) echo "3000" ;;
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
    cp ".env" "data/backups/env-$(date +%Y%m%d-%H%M%S).bak"
    ls -1t data/backups/env-*.bak 2>/dev/null | tail -n +6 | xargs -r rm -f
    log_info ".env ya existe: se conservan los valores actuales (respaldado antes de tocarlo)"
fi

for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" ".env" 2>/dev/null; then
        echo "${VAR}=$(DEFAULT_VALUE "$VAR")" >> ".env"
        log_info "Añadida variable faltante: $VAR"
    fi
done

STOCKHOGAR_PORT="$(grep -m1 '^STOCKHOGAR_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')"
STOCKHOGAR_PORT="${STOCKHOGAR_PORT:-5000}"
if ! [[ "$STOCKHOGAR_PORT" =~ ^[0-9]+$ ]] || [[ "$STOCKHOGAR_PORT" -lt 1 ]] || [[ "$STOCKHOGAR_PORT" -gt 65535 ]]; then
    log_error "STOCKHOGAR_PORT='$STOCKHOGAR_PORT' en .env no es un puerto válido (1-65535)."
    exit 1
fi

# Si el puerto ya está en uso por algo que NO sea el propio stack de compose de
# este proyecto (p.ej. otro servicio, u otra instalación de StockHogar), avisamos
# ahora en vez de dejar que 'compose up' falle de forma confusa más tarde.
if check_cmd ss && ss -ltn 2>/dev/null | grep -q ":${STOCKHOGAR_PORT} "; then
    if ! $COMPOSE ps 2>/dev/null | grep -q .; then
        log_error "El puerto ${STOCKHOGAR_PORT} ya está en uso por otro proceso y no hay contenedores de" \
                   "este proyecto corriendo todavía. Cambia STOCKHOGAR_PORT en .env o libera el puerto."
        exit 1
    fi
    log_info "El puerto ${STOCKHOGAR_PORT} está en uso, probablemente por una instalación previa de este mismo stack; se reconstruirá sobre ella."
fi

log_warning "Revisa .env y rellena GOOGLE_CLIENT_ID / APPLE_CLIENT_ID / SMTP_* si vas a" \
             "usar login social o invitaciones por email. Sin ellos la app funciona igual" \
             "(login con usuario/contraseña, invitaciones como enlace copiable)."

step_end

################################################################################
step_start "Validar configuración de Docker Compose"
################################################################################

if ! $COMPOSE config -q 2>>"$LOG_FILE"; then
    log_error "docker-compose.yml (o el .env) no es válido. Revisa el log:"
    tail -n 30 "$LOG_FILE"
    exit 1
fi
log_success "docker-compose.yml válido"

step_end

################################################################################
step_start "Construir imagen"
################################################################################

IMAGE_NAME="$($COMPOSE config --images 2>/dev/null | head -1)"
if [[ -n "$IMAGE_NAME" ]] && $DOCKER image inspect "$IMAGE_NAME" &> /dev/null; then
    run $DOCKER tag "$IMAGE_NAME" "${IMAGE_NAME}:rollback"
    log_info "Imagen anterior guardada como ${IMAGE_NAME}:rollback por si hay que revertir"
else
    log_info "No hay imagen anterior (primera instalación); no hay nada que respaldar todavía"
fi

log_info "Construyendo imagen Docker (puede tardar varios minutos)..."
log_info "Se descargan también los modelos de traducción (Argos Translate); requiere conexión a internet."
retry $COMPOSE build

step_end

################################################################################
step_start "Iniciar contenedores"
################################################################################

run $COMPOSE up -d --remove-orphans

log_info "Esperando a que el contenedor arranque..."
sleep 5
$COMPOSE ps | tee -a "$LOG_FILE"

step_end

################################################################################
step_start "Instalación completada"
################################################################################

IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
IP_ADDRESS="${IP_ADDRESS:-localhost}"

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  StockHogar instalado${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
FRONTEND_PORT="$(grep -m1 '^STOCKHOGAR_FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

echo -e "  ${YELLOW}Acceso (frontend nuevo, Next.js):${NC}"
echo -e "    Local:  http://localhost:${FRONTEND_PORT}"
echo -e "    Red:    http://${IP_ADDRESS}:${FRONTEND_PORT}"
echo ""
echo -e "  ${YELLOW}Backend Flask (API, y frontend anterior en /):${NC}"
echo -e "    Local:  http://localhost:${STOCKHOGAR_PORT}"
echo -e "    Red:    http://${IP_ADDRESS}:${STOCKHOGAR_PORT}"
echo ""

echo -e "  ${YELLOW}Panel de gestión del servidor:${NC}"
echo -e "    Es un proyecto aparte (StockHogar-Panel), con su propio instalador."
echo -e "    Si lo tienes clonado como carpeta hermana de esta, instálalo con:"
echo -e "      cd ../StockHogar-Panel && ./install.sh"
echo ""
echo -e "  ${YELLOW}Comandos útiles:${NC}"
echo -e "    Logs:       $COMPOSE logs -f stockhogar"
echo -e "    Detener:    $COMPOSE down"
echo -e "    Reiniciar:  $COMPOSE restart"
echo -e "    Actualizar: ./install.sh --update"
echo ""

# --- Panel de Gestión del Servidor: se instala solo si está disponible -----
# Es un proyecto independiente (StockHogar-Panel), pero si está clonado como
# carpeta hermana de este repo, aprovechamos para instalarlo automáticamente
# aquí también, en vez de obligar a un segundo paso manual.
PANEL_DIR="$(cd "$SCRIPT_DIR/../StockHogar-Panel" 2>/dev/null && pwd || echo "")"
if [[ -n "$PANEL_DIR" ]] && [[ -f "$PANEL_DIR/install.sh" ]]; then
    echo -e "${BLUE}=== Instalando también el Panel de Gestión del Servidor ===${NC}"
    if (cd "$PANEL_DIR" && ./install.sh "$SCRIPT_DIR"); then
        log_success "Panel de Gestión instalado (ver arriba la URL y la contraseña temporal)"
        log_info "Para que arranque solo con la Raspberry Pi: cd \"$PANEL_DIR\" && ./install.sh --systemd"
    else
        log_warning "No se pudo instalar el panel automáticamente. Instálalo a mano: cd \"$PANEL_DIR\" && ./install.sh"
    fi
    echo ""
else
    log_info "No se encontró StockHogar-Panel como carpeta hermana; omito su instalación. Clónalo junto a este repo si quieres el panel de gestión (rendimiento, mantenimiento, backups...)."
fi

log_info "Comprobando que la aplicación responde..."
READY=0
for i in $(seq 1 15); do
    if curl -fsS "http://localhost:${STOCKHOGAR_PORT}/" > /dev/null 2>&1; then
        READY=1
        break
    fi
    if ! $COMPOSE ps stockhogar 2>/dev/null | grep -qi "up"; then
        log_error "El contenedor stockhogar no está en marcha. Últimas líneas de log:"
        $COMPOSE logs --tail=60 stockhogar 2>&1 | tee -a "$LOG_FILE" || true
        rollback
        exit 1
    fi
    sleep 4
done

if [[ $READY -eq 1 ]]; then
    log_success "Backend respondiendo correctamente en el puerto ${STOCKHOGAR_PORT}"

    # El frontend depende del backend y puede tardar un poco mas en arrancar
    # (compilacion/arranque de Next.js); no bloqueante ni dispara rollback,
    # solo se avisa si tarda mas de lo esperado.
    FRONTEND_READY=0
    for i in $(seq 1 15); do
        if curl -fsS "http://localhost:${FRONTEND_PORT}/" > /dev/null 2>&1; then
            FRONTEND_READY=1
            break
        fi
        sleep 4
    done
    if [[ $FRONTEND_READY -eq 1 ]]; then
        log_success "Frontend respondiendo correctamente en el puerto ${FRONTEND_PORT}"
    else
        log_warning "El frontend aún no responde tras 60s. Puede seguir arrancando; revisa: $COMPOSE logs -f frontend"
    fi
    exit 0
elif [[ $UPDATE_MODE -eq 1 ]]; then
    # En --update SÍ tenemos una versión anterior conocida-buena a la que
    # volver, así que un healthcheck fallido dispara el rollback automático
    # en vez de dejar la instalación en un estado roto.
    log_error "La aplicación no respondió en 60s tras la actualización. Últimas líneas de log:"
    $COMPOSE logs --tail=60 stockhogar 2>&1 | tee -a "$LOG_FILE" || true
    rollback
    exit 1
else
    log_warning "La aplicación aún no responde tras 60s. Últimas líneas de log:"
    $COMPOSE logs --tail=60 stockhogar 2>&1 | tee -a "$LOG_FILE" || true
    log_warning "Puede seguir arrancando (p.ej. descarga de modelos); revisa: $COMPOSE logs -f stockhogar"
    exit 0
fi
