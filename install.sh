#!/bin/bash
################################################################################
# StockHogar - Instalador Docker (Raspberry Pi / Debian / Ubuntu)
#
# Uso:
#   ./install.sh              Instala o actualiza StockHogar
#   ./install.sh --update     Además hace `git pull --ff-only` antes de reconstruir
#   ./install.sh --reinstall  Descarta cambios locales (git reset --hard al remoto)
#                             y reconstruye TODO sin caché (--no-cache)
#   ./install.sh --no-build   Reinicia contenedores sin reconstruir la imagen
#   ./install.sh --help       Muestra esta ayuda
#
# Seguro de re-ejecutar: no pisa un .env existente (y lo respalda antes de
# tocarlo), hace backup de la base de datos antes de reconstruir contenedores,
# detecta si Docker Compose está disponible como plugin v2 (`docker compose`)
# o binario v1 (`docker-compose`), y si algo falla deja el sistema en un estado
# conocido (no a medias) y vuelca los logs relevantes.
#
# El build se muestra EN VIVO por pantalla (no solo en el log): en una Raspberry
# Pi de 32 bits `next build` tarda entre 15 y 60 minutos y sin salida visible
# parece que el instalador se ha colgado.
################################################################################

set -Eeuo pipefail

# --- Rutas: el script funciona sin importar desde dónde se invoque ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ORIGINAL_ARGS=("$@")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STEPS_COMPLETED=0
STEPS_TOTAL=15
LOG_FILE="$SCRIPT_DIR/install.log"
LOCK_FILE="$SCRIPT_DIR/.install.lock"
: > "$LOG_FILE"

log_info()    { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"  | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }

step_start() {
    STEPS_COMPLETED=$((STEPS_COMPLETED + 1))
    echo ""
    echo -e "${BLUE}=== PASO $STEPS_COMPLETED/$STEPS_TOTAL: $1 ===${NC}" | tee -a "$LOG_FILE"
}
step_end() { log_success "Paso completado"; }

check_cmd() { command -v "$1" &> /dev/null; }

# Re-ejecutar este script bajo timeout global si no estamos ya bajo uno.
# Si timeout mata el script, el trap cleanup() se ejecuta y limpia el lock.
# Esto evita que un proceso colgado bloquee futuras ejecuciones.
if [[ "${_INSTALL_SH_TIMEOUT:-0}" -eq 0 ]]; then
    if check_cmd timeout; then
        export _INSTALL_SH_TIMEOUT=1
        # 5 horas de timeout (18000s): builds lentos en Pi pueden tardar ~60 min,
        # más overhead de I/O. Si se agota, timeout envía SIGTERM (permite cleanup)
        # y luego SIGKILL si no termina en 60s.
        exec timeout --signal=TERM --kill-after=60 18000 bash "$0" "$@"
    fi
fi

# DOCKER y COMPOSE son ARRAYS, no cadenas: `docker` puede necesitar `sudo`
# delante y `docker compose` son dos palabras. Como arrays se expanden sin
# `eval` ni riesgo de word-splitting: "${COMPOSE[@]}" ps
DOCKER=()
COMPOSE=()

# --- Bloqueo: evita que dos ejecuciones se pisen (cron + manual, doble clic) -
# flock (no el viejo check-then-write de PID) para que el propio kernel
# resuelva la carrera: dos procesos pueden pasar el `[[ -e "$LOCK_FILE" ]]`
# a la vez, `flock` no.
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    # El lock no está disponible. Verificar si el proceso que lo tiene existe.
    # Si quedó huérfano (la anterior ejecución se colgó), limpiar y reintentar.
    PREV_PID=""
    if [[ -s "$LOCK_FILE" ]]; then
        PREV_PID="$(cat "$LOCK_FILE" 2>/dev/null)"
    fi
    if [[ -n "$PREV_PID" ]] && ! kill -0 "$PREV_PID" 2>/dev/null; then
        # El PID que tiene el lock NO existe: lock huérfano. Limpiar y reintentar.
        log_warning "Lock huérfano detectado (PID $PREV_PID no existe). Limpiando..."
        rm -f "$LOCK_FILE"
        exec 200>"$LOCK_FILE"
        if ! flock -n 200; then
            log_error "Ya hay una instalación en curso. Espera a que termine o revisa $LOCK_FILE."
            exit 1
        fi
    else
        log_error "Ya hay una instalación en curso (PID ${PREV_PID:-desconocido}). Espera a que termine o revisa $LOCK_FILE."
        exit 1
    fi
fi
echo "$$" >&200

HEARTBEAT_PID=""
stop_heartbeat() {
    [[ -z "$HEARTBEAT_PID" ]] && return 0
    # Se matan PRIMERO los hijos (el `sleep`) y después el subshell: si solo se
    # mata el subshell, el `sleep` queda huérfano con el stdout heredado abierto
    # y bloquea a quien esté al otro lado de una tubería, de modo que
    # `./install.sh | tee log` se queda "colgado" al terminar.
    pkill -P "$HEARTBEAT_PID" 2>/dev/null || true
    kill "$HEARTBEAT_PID" 2>/dev/null || true
    wait "$HEARTBEAT_PID" 2>/dev/null || true
    HEARTBEAT_PID=""
    return 0
}

CLEANUP_DONE=0
cleanup() {
    [[ "$CLEANUP_DONE" -eq 1 ]] && return 0
    CLEANUP_DONE=1
    stop_heartbeat
    # Limpiar el lock file para que futuras ejecuciones no queden bloqueadas.
    # Importante especialmente si este script es matado por timeout.
    rm -f "$LOCK_FILE"
    return 0
}
trap cleanup EXIT

on_interrupt() {
    echo ""
    log_warning "Instalación interrumpida por el usuario. Vuelve a ejecutar ./install.sh para reintentar de forma segura."
    exit 130
}
trap on_interrupt INT TERM

# CONTAINERS_TOUCHED marca si ya hemos modificado imágenes o contenedores. El
# rollback solo tiene sentido a partir de ese punto: antes de eso no hay nada
# que revertir y un rollback sería ruido (o peor, revertiría el git pull por un
# error tonto del propio script).
CONTAINERS_TOUCHED=0
ROLLBACK_DONE=0
IMAGE_NAMES_BACKED_UP=()
rollback() {
    [[ "$ROLLBACK_DONE" -eq 1 ]] && return 0
    [[ "$CONTAINERS_TOUCHED" -eq 0 ]] && return 0
    ROLLBACK_DONE=1
    log_warning "Iniciando rollback automático a la versión anterior..."

    if [[ "${#IMAGE_NAMES_BACKED_UP[@]}" -gt 0 ]]; then
        RETAG_OK=1
        for IMAGE_NAME in "${IMAGE_NAMES_BACKED_UP[@]}"; do
            IMAGE_BASE="${IMAGE_NAME%:*}"
            if "${DOCKER[@]}" image inspect "${IMAGE_BASE}:rollback" &> /dev/null; then
                "${DOCKER[@]}" tag "${IMAGE_BASE}:rollback" "$IMAGE_NAME" >> "$LOG_FILE" 2>&1 || RETAG_OK=0
            fi
        done
        # Las imágenes :rollback llevan el nombre anterior: se vuelve también al pin anterior.
        if [[ "${PIN_PREVIO_GUARDADO:-0}" -eq 1 ]]; then fijar_env STOCKHOGAR_IMAGE_TAG "${PIN_PREVIO:-}" || true; fi
        if [[ "$RETAG_OK" -eq 1 ]] && "${COMPOSE[@]}" up -d --force-recreate >> "$LOG_FILE" 2>&1; then
            log_warning "Imágenes Docker revertidas a la versión anterior y contenedores recreados."
        else
            log_error "El rollback de las imágenes Docker también falló; revisa $LOG_FILE manualmente."
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

    log_error "Rollback completado. Revisa $LOG_FILE para ver qué falló antes de reintentar."
}

handle_error() {
    local line="$1" code="$2"
    log_error "Fallo en la línea $line (código $code)"
    log_error "Log completo: $LOG_FILE"
    if [[ ${#COMPOSE[@]} -gt 0 ]] && "${COMPOSE[@]}" ps &> /dev/null; then
        log_error "Últimas líneas de los contenedores (para diagnóstico):"
        "${COMPOSE[@]}" logs --tail=40 2>&1 | tee -a "$LOG_FILE" || true
    fi
    rollback
    exit 1
}
trap 'handle_error ${LINENO} $?' ERR

run() {
    # Ejecuta un comando silenciosamente (solo al log) y aborta si falla,
    # diciendo CUÁL comando reventó (el trap ERR por sí solo no lo dice).
    log_info "\$ $*"
    if ! "$@" >> "$LOG_FILE" 2>&1; then
        log_error "Comando falló: $*"
        log_error "Log completo: $LOG_FILE"
        exit 1
    fi
}

retry() {
    # Reintenta con backoff exponencial. Solo para operaciones de RED cortas
    # (apt, curl): nunca para el build, donde un reintento a ciegas significa
    # repetir 40 minutos de compilación por un error que no se va a arreglar solo.
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

# --- Helpers de contenedores -----------------------------------------------
# Todos acaban en `|| true`: con `set -e` + `pipefail`, una asignación desde una
# substitución que devuelve error aborta el script entero.
container_id() { "${COMPOSE[@]}" ps -q "$1" 2>/dev/null | head -1 || true; }

container_running() {
    # Comprueba el estado real vía `docker inspect` en vez de parsear la tabla
    # de `compose ps`, cuyo formato cambia entre versiones de Compose.
    local cid
    cid="$(container_id "$1")"
    [[ -z "$cid" ]] && return 1
    [[ "$("${DOCKER[@]}" inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" == "true" ]]
}

container_health() {
    # "healthy" | "unhealthy" | "starting" | "none" (sin HEALTHCHECK definido)
    local cid
    cid="$(container_id "$1")"
    [[ -z "$cid" ]] && { echo "none"; return; }
    "${DOCKER[@]}" inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo "none"
}

wait_healthy() {
    # Espera ACOTADA (nunca infinita) a que un servicio esté healthy.
    # Devuelve 0 si está healthy o si no define healthcheck pero corre.
    local service="$1" max_wait="$2" waited=0 health
    while [[ "$waited" -lt "$max_wait" ]]; do
        container_running "$service" || return 1
        health="$(container_health "$service")"
        case "$health" in
            healthy|none) return 0 ;;
            unhealthy)    return 1 ;;
        esac
        sleep 3
        waited=$((waited + 3))
    done
    return 1
}

usage() {
    cat <<EOF
Uso: ./install.sh [--update] [--reinstall] [--no-build] [--help]

  (sin flags)  Instala o reconstruye StockHogar en este directorio.
  --update     Además hace 'git pull --ff-only' antes de reconstruir.
  --reinstall  Descarta cambios locales ('git reset --hard' contra el remoto de
               la rama actual) y reconstruye TODAS las imágenes sin caché
               (--no-cache). No toca data/, .env ni uploads/ (fuera de git).
  --no-build   No reconstruye la imagen; solo recrea los contenedores (rápido).
               Se ignora si se combina con --reinstall.
  --help       Muestra esta ayuda y sale.
EOF
}

UPDATE_MODE=0
REINSTALL_MODE=0
BUILD_MODE=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --update)     UPDATE_MODE=1 ;;
        --reinstall)  REINSTALL_MODE=1 ;;
        --no-build)   BUILD_MODE=0 ;;
        --help|-h)    usage; exit 0 ;;
        *) log_error "Opción desconocida: $1"; usage; exit 1 ;;
    esac
    shift
done
if [[ "$REINSTALL_MODE" -eq 1 ]] && [[ "$BUILD_MODE" -eq 0 ]]; then
    log_warning "--no-build se ignora junto a --reinstall (--reinstall siempre reconstruye sin caché)"
    BUILD_MODE=1
fi

################################################################################
step_start "Detectar sistema y recursos"
################################################################################

if [[ -f /etc/os-release ]] && grep -qiE "raspbian|debian|ubuntu" /etc/os-release; then
    log_success "OS compatible: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
else
    log_warning "SO no reconocido como Debian/Ubuntu/Raspbian; se continúa igualmente"
fi

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|aarch64) log_success "Arquitectura: $ARCH (soportada)" ;;
    armv7l|armv6l)  log_success "Arquitectura: $ARCH (soportada, build lento)"
                    log_warning "En $ARCH no hay onnxruntime: el escáner de tickets usará solo Tesseract" \
                                "(lee peor que el motor neuronal). Con un sistema de 64 bits (aarch64) se activa el motor neuronal." ;;
    *) log_warning "Arquitectura no probada: $ARCH; puede que no existan imágenes base compatibles" ;;
esac

# Leído de /proc/meminfo y NO de `free`: la salida de `free` está traducida
# (en un Raspbian en español la línea de swap es "Inter:", no "Swap:"), así que
# parsearla daba 0MB de swap y disparaba un aviso de OOM falso.
MEMORY_MB="$(awk '/^MemTotal:/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo "")"
SWAP_MB="$(awk '/^SwapTotal:/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo "")"
[[ -z "$SWAP_MB" ]] && SWAP_MB=0
if [[ -n "$MEMORY_MB" ]]; then
    log_success "Memoria: ${MEMORY_MB}MB (swap: ${SWAP_MB:-0}MB)"
    # `next build` con webpack es lo que más RAM consume de todo el proceso.
    # Con <1.5GB entre RAM y swap el kernel mata el build (OOM) a mitad, y en
    # una Pi eso pasa tras 20+ minutos de compilación.
    if [[ "$BUILD_MODE" -eq 1 ]] && [[ $((MEMORY_MB + ${SWAP_MB:-0})) -lt 1536 ]]; then
        log_warning "RAM + swap = $((MEMORY_MB + ${SWAP_MB:-0}))MB. El build de Next.js puede morir por falta de memoria (OOM)."
        log_warning "Recomendado ampliar el swap a 2GB antes de continuar:"
        log_warning "  sudo dphys-swapfile swapoff && sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile && sudo dphys-swapfile setup && sudo dphys-swapfile swapon"
    fi
fi

FREE_DISK_MB="$(df -Pm "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "")"
# El build reconstruye TODAS las capas de golpe (--no-cache, ver más abajo),
# así que necesita el mismo margen tanto en modo normal como en --reinstall.
DISK_MIN_MB=2048; DISK_RECOMENDADO_MB=4096
if [[ -n "$FREE_DISK_MB" ]]; then
    if [[ "$FREE_DISK_MB" -lt "$DISK_MIN_MB" ]]; then
        log_error "Espacio libre: ${FREE_DISK_MB}MB. Insuficiente para construir la imagen (mínimo ${DISK_MIN_MB}MB). Libera espacio y reintenta."
        exit 1
    elif [[ "$FREE_DISK_MB" -lt "$DISK_RECOMENDADO_MB" ]]; then
        log_warning "Espacio libre: ${FREE_DISK_MB}MB (recomendado ${DISK_RECOMENDADO_MB}MB+ para construir con margen)"
    else
        log_success "Espacio libre en disco: ${FREE_DISK_MB}MB"
    fi
fi

if ! [[ -w "$SCRIPT_DIR" ]]; then
    log_error "No hay permiso de escritura en $SCRIPT_DIR; no se pueden crear data/, logs/, uploads/ ni .env"
    exit 1
fi

if check_cmd curl && ! curl -fsS --max-time 8 -o /dev/null https://get.docker.com; then
    log_error "Sin conectividad a internet (no se alcanza get.docker.com). Revisa la red y reintenta."
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

# Un solo `apt-get update`, y solo si falta algo que instalar.
if ! check_cmd curl || ! check_cmd git; then
    log_info "Instalando dependencias del sistema que faltan..."
    retry $SUDO apt-get update -qq
    check_cmd curl || retry $SUDO apt-get install -y -qq curl
    check_cmd git  || retry $SUDO apt-get install -y -qq git
fi
log_success "curl y git disponibles"

step_end

################################################################################
step_start "Instalar Docker"
################################################################################

if check_cmd docker; then
    log_success "Docker ya instalado: $(docker --version)"
else
    log_info "Instalando Docker (script oficial get.docker.com)..."
    DOCKER_SCRIPT="$(mktemp /tmp/get-docker.XXXXXX.sh)"
    retry curl -fsSL https://get.docker.com -o "$DOCKER_SCRIPT"
    run $SUDO sh "$DOCKER_SCRIPT"
    rm -f "$DOCKER_SCRIPT"
    if [[ -n "$SUDO" ]]; then
        run $SUDO usermod -aG docker "$(id -un)"
        log_warning "Se añadió tu usuario al grupo 'docker'. Si algo falla por permisos," \
                    "cierra sesión y vuelve a entrar (o ejecuta: newgrp docker) y relanza este script."
    fi
    log_success "Docker instalado"
fi

if ! $SUDO systemctl is-active --quiet docker 2>/dev/null && ! docker info &> /dev/null; then
    log_info "Arrancando el servicio de Docker..."
    run $SUDO systemctl enable --now docker || run $SUDO service docker start
fi

for i in 1 2 3 4 5; do
    if docker info &> /dev/null; then
        DOCKER=(docker)
        break
    elif [[ -n "$SUDO" ]] && $SUDO docker info &> /dev/null; then
        DOCKER=(sudo docker)
        log_warning "Docker solo responde con sudo (el grupo 'docker' aún no está activo en esta sesión)"
        break
    fi
    log_info "Esperando a que el daemon de Docker esté listo (intento $i/5)..."
    sleep 3
done

if [[ ${#DOCKER[@]} -eq 0 ]]; then
    log_error "El daemon de Docker no responde. Revisa: sudo systemctl status docker"
    exit 1
fi
log_success "Docker operativo: $("${DOCKER[@]}" version --format '{{.Server.Version}}' 2>/dev/null || echo desconocida)"

step_end

################################################################################
step_start "Optimizar el sistema (Raspberry Pi / servidor)"
################################################################################

# Ajustes del sistema operativo que hacen que la app funcione siempre y aguante
# en una Raspberry Pi: swap suficiente, reloj en hora, menos escrituras a la SD,
# reinicio automático si el sistema se cuelga y memoria liberada.
#
# Reglas: cada ajuste es IDEMPOTENTE (se puede ejecutar en cada --update), y
# NINGUNO es fatal: si uno falla se avisa y se sigue, porque un ajuste de
# rendimiento nunca debe impedir instalar la app. Se omite todo con
# DREAME_OPTIMIZAR_SISTEMA=0.
REBOOT_RECOMENDADO=0

# escribir_si_cambia DESTINO  (contenido por stdin) -> 0 si cambió, 1 si ya estaba igual
escribir_si_cambia() {
    local destino="$1" tmp rc
    tmp="$(mktemp)"
    cat > "$tmp"
    if [[ -f "$destino" ]] && cmp -s "$tmp" "$destino"; then
        rm -f "$tmp"
        return 1
    fi
    $SUDO mkdir -p "$(dirname "$destino")" && $SUDO install -m 644 "$tmp" "$destino"
    rc=$?
    rm -f "$tmp"
    return $rc
}

if [[ "${DREAME_OPTIMIZAR_SISTEMA:-1}" == "0" ]]; then
    log_info "DREAME_OPTIMIZAR_SISTEMA=0: se omite la optimización del sistema"
elif [[ ! -d /run/systemd/system ]]; then
    log_info "Sin systemd: se omite la optimización del sistema"
else
    ES_PI=0
    if [[ -r /proc/device-tree/model ]] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
        ES_PI=1
        log_info "Equipo: $(tr -d '\0' < /proc/device-tree/model)"
    fi

    # 1) Swap. Con poca RAM el build de Next, el lector de tickets y Docker juntos
    #    acaban en OOM-kill; 2 GB de swap lo evita. En la SD solo se usa si la RAM se
    #    agota (swappiness baja, más abajo), así que apenas desgasta la tarjeta.
    SWAP_OBJETIVO_MB=2048
    if [[ -n "${MEMORY_MB:-}" ]] && [[ $((MEMORY_MB + ${SWAP_MB:-0})) -lt "$SWAP_OBJETIVO_MB" ]] \
        && [[ "${FREE_DISK_MB:-0}" -gt $((SWAP_OBJETIVO_MB + 2048)) ]]; then
        if [[ -f /etc/dphys-swapfile ]] && check_cmd dphys-swapfile; then
            log_info "Ampliando el swap a ${SWAP_OBJETIVO_MB} MB (dphys-swapfile)"
            {
                $SUDO sed -i "s/^#\?CONF_SWAPSIZE=.*/CONF_SWAPSIZE=${SWAP_OBJETIVO_MB}/" /etc/dphys-swapfile \
                && { if grep -q '^CONF_MAXSWAP=' /etc/dphys-swapfile; then
                         $SUDO sed -i "s/^CONF_MAXSWAP=.*/CONF_MAXSWAP=${SWAP_OBJETIVO_MB}/" /etc/dphys-swapfile
                     else
                         echo "CONF_MAXSWAP=${SWAP_OBJETIVO_MB}" | $SUDO tee -a /etc/dphys-swapfile > /dev/null
                     fi; } \
                && $SUDO dphys-swapfile swapoff \
                && $SUDO dphys-swapfile setup \
                && $SUDO dphys-swapfile swapon
            } >> "$LOG_FILE" 2>&1 \
                && log_success "Swap ampliado a ${SWAP_OBJETIVO_MB} MB" \
                || log_warning "No se pudo ampliar el swap (dphys-swapfile); se continúa"
        elif [[ ! -f /swapfile ]] && ! grep -qE '^\s*/swapfile\s' /etc/fstab 2>/dev/null; then
            log_info "Creando /swapfile de ${SWAP_OBJETIVO_MB} MB"
            {
                $SUDO fallocate -l "${SWAP_OBJETIVO_MB}M" /swapfile \
                && $SUDO chmod 600 /swapfile \
                && $SUDO mkswap /swapfile \
                && $SUDO swapon /swapfile \
                && echo "/swapfile none swap sw 0 0" | $SUDO tee -a /etc/fstab > /dev/null
            } >> "$LOG_FILE" 2>&1 \
                && log_success "Swap creado: /swapfile (${SWAP_OBJETIVO_MB} MB)" \
                || log_warning "No se pudo crear el swap; se continúa"
        fi
    else
        log_success "Memoria + swap suficientes (${MEMORY_MB:-?} MB + ${SWAP_MB:-0} MB)"
    fi

    # 2) Kernel: usar swap solo si hace falta, no vaciar la caché de disco a las
    #    primeras de cambio y agrupar las escrituras (menos paradas de la SD).
    if escribir_si_cambia /etc/sysctl.d/99-dreame.conf <<'EOF'
# Dreame! - ajustes de rendimiento para servidor doméstico (install.sh)
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_background_ratio = 5
vm.dirty_ratio = 20
net.core.somaxconn = 1024
EOF
    then
        $SUDO sysctl -p /etc/sysctl.d/99-dreame.conf >> "$LOG_FILE" 2>&1 \
            && log_success "Parámetros del kernel aplicados (swappiness, caché, escrituras)" \
            || log_warning "No se pudieron aplicar los parámetros del kernel"
    else
        log_info "Parámetros del kernel ya aplicados"
    fi

    # 3) Diario del sistema acotado: sin límite crece sin parar y llena la SD.
    if escribir_si_cambia /etc/systemd/journald.conf.d/99-dreame.conf <<'EOF'
[Journal]
SystemMaxUse=100M
RuntimeMaxUse=50M
Compress=yes
EOF
    then
        $SUDO systemctl restart systemd-journald >> "$LOG_FILE" 2>&1 || true
        log_success "Diario del sistema limitado a 100 MB"
    fi

    # 4) Reloj. Una Pi no tiene reloj con batería: sin NTP arranca con la hora
    #    equivocada y fallan HTTPS, las cookies de sesión y los tokens.
    if check_cmd timedatectl; then
        if [[ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" == "yes" ]]; then
            log_success "Reloj sincronizado por NTP"
        else
            $SUDO timedatectl set-ntp true >> "$LOG_FILE" 2>&1 \
                && log_success "Sincronización horaria (NTP) activada" \
                || log_warning "No se pudo activar NTP: revisa la hora del sistema (date)"
        fi
    fi

    # 5) Docker debe arrancar solo tras un corte de luz.
    for SERVICIO in docker containerd; do
        systemctl is-enabled --quiet "$SERVICIO" 2>/dev/null \
            || $SUDO systemctl enable "$SERVICIO" >> "$LOG_FILE" 2>&1 || true
    done
    log_success "Docker arranca automáticamente con el sistema"

    # 6) Watchdog: si el sistema se cuelga (típico de una Pi sin memoria), el
    #    hardware lo reinicia en vez de dejar la app caída hasta que alguien
    #    enchufe y desenchufe. Solo si existe /dev/watchdog.
    if [[ -e /dev/watchdog ]]; then
        if escribir_si_cambia /etc/systemd/system.conf.d/99-dreame-watchdog.conf <<'EOF'
[Manager]
RuntimeWatchdogSec=30
RebootWatchdogSec=5min
EOF
        then
            $SUDO systemctl daemon-reexec >> "$LOG_FILE" 2>&1 || true
            log_success "Watchdog de hardware activado (reinicio automático si el sistema se cuelga)"
        else
            log_info "Watchdog de hardware ya configurado"
        fi
    else
        log_info "Sin /dev/watchdog: se omite el watchdog"
    fi

    if [[ "$ES_PI" -eq 1 ]]; then
        # 7) Servicios que un servidor sin pantalla no usa (unos 30 MB de RAM y algo de CPU).
        for SERVICIO in bluetooth hciuart ModemManager triggerhappy; do
            if systemctl is-enabled --quiet "$SERVICIO" 2>/dev/null; then
                $SUDO systemctl disable --now "$SERVICIO" >> "$LOG_FILE" 2>&1 \
                    && log_success "Servicio innecesario desactivado: $SERVICIO" || true
            fi
        done

        # 8) Memoria de vídeo: 16 MB bastan sin escritorio y el resto vuelve a la RAM.
        #    Solo se toca si el usuario no la fijó. Surte efecto en el próximo reinicio.
        #    DREAME_GPU_MEM=0 lo omite.
        CONFIG_ARRANQUE=""
        for CANDIDATO in /boot/firmware/config.txt /boot/config.txt; do
            if [[ -f "$CANDIDATO" ]]; then CONFIG_ARRANQUE="$CANDIDATO"; break; fi
        done
        if [[ -n "$CONFIG_ARRANQUE" ]] && [[ "${DREAME_GPU_MEM:-16}" != "0" ]]; then
            if grep -qE '^\s*gpu_mem' "$CONFIG_ARRANQUE"; then
                log_info "gpu_mem ya está definido en $CONFIG_ARRANQUE; no se toca"
            else
                {
                    $SUDO cp "$CONFIG_ARRANQUE" "${CONFIG_ARRANQUE}.dreame.bak" \
                    && printf '\n# Dreame!: sin escritorio, 16 MB de GPU y el resto de RAM para la app\ngpu_mem=%s\n' "${DREAME_GPU_MEM:-16}" \
                       | $SUDO tee -a "$CONFIG_ARRANQUE" > /dev/null
                } >> "$LOG_FILE" 2>&1 \
                    && { log_success "gpu_mem=${DREAME_GPU_MEM:-16} añadido a $CONFIG_ARRANQUE (copia en .dreame.bak)"; REBOOT_RECOMENDADO=1; } \
                    || log_warning "No se pudo ajustar gpu_mem"
            fi
        fi
    fi
fi

step_end

################################################################################
step_start "Reforzar la seguridad del sistema"
################################################################################

# Endurece la Raspberry Pi: parches de seguridad automáticos, cortafuegos,
# bloqueo de intentos de acceso por SSH, SSH más estricto, parámetros de red del
# kernel, daemon de Docker, volcados de memoria y permisos de los ficheros con
# secretos. También AVISA (sin cambiar nada) de lo que depende del usuario: la
# contraseña por defecto de `pi`, el grupo docker y los sudo sin contraseña.
#
# Reglas, igual que en la optimización: IDEMPOTENTE, nada es fatal (un fallo se
# avisa y se sigue) y se omite con DREAME_ENDURECER_SISTEMA=0. Y una regla más:
# NUNCA dejar al usuario sin acceso. Por eso el cortafuegos no se activa sin una
# regla de SSH ya confirmada (y las reglas de permiso van ANTES de la política de
# denegar), el SSH solo se recarga si `sshd -t` valida la configuración (y luego se
# comprueba con `sshd -T` que lo pedido queda de verdad en vigor), y desactivar la
# contraseña de SSH es opt-in explícito (DREAME_SSH_SOLO_CLAVES=1) y solo si hay
# una clave pública autorizada con los permisos que exige sshd.
#   DREAME_REINICIO_AUTOMATICO=1  reinicio automático a las 04:30 si una actualización lo pide.
SEGURIDAD_REINICIAR_SSH=0

# ¿Hay un túnel de Cloudflare en esta máquina? Entonces el tráfico público entra
# por el túnel (que se conecta a localhost) y el frontend no tiene por qué
# escuchar en toda la red local.
hay_tunel() {
    systemctl is-active --quiet cloudflared 2>/dev/null && return 0
    pgrep -x cloudflared >/dev/null 2>&1 && return 0
    docker ps --format '{{.Image}} {{.Names}}' 2>/dev/null | grep -qi cloudflared && return 0
    return 1
}
# Valor de una clave de .env, SIN comillas ni espacios ("127.0.0.1" entrecomillado también vale).
env_previo() { grep -m1 "^${1}=" .env 2>/dev/null | cut -d= -f2- | tr -d "[:space:]\"'" || true; }
# fijar_env CLAVE VALOR: pone la clave en .env (VALOR vacío = la quita). Reescribe el contenido
# sobre el mismo fichero para conservar propietario y permisos.
fijar_env() {
    local clave="$1" valor="${2:-}" tmp
    [[ -f .env ]] || return 0
    tmp="$(mktemp "$SCRIPT_DIR/.env.XXXXXX")" || return 1
    { grep -v "^${clave}=" .env || true; } > "$tmp"
    [[ -n "$valor" ]] && printf '%s=%s\n' "$clave" "$valor" >> "$tmp"
    cat "$tmp" > .env
    rm -f "$tmp"
}
# Permisos de los ficheros con secretos. Se llama aquí y otra vez al final de la instalación,
# cuando .env y data/ ya existen (en la primera instalación este paso corre ANTES de crearlos).
ajustar_permisos_secretos() {
    if [[ -f .env ]]; then chmod 600 .env 2>/dev/null || true; fi
    for SECRETO in data/secret.json data/vapid_private_key.pem; do
        if [[ -f "$SECRETO" ]]; then chmod 600 "$SECRETO" 2>/dev/null || true; fi
    done
    # data/ solo se cierra si es de uid 1000: es el usuario con el que corre el contenedor (appuser).
    # Con otro propietario cerrarlo dejaría al contenedor sin acceso a su propia base de datos.
    if [[ -d data ]] && [[ "$(stat -c %u data 2>/dev/null)" == "1000" ]]; then
        chmod 750 data 2>/dev/null || true
        if [[ -d data/backups ]]; then chmod 750 data/backups 2>/dev/null || true; fi
        if compgen -G 'data/*.db' >/dev/null; then chmod 640 data/*.db 2>/dev/null || true; fi
        if compgen -G 'data/backups/*' >/dev/null; then chmod 640 data/backups/* 2>/dev/null || true; fi
    fi
    if [[ -d "${HOME}/.stockhogar-env-backups" ]]; then chmod 700 "${HOME}/.stockhogar-env-backups" 2>/dev/null || true; fi
}

# Puerto y enlace del frontend tal como estan (o estaran) en .env
FRONTEND_PORT_FW="$(env_previo STOCKHOGAR_FRONTEND_PORT)"; FRONTEND_PORT_FW="${FRONTEND_PORT_FW:-3000}"
FRONTEND_BIND_FW="$(env_previo STOCKHOGAR_FRONTEND_BIND)"
if [[ -z "$FRONTEND_BIND_FW" ]]; then
    if [[ "${DREAME_ABRIR_LAN:-0}" != "1" ]] && hay_tunel; then FRONTEND_BIND_FW="127.0.0.1"; else FRONTEND_BIND_FW="0.0.0.0"; fi
fi

if [[ "${DREAME_ENDURECER_SISTEMA:-1}" == "0" ]]; then
    log_info "DREAME_ENDURECER_SISTEMA=0: se omite el refuerzo de seguridad"
elif [[ ! -d /run/systemd/system ]]; then
    log_info "Sin systemd: se omite el refuerzo de seguridad"
elif ! check_cmd apt-get; then
    log_info "Sin apt: se omite el refuerzo de seguridad (solo Debian/Raspberry Pi OS/Ubuntu)"
else
    # Puerto real de SSH (puede no ser el 22) y si hay un sshd escuchando.
    SSH_PUERTO=""
    if check_cmd sshd; then
        SSH_PUERTO="$($SUDO sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')"
    fi
    if [[ -z "$SSH_PUERTO" ]] && check_cmd ss; then
        SSH_PUERTO="$(ss -ltnp 2>/dev/null | awk '/sshd/{n=split($4,a,":"); print a[n]; exit}')"
    fi
    SSH_ACTIVO=0
    if systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd 2>/dev/null; then
        SSH_ACTIVO=1
    fi
    if [[ "$SSH_ACTIVO" -eq 1 ]]; then SSH_PUERTO="${SSH_PUERTO:-22}"; fi
    # IP desde la que se instala (si es por SSH): fail2ban no debe bloquearla.
    CLIENTE_SSH="${SSH_CONNECTION:-}"; CLIENTE_SSH="${CLIENTE_SSH%% *}"

    PAQUETES_SEGURIDAD=()
    check_cmd ufw || PAQUETES_SEGURIDAD+=(ufw)
    check_cmd fail2ban-client || PAQUETES_SEGURIDAD+=(fail2ban)
    dpkg -s unattended-upgrades >/dev/null 2>&1 || PAQUETES_SEGURIDAD+=(unattended-upgrades)
    if [[ "${#PAQUETES_SEGURIDAD[@]}" -gt 0 ]]; then
        log_info "Instalando paquetes de seguridad: ${PAQUETES_SEGURIDAD[*]}"
        {
            $SUDO apt-get update -qq \
            && DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${PAQUETES_SEGURIDAD[@]}"
        } >> "$LOG_FILE" 2>&1 \
            && log_success "Paquetes de seguridad instalados" \
            || log_warning "No se pudieron instalar todos los paquetes de seguridad; se aplica lo que haya"
    fi

    # 1) Parches de seguridad automáticos: Debian-Security (por defecto) y el repositorio de
    #    Raspberry Pi (kernel, firmware). Docker NO entra: actualizar el daemon reinicia los
    #    contenedores sin avisar. El reinicio automático es opt-in.
    if dpkg -s unattended-upgrades >/dev/null 2>&1; then
        if escribir_si_cambia /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
        then
            log_success "Parches de seguridad automáticos activados (unattended-upgrades)"
        else
            log_info "Parches de seguridad automáticos ya activados"
        fi
        UNATTENDED_EXTRA='Unattended-Upgrade::Origins-Pattern:: "origin=Raspberry Pi Foundation,codename=${distro_codename}";
Unattended-Upgrade::Remove-Unused-Dependencies "true";'
        if [[ "${DREAME_REINICIO_AUTOMATICO:-0}" == "1" ]]; then
            UNATTENDED_EXTRA+=$'\nUnattended-Upgrade::Automatic-Reboot "true";\nUnattended-Upgrade::Automatic-Reboot-Time "04:30";'
        fi
        printf '%s\n' "$UNATTENDED_EXTRA" | escribir_si_cambia /etc/apt/apt.conf.d/52dreame-unattended \
            && log_success "unattended-upgrades: repositorio de Raspberry Pi incluido$([[ "${DREAME_REINICIO_AUTOMATICO:-0}" == "1" ]] && echo ', reinicio automático 04:30')" || true
    fi

    # 2) Parámetros de red y del kernel (sin tocar ip_forward: Docker lo necesita).
    if escribir_si_cambia /etc/sysctl.d/99-dreame-seguridad.conf <<'EOF'
# Dreame! - endurecimiento del kernel (install.sh)
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
kernel.yama.ptrace_scope = 1
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.protected_fifos = 2
fs.protected_regular = 2
fs.suid_dumpable = 0
EOF
    then
        # sysctl -p sigue con el resto aunque una clave no exista en este kernel (devuelve error al final).
        $SUDO sysctl -p /etc/sysctl.d/99-dreame-seguridad.conf >> "$LOG_FILE" 2>&1 \
            && log_success "Parámetros de red y kernel endurecidos" \
            || log_warning "Algún parámetro del kernel no se pudo aplicar (kernel sin soporte); el resto sí"
    else
        log_info "Parámetros de seguridad del kernel ya aplicados"
    fi

    # Sin volcados de memoria (core dumps): un proceso que cae no deja en disco su memoria,
    # que puede llevar contraseñas y claves.
    escribir_si_cambia /etc/security/limits.d/99-dreame.conf <<'EOF' && log_success "Volcados de memoria desactivados"
# Dreame! (install.sh)
* hard core 0
EOF

    # 3) SSH más estricto. Un fichero propio en sshd_config.d (no se edita el sshd_config del
    #    sistema) que se valida con `sshd -t` antes de recargar. Se llama 00-dreame.conf, NO 99:
    #    sshd se queda con el PRIMER valor que lee de cada clave y los ficheros se leen en orden
    #    alfabético, así que un 50-cloud-init.conf con PasswordAuthentication yes anulaba el 99.
    if [[ "$SSH_ACTIVO" -eq 1 ]] && [[ -d /etc/ssh/sshd_config.d ]]; then
        SSH_SOLO_CLAVES=0
        if [[ "${DREAME_SSH_SOLO_CLAVES:-0}" == "1" ]]; then
            CLAVES_SSH="${HOME}/.ssh/authorized_keys"
            if [[ -s "$CLAVES_SSH" ]] && grep -qE '^(ssh-|ecdsa-|sk-)' "$CLAVES_SSH"; then
                # sshd (StrictModes) ignora authorized_keys si ~ o ~/.ssh o el fichero los puede escribir
                # otros: con la contraseña ya desactivada eso es quedarse sin acceso.
                if [[ -n "$(find "${HOME}" "${HOME}/.ssh" "$CLAVES_SSH" -maxdepth 0 -perm /022 2>/dev/null)" ]] \
                    || [[ "$(stat -c %u "$CLAVES_SSH" 2>/dev/null)" != "$(id -u)" ]]; then
                    log_warning "DREAME_SSH_SOLO_CLAVES=1 ignorado: ${HOME}, ${HOME}/.ssh o authorized_keys son escribibles por otros (sshd los ignoraría)."
                    log_warning "Arréglalo con: chmod go-w ~ ; chmod 700 ~/.ssh ; chmod 600 ~/.ssh/authorized_keys"
                else
                    SSH_SOLO_CLAVES=1
                fi
            else
                log_warning "DREAME_SSH_SOLO_CLAVES=1 ignorado: ${HOME}/.ssh/authorized_keys no tiene ninguna clave pública."
                log_warning "Copia tu clave primero (ssh-copy-id) o te quedarías sin acceso."
            fi
        fi
        SSH_CONF_NUEVA="$(mktemp)"
        {
            echo "# Dreame! - SSH más estricto (install.sh). Se puede borrar este fichero para revertirlo."
            echo "MaxAuthTries 6"
            echo "LoginGraceTime 30"
            echo "X11Forwarding no"
            echo "ClientAliveInterval 300"
            echo "ClientAliveCountMax 2"
            echo "PermitEmptyPasswords no"
            # Solo se prohíbe root si quien instala NO es root: si no, nadie más podría entrar.
            if [[ "$(id -u)" -ne 0 ]]; then echo "PermitRootLogin no"; fi
            if [[ "$SSH_SOLO_CLAVES" -eq 1 ]]; then echo "PasswordAuthentication no"; echo "KbdInteractiveAuthentication no"; fi
        } > "$SSH_CONF_NUEVA"
        SSH_CONF=/etc/ssh/sshd_config.d/00-dreame.conf
        SSH_CONF_ANTIGUO=/etc/ssh/sshd_config.d/99-dreame.conf   # nombre de versiones anteriores
        if [[ -f "$SSH_CONF" ]] && cmp -s "$SSH_CONF_NUEVA" "$SSH_CONF" && [[ ! -f "$SSH_CONF_ANTIGUO" ]]; then
            log_info "SSH ya endurecido"
        else
            SSH_CONF_ANTERIOR=""
            if [[ -f "$SSH_CONF" ]]; then SSH_CONF_ANTERIOR="$(cat "$SSH_CONF")"; fi
            $SUDO install -m 644 "$SSH_CONF_NUEVA" "$SSH_CONF"
            if $SUDO sshd -t >> "$LOG_FILE" 2>&1; then
                $SUDO rm -f "$SSH_CONF_ANTIGUO"
                { $SUDO systemctl reload ssh 2>/dev/null || $SUDO systemctl reload sshd 2>/dev/null; } >> "$LOG_FILE" 2>&1 \
                    && log_success "SSH endurecido (intentos limitados, sin root$([[ "$SSH_SOLO_CLAVES" -eq 1 ]] && echo ', solo claves'))" \
                    || log_warning "SSH configurado pero no se pudo recargar; se aplicará al reiniciar el servicio"
                # ¿Queda de verdad en vigor? (otro fichero o el sshd_config pueden anular lo pedido)
                SSH_EFECTIVO="$($SUDO sshd -T 2>/dev/null)"
                for PAR_SSH in "maxauthtries 6" "permitemptypasswords no" "x11forwarding no"; do
                    grep -qi "^${PAR_SSH}\$" <<<"$SSH_EFECTIVO" \
                        || log_warning "SSH: '${PAR_SSH}' NO está en vigor (¿otro fichero de sshd_config.d lo anula?). Revisa: sudo sshd -T"
                done
                if [[ "$SSH_SOLO_CLAVES" -eq 1 ]]; then
                    grep -qi "^passwordauthentication no\$" <<<"$SSH_EFECTIVO" \
                        || log_warning "SSH: la contraseña SIGUE permitida (otro fichero la activa). Revisa: sudo sshd -T | grep -i passwordauth"
                fi
            else
                log_warning "La configuración de SSH no valida (sshd -t): se revierte y no se toca"
                if [[ -n "$SSH_CONF_ANTERIOR" ]]; then
                    printf '%s\n' "$SSH_CONF_ANTERIOR" | $SUDO tee "$SSH_CONF" > /dev/null
                else
                    $SUDO rm -f "$SSH_CONF"
                fi
            fi
        fi
        rm -f "$SSH_CONF_NUEVA"
        if [[ "$SSH_SOLO_CLAVES" -eq 0 ]]; then
            log_info "Consejo: para desactivar la contraseña de SSH, copia tu clave (ssh-copy-id) y relanza con DREAME_SSH_SOLO_CLAVES=1"
        fi
    fi

    # 4) fail2ban: bloquea durante una hora a quien falle 5 veces seguidas en SSH. No bloquea
    #    la IP desde la que se está instalando (un despiste de contraseña no debe dejarte fuera).
    if check_cmd fail2ban-client; then
        IGNORAR_IP="127.0.0.1/8 ::1"
        if [[ -n "$CLIENTE_SSH" ]]; then IGNORAR_IP+=" $CLIENTE_SSH"; fi
        if escribir_si_cambia /etc/fail2ban/jail.d/dreame.local <<EOF
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd
ignoreip = ${IGNORAR_IP}

[sshd]
enabled = true
port    = ${SSH_PUERTO:-22}
EOF
        then
            $SUDO systemctl enable --now fail2ban >> "$LOG_FILE" 2>&1 || true
            $SUDO systemctl restart fail2ban >> "$LOG_FILE" 2>&1 || true
            log_success "fail2ban activo (SSH: 5 fallos → 1 hora de bloqueo)"
        else
            $SUDO systemctl enable --now fail2ban >> "$LOG_FILE" 2>&1 || true
            log_info "fail2ban ya configurado"
        fi
        # backend=systemd necesita el módulo de Python para leer el diario; si falta, el jail no arranca.
        if ! $SUDO fail2ban-client status sshd >/dev/null 2>&1; then
            log_warning "El jail sshd de fail2ban no está activo: instala python3-systemd (sudo apt install python3-systemd) y reinicia fail2ban"
        fi
    fi

    # 5) Cortafuegos. Política: todo lo entrante denegado salvo SSH y, si el frontend escucha
    #    en la red local, su puerto SOLO desde redes privadas. Las reglas de PERMISO se añaden
    #    ANTES de la política de denegar. OJO: Docker publica sus puertos saltándose ufw, así que
    #    la protección real del puerto 3000 es su enlace (STOCKHOGAR_FRONTEND_BIND en .env), no
    #    esta regla.
    if check_cmd ufw; then
        if [[ "$SSH_ACTIVO" -eq 1 ]] || [[ "${DREAME_UFW_SIN_SSH:-0}" == "1" ]]; then
            {
                if [[ "$SSH_ACTIVO" -eq 1 ]]; then $SUDO ufw limit "${SSH_PUERTO}/tcp" comment 'SSH (limitado)' || true; fi
                if [[ "$FRONTEND_BIND_FW" != "127.0.0.1" ]]; then
                    for RED_PRIVADA in 192.168.0.0/16 10.0.0.0/8 172.16.0.0/12; do
                        $SUDO ufw allow from "$RED_PRIVADA" to any port "$FRONTEND_PORT_FW" proto tcp comment 'Dreame! frontend (red local)' || true
                    done
                fi
            } >> "$LOG_FILE" 2>&1
            # `ufw show added` lista las reglas aunque ufw aún esté inactivo.
            if [[ "$SSH_ACTIVO" -eq 0 ]] || $SUDO ufw show added 2>/dev/null | grep -qE "ufw (limit|allow) ${SSH_PUERTO}/tcp"; then
                {
                    $SUDO ufw default deny incoming \
                    && $SUDO ufw default allow outgoing \
                    && $SUDO ufw --force enable
                } >> "$LOG_FILE" 2>&1 \
                    && log_success "Cortafuegos (ufw) activo: entrante denegado salvo SSH${SSH_PUERTO:+ (puerto $SSH_PUERTO)} y red local al frontend" \
                    || log_warning "No se pudo activar ufw"
            else
                log_warning "No se confirmó la regla de SSH en ufw: NO se activa el cortafuegos para no dejarte sin acceso"
            fi
        else
            log_warning "No hay sshd activo: no se activa ufw automáticamente (DREAME_UFW_SIN_SSH=1 para forzarlo si usas teclado y pantalla)"
        fi
    fi

    # 6) Docker: sin privilegios nuevos por defecto, los contenedores sobreviven a un reinicio del
    #    daemon (live-restore) y los logs rotan para todo contenedor. Se FUSIONA con el
    #    daemon.json existente (solo se añaden las claves que faltan) y no se toca uno ilegible.
    if check_cmd docker && check_cmd python3; then
        DAEMON_JSON=/etc/docker/daemon.json
        DAEMON_NUEVO="$(mktemp)"
        if $SUDO cat "$DAEMON_JSON" 2>/dev/null | python3 -c '
import json, sys
texto = sys.stdin.read().strip()
try:
    d = json.loads(texto) if texto else {}
except Exception:
    sys.exit(3)
d.setdefault("live-restore", True)
d.setdefault("no-new-privileges", True)
d.setdefault("log-driver", "json-file")
opciones = d.setdefault("log-opts", {})
opciones.setdefault("max-size", "10m")
opciones.setdefault("max-file", "3")
print(json.dumps(d, indent=2, sort_keys=True))
' > "$DAEMON_NUEVO"; then
            if [[ -f "$DAEMON_JSON" ]] && cmp -s "$DAEMON_NUEVO" "$DAEMON_JSON"; then
                log_info "daemon.json de Docker ya endurecido"
            else
                if [[ -f "$DAEMON_JSON" ]]; then $SUDO cp "$DAEMON_JSON" "${DAEMON_JSON}.dreame.bak"; fi
                $SUDO mkdir -p /etc/docker && $SUDO install -m 644 "$DAEMON_NUEVO" "$DAEMON_JSON"
                if [[ -z "$(docker ps -q 2>/dev/null)" ]]; then
                    $SUDO systemctl restart docker >> "$LOG_FILE" 2>&1 \
                        && log_success "daemon.json de Docker endurecido (no-new-privileges, live-restore, logs rotados)" \
                        || log_warning "daemon.json escrito pero Docker no reinició: revisa 'sudo journalctl -u docker'"
                else
                    # Hay contenedores en marcha: no se reinicia Docker ahora (cortaría el servicio).
                    log_success "daemon.json de Docker endurecido; se aplicará la próxima vez que reinicie Docker o la Pi"
                fi
            fi
        else
            log_warning "/etc/docker/daemon.json no se pudo interpretar como JSON: no se toca"
        fi
        rm -f "$DAEMON_NUEVO"
    fi

    # 7) Servicios de red que un servidor sin escritorio no usa (impresión y RPC/NFS).
    for SERVICIO in cups cups-browsed rpcbind; do
        if systemctl is-enabled --quiet "$SERVICIO" 2>/dev/null; then
            $SUDO systemctl disable --now "$SERVICIO" "${SERVICIO}.socket" >> "$LOG_FILE" 2>&1 \
                && log_success "Servicio de red innecesario desactivado: $SERVICIO" || true
        fi
    done

    # 8) Permisos de los ficheros con secretos.
    ajustar_permisos_secretos
    log_success ".env, claves y base de datos con permisos restringidos"

    # 9) AVISOS (no se cambia nada: dependen del usuario).
    #    - Contraseña por defecto del usuario `pi`.
    if id pi >/dev/null 2>&1; then
        HASH_PI="$($SUDO awk -F: '$1=="pi"{print $2}' /etc/shadow 2>/dev/null)"
        if [[ "$HASH_PI" == \$* ]] && check_cmd python3; then
            printf '%s' "$HASH_PI" | python3 -c '
import sys
try:
    import crypt
except ImportError:
    sys.exit(2)
h = sys.stdin.read()
sys.exit(0 if crypt.crypt("raspberry", h) == h else 1)
' 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log_warning "El usuario 'pi' tiene la contraseña POR DEFECTO (raspberry): cualquiera en tu red entra por SSH. Cámbiala YA: passwd"
            fi
        fi
    fi
    #    - Quien está en el grupo docker equivale a root.
    MIEMBROS_DOCKER="$(getent group docker 2>/dev/null | cut -d: -f4)"
    if [[ -n "$MIEMBROS_DOCKER" ]]; then
        log_info "Usuarios del grupo docker (equivale a ser root): $MIEMBROS_DOCKER"
    fi
    if $SUDO grep -rqsE '^[^#]*NOPASSWD' /etc/sudoers /etc/sudoers.d 2>/dev/null; then
        log_info "Hay reglas sudo NOPASSWD (normal en Raspberry Pi OS): quien consiga una sesión de ese usuario tiene root sin contraseña."
    fi

    # 10) Informe de lo que escucha en la red (lo que no debería estar ahí se ve aquí).
    if check_cmd ss; then
        ABIERTOS="$(ss -ltnH 2>/dev/null | awk '{print $4}' | grep -vE '^(127\.|\[::1\]|::1)' | sed 's/.*://' | sort -un | tr '\n' ' ')"
        log_info "Puertos TCP escuchando fuera de loopback: ${ABIERTOS:-ninguno}"
    fi
fi

step_end

################################################################################
step_start "Detectar Docker Compose"
################################################################################

# `--progress plain` es un flag GLOBAL de Compose v2 (va antes del subcomando:
# `docker compose --progress plain build`); ponerlo detrás de `build` funciona
# pero imprime un aviso de deprecación. En v1 no existe y no se pasa.
COMPOSE_FLAGS=()

if "${DOCKER[@]}" compose version &> /dev/null; then
    COMPOSE=("${DOCKER[@]}" compose)
    COMPOSE_FLAGS=(--progress plain)
    log_success "Docker Compose (plugin v2): $("${DOCKER[@]}" compose version --short 2>/dev/null)"
elif check_cmd docker-compose; then
    COMPOSE=(docker-compose)
    log_warning "Usando docker-compose v1 (binario independiente). Se recomienda migrar al plugin v2."
else
    log_info "Instalando docker-compose-plugin..."
    retry $SUDO apt-get update -qq
    retry $SUDO apt-get install -y -qq docker-compose-plugin
    if "${DOCKER[@]}" compose version &> /dev/null; then
        COMPOSE=("${DOCKER[@]}" compose)
        COMPOSE_FLAGS=(--progress plain)
        log_success "Docker Compose (plugin v2) instalado: $("${DOCKER[@]}" compose version --short 2>/dev/null)"
    else
        log_error "No se pudo instalar Docker Compose. Manual: https://docs.docker.com/compose/install/linux/"
        exit 1
    fi
fi

step_end

################################################################################
step_start "Verificar estructura del proyecto"
################################################################################

MISSING=0
for FILE in "Dockerfile.raspbian" "docker-compose.yml" "requirements.txt" "stockhogar/__init__.py" \
            "stockhogar/integraciones/ocr_rapid.py" "stockhogar/servicios/ocr/diccionario/__init__.py" \
            "stockhogar/servicios/ocr/diccionario/datos_off.py" "stockhogar/servicios/ocr/cuadre_ticket.py" \
            "public/manifest.json" "public/icon.png" \
            "Dockerfile.frontend" "package.json" "next.config.mjs"; do
    if [[ ! -f "$FILE" ]]; then
        log_error "Falta: $FILE"
        MISSING=1
    fi
done

if [[ $MISSING -eq 1 ]]; then
    log_error "Estructura del proyecto incompleta. ¿Se ejecutó el script dentro del repo clonado?"
    log_error "Los iconos y el manifest PWA viven en 'public/' (frontend Next.js)" \
              "y deben estar ya commiteados; este script no los genera."
    exit 1
fi
log_success "Proyecto verificado (incluye iconos PWA y manifest)"

# Toda carpeta de fuentes importada con el alias "@/" tiene que estar copiada en
# Dockerfile.frontend. Si falta, el build no falla al copiar: falla 7 minutos más
# tarde con "Module not found", ya dentro de `next build`. Comprobarlo aquí
# cuesta un segundo y evita ese viaje en balde.
MISSING_COPY=""
while read -r DIR; do
    [[ -z "$DIR" || ! -d "$DIR" ]] && continue
    grep -qE "^COPY +${DIR}(/\.)? +" Dockerfile.frontend || MISSING_COPY+=" $DIR"
done < <(grep -rhoE "from '@/[a-zA-Z0-9_-]+/" app components contexts hooks lib 2>/dev/null \
         | sed "s|from '@/||; s|/$||" | sort -u)

if [[ -n "$MISSING_COPY" ]]; then
    log_error "Dockerfile.frontend no copia estas carpetas, que sí se importan con '@/':${MISSING_COPY}"
    log_error "El build de Next.js fallaría con \"Module not found\". Añade en Dockerfile.frontend:"
    for DIR in $MISSING_COPY; do log_error "  COPY $DIR ./$DIR"; done
    exit 1
fi
log_success "Dockerfile.frontend copia todas las carpetas que importa el alias '@/'"

step_end

################################################################################
step_start "Actualizar código (git pull)"
################################################################################

if [[ "${STOCKHOGAR_REEXEC:-0}" -eq 1 ]]; then
    # Segunda pasada tras el re-exec de abajo: el código ya se actualizó en
    # la primera pasada, solo se recupera PREV_GIT_COMMIT para el rollback.
    PREV_GIT_COMMIT="${STOCKHOGAR_PREV_GIT_COMMIT:-}"
    log_info "Continuando con el código ya actualizado a $(git rev-parse --short HEAD)."
elif [[ $REINSTALL_MODE -eq 1 ]]; then
    if [[ -d .git ]]; then
        PREV_GIT_COMMIT="$(git rev-parse HEAD)"
        log_info "Commit actual (para rollback si algo falla): $PREV_GIT_COMMIT"
        RAMA_ACTUAL="$(git rev-parse --abbrev-ref HEAD)"
        log_warning "--reinstall: se descartará cualquier cambio local de código (git reset --hard)"
        run git fetch --all
        # Firma del commit (opt-in: solo si existe el fichero de firmantes, ver scripts/verificar_firma.sh)
        if [[ -f scripts/verificar_firma.sh ]] && ! bash scripts/verificar_firma.sh "origin/${RAMA_ACTUAL}"; then
            log_error "Se aborta: el código a instalar no está firmado por un firmante de confianza."
            exit 1
        fi
        run git reset --hard "origin/${RAMA_ACTUAL}"
        log_success "Código reinstalado desde origin/${RAMA_ACTUAL} a $(git rev-parse --short HEAD)"
        # El git reset de arriba puede haber modificado este propio fichero:
        # bash ya tiene bufferizado en memoria el resto del script leído
        # ANTES del reset, así que seguir sin más ejecutaría código
        # potencialmente obsoleto. Se relanza para garantizar que el resto
        # de pasos corre con el contenido ya actualizado en disco.
        log_info "Relanzando install.sh para aplicar cualquier cambio en el propio script..."
        STOCKHOGAR_REEXEC=1 STOCKHOGAR_PREV_GIT_COMMIT="$PREV_GIT_COMMIT" \
            exec bash "$SCRIPT_DIR/install.sh" "${ORIGINAL_ARGS[@]}"
    else
        log_warning "No es un repositorio git; se omite git fetch/reset"
    fi
elif [[ $UPDATE_MODE -eq 1 ]]; then
    if [[ -d .git ]]; then
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            log_error "Hay cambios locales sin commitear; 'git pull --ff-only' podría fallar o perder trabajo."
            log_error "Guárdalos (git stash) o descártalos (git checkout -- .) antes de usar --update."
            log_error "Ficheros afectados:"
            git diff --name-only 2>/dev/null | tee -a "$LOG_FILE"
            exit 1
        fi
        PREV_GIT_COMMIT="$(git rev-parse HEAD)"
        log_info "Commit actual (para rollback si algo falla): $PREV_GIT_COMMIT"
        run git fetch origin
        RAMA_SEGUIDA="$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null || echo origin/produccion)"
        if [[ -f scripts/verificar_firma.sh ]] && ! bash scripts/verificar_firma.sh "$RAMA_SEGUIDA"; then
            log_error "Se aborta: el código a instalar no está firmado por un firmante de confianza."
            exit 1
        fi
        run git pull --ff-only
        log_success "Código actualizado a $(git rev-parse --short HEAD)"
        # Mismo motivo que en --reinstall: garantizar que lo que sigue corre
        # con el script ya actualizado, no con lo que bash tenía bufferizado.
        log_info "Relanzando install.sh para aplicar cualquier cambio en el propio script..."
        STOCKHOGAR_REEXEC=1 STOCKHOGAR_PREV_GIT_COMMIT="$PREV_GIT_COMMIT" \
            exec bash "$SCRIPT_DIR/install.sh" "${ORIGINAL_ARGS[@]}"
    else
        log_warning "No es un repositorio git; se omite git pull"
    fi
else
    log_info "Modo instalación (usa --update para además hacer git pull, o --reinstall para descartar cambios locales)"
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
    DB_BACKUP_FILE="data/backups/stock-$(date +%Y%m%d-%H%M%S).db"
    if ! cp "data/stock.db" "$DB_BACKUP_FILE" || [[ ! -s "$DB_BACKUP_FILE" ]]; then
        log_error "El backup de la base de datos falló o quedó vacío; se aborta antes de tocar los contenedores."
        exit 1
    fi
    log_success "Backup creado: $DB_BACKUP_FILE"
    # Nos quedamos con las 5 copias más recientes para no llenar el disco.
    ls -1t data/backups/stock-*.db 2>/dev/null | tail -n +6 | xargs -r rm -f || true
else
    log_info "No hay base de datos previa; se creará una nueva al arrancar"
fi

step_end

################################################################################
step_start "Configurar variables de entorno (.env)"
################################################################################

# El .env real del usuario NUNCA se sobrescribe: si no existe se crea desde
# .env.example, y si existe solo se le añaden las claves que falten.
REQUIRED_VARS=(
    GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET
    SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_FROM
    APP_URL
    STOCKHOGAR_PORT
    STOCKHOGAR_FRONTEND_PORT
    FLASK_ENV
    # Escáner de tickets: motor de nube opcional (sin clave se usa el lector local)
    # y límite de memoria del backend (el lector neuronal necesita ~450 MB de pico).
    ANTHROPIC_API_KEY
    STOCKHOGAR_MEM_LIMIT
    # Concurrencia de gunicorn (Dockerfile / Dockerfile.raspbian): se ajusta a la RAM.
    GUNICORN_WORKERS
    GUNICORN_THREADS
    # Interfaz en la que escucha el frontend: 127.0.0.1 si hay túnel de Cloudflare
    # (nada de la LAN llega a él), 0.0.0.0 para usarlo desde la red local.
    STOCKHOGAR_FRONTEND_BIND
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
        # armv7l no tiene el motor neuronal, y con menos de ~1,5 GB de RAM no cabe
        # el límite de 1 GB sin ahogar al resto: se queda en 768m como antes.
        STOCKHOGAR_MEM_LIMIT)
            if [[ "$ARCH" == armv7l || "$ARCH" == armv6l ]] || [[ -n "${MEMORY_MB:-}" && "$MEMORY_MB" -lt 1500 ]]; then
                echo "768m"
            else
                echo "1024m"
            fi ;;
        # Cada worker carga la app entera (y el lector neuronal): con poca RAM un solo
        # worker con más hilos rinde mejor que dos que se pelean por la memoria. Los
        # hilos comparten memoria y atienden además los análisis de tickets en segundo plano.
        GUNICORN_WORKERS)
            if [[ -n "${MEMORY_MB:-}" && "$MEMORY_MB" -lt 1500 ]]; then echo "1"; else echo "2"; fi ;;
        GUNICORN_THREADS)
            if [[ -n "${MEMORY_MB:-}" && "$MEMORY_MB" -lt 1500 ]]; then echo "6"; else echo "4"; fi ;;
        # Con túnel de Cloudflare el frontend solo escucha en loopback: docker publica
        # sus puertos saltándose ufw, así que el enlace ES el cortafuegos. DREAME_ABRIR_LAN=1
        # lo deja abierto a la red local.
        STOCKHOGAR_FRONTEND_BIND) echo "$FRONTEND_BIND_FW" ;;
        *) echo "" ;;
    esac
}

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp ".env.example" ".env"
        log_success ".env creado a partir de .env.example"
    else
        : > ".env"
        log_success ".env creado vacío"
    fi
else
    # El respaldo del .env NO puede vivir en data/backups/: ese directorio lo
    # sirve por HTTP el Panel de Gestion para descargar copias de seguridad, y
    # el .env lleva en claro las credenciales OAuth de Google, la
    # contraseña SMTP, la API key de Anthropic y la de Postgres. Va a un
    # directorio del usuario, fuera del volumen que se monta en el contenedor,
    # y con permisos 600 desde el momento de crearlo (install -m, no cp).
    ENV_BACKUP_DIR="${HOME}/.stockhogar-env-backups"
    mkdir -p "$ENV_BACKUP_DIR" && chmod 700 "$ENV_BACKUP_DIR"
    install -m 600 ".env" "$ENV_BACKUP_DIR/env-$(date +%Y%m%d-%H%M%S).bak"
    ls -1t "$ENV_BACKUP_DIR"/env-*.bak 2>/dev/null | tail -n +6 | xargs -r rm -f || true
    # Limpieza de las copias que las versiones anteriores dejaron expuestas.
    ls -1 data/backups/env-*.bak 2>/dev/null | xargs -r shred -u 2>/dev/null \
        || rm -f data/backups/env-*.bak 2>/dev/null || true
    log_info ".env ya existe: se conservan los valores actuales (respaldado antes de tocarlo)"
fi

for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" ".env" 2>/dev/null; then
        echo "${VAR}=$(DEFAULT_VALUE "$VAR")" >> ".env"
        log_info "Añadida variable faltante: $VAR"
    fi
done

# Leer los DOS puertos aquí, juntos: el paso final los necesita y si alguno
# quedara sin definir el script moriría por `set -u` justo después del build.
env_value() { grep -m1 "^${1}=" .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true; }

valid_port() { [[ "$1" =~ ^[0-9]+$ ]] && [[ "$1" -ge 1 ]] && [[ "$1" -le 65535 ]]; }

STOCKHOGAR_PORT="$(env_value STOCKHOGAR_PORT)"; STOCKHOGAR_PORT="${STOCKHOGAR_PORT:-5000}"
FRONTEND_PORT="$(env_value STOCKHOGAR_FRONTEND_PORT)"; FRONTEND_PORT="${FRONTEND_PORT:-3000}"

for P in STOCKHOGAR_PORT FRONTEND_PORT; do
    if ! valid_port "${!P}"; then
        log_error "$P='${!P}' en .env no es un puerto válido (1-65535)."
        exit 1
    fi
done
log_success "Puertos: backend ${STOCKHOGAR_PORT}, frontend ${FRONTEND_PORT}"

# Si un puerto está ocupado por algo que NO es este stack, avisamos ahora en vez
# de dejar que `compose up` falle de forma confusa más tarde.
if check_cmd ss; then
    STACK_UP=0
    "${COMPOSE[@]}" ps -q 2>/dev/null | grep -q . && STACK_UP=1 || true
    for P in "$STOCKHOGAR_PORT" "$FRONTEND_PORT"; do
        if ss -ltn 2>/dev/null | grep -q ":${P} " && [[ "$STACK_UP" -eq 0 ]]; then
            log_error "El puerto ${P} está en uso por otro proceso y no hay contenedores de este proyecto corriendo."
            log_error "Cambia el puerto en .env o libera el puerto."
            exit 1
        fi
    done
    [[ "$STACK_UP" -eq 1 ]] && log_info "Ya hay contenedores de este stack en marcha; se reconstruirá sobre ellos."
fi

if [[ -z "$(env_value GOOGLE_CLIENT_ID)" ]]; then
    log_warning "GOOGLE_CLIENT_ID vacío: el login con Google no funcionará (el resto de la app sí)."
fi

step_end

################################################################################
step_start "Validar configuración de Docker Compose"
################################################################################

# .env ya existe: solo su propietario lo lee (lleva claves SMTP/OAuth/API).
if [[ -f .env ]]; then chmod 600 .env 2>/dev/null || true; fi

if ! "${COMPOSE[@]}" config -q 2>>"$LOG_FILE"; then
    log_error "docker-compose.yml (o el .env) no es válido:"
    tail -n 20 "$LOG_FILE"
    exit 1
fi
log_success "docker-compose.yml válido"

step_end

################################################################################
step_start "Guardar las imágenes actuales (rollback)"
################################################################################

# Se hace ANTES del pull: con las imágenes precompiladas el build se omite, y el pull
# pisaría :latest sin haber guardado nada (el rollback no tendría a qué volver).
# Cada servicio se guarda como :rollback. Se recuerda también el pin de versión actual.
PIN_PREVIO="$(env_previo STOCKHOGAR_IMAGE_TAG)"
PIN_PREVIO_GUARDADO=1
mapfile -t IMAGE_NAMES < <("${COMPOSE[@]}" config --images 2>/dev/null)
IMAGE_NAMES_BACKED_UP=()
for IMAGE_NAME in "${IMAGE_NAMES[@]}"; do
    if "${DOCKER[@]}" image inspect "$IMAGE_NAME" &> /dev/null; then
        CONTAINERS_TOUCHED=1
        IMAGE_BASE="${IMAGE_NAME%:*}"
        run "${DOCKER[@]}" tag "$IMAGE_NAME" "${IMAGE_BASE}:rollback"
        IMAGE_NAMES_BACKED_UP+=("$IMAGE_NAME")
        log_info "Imagen anterior guardada como ${IMAGE_BASE}:rollback"
    fi
done
if [[ "${#IMAGE_NAMES_BACKED_UP[@]}" -eq 0 ]]; then log_info "No hay imagen anterior que respaldar (primera instalación)"; fi

step_end

################################################################################
step_start "Descargar imágenes precompiladas (GHCR)"
################################################################################

# Despliegue por commit: docker-publish.yml etiqueta cada imagen con el commit exacto que pasó
# el CI. Si las imágenes de ESTE commit ya existen en GHCR se fija STOCKHOGAR_IMAGE_TAG en .env
# y el compose las usa (código e imagen de la misma versión; un :latest pisado no se cuela).
# Si no se puede saber o aún no están, se usa :latest como siempre (nunca bloquea).
if [[ "$BUILD_MODE" -ne 0 && "$REINSTALL_MODE" -eq 0 && ( "$ARCH" == "armv7l" || "$ARCH" == "armv6l" ) ]] \
    && [[ -f scripts/imagen_publicada.sh ]] && COMMIT_DESPLIEGUE="$(git rev-parse HEAD 2>/dev/null)"; then
    RC_PUBLICADA=0
    bash scripts/imagen_publicada.sh "$COMMIT_DESPLIEGUE" >> "$LOG_FILE" 2>&1 || RC_PUBLICADA=$?
    if [[ "$RC_PUBLICADA" -eq 0 ]]; then
        fijar_env STOCKHOGAR_IMAGE_TAG "$COMMIT_DESPLIEGUE"
        log_success "Imágenes fijadas al commit ${COMMIT_DESPLIEGUE:0:8}"
    else
        fijar_env STOCKHOGAR_IMAGE_TAG ""
        log_info "Imágenes de este commit no confirmadas en GHCR (código $RC_PUBLICADA): se usa :latest"
    fi
else
    # Compilar en local (o --reinstall / --no-build / otra arquitectura): sin pin
    if [[ "$BUILD_MODE" -ne 0 ]]; then fijar_env STOCKHOGAR_IMAGE_TAG ""; fi
fi

# .github/workflows/docker-publish.yml compila armv7l en un runner de GitHub
# (rápido, RAM de sobra) y publica en ghcr.io en cada push a "produccion". Si
# esas imágenes están disponibles, un "pull" es muchísimo más barato para la
# Pi que compilar in-situ (evita el pico de CPU/RAM que colgaba el sistema
# durante "next build"). Si el pull falla (imagen aún no publicada, sin red
# hacia GHCR, etc.) se cae al build local de siempre: no es fatal.
PULLED_INSTEAD_OF_BUILD=0
if [[ "$BUILD_MODE" -eq 0 ]]; then
    log_info "--no-build: se omite también el intento de pull"
elif [[ "$REINSTALL_MODE" -eq 1 ]]; then
    log_info "--reinstall pide reconstruir todo sin caché explícitamente: se omite el pull"
elif [[ "$ARCH" != "armv7l" && "$ARCH" != "armv6l" ]]; then
    # docker-publish.yml solo publica linux/arm/v7, que NO lleva el lector neuronal
    # de tickets (no hay onnxruntime para 32 bits): en x86_64/aarch64 se compila en
    # local para que la imagen lo incluya, aunque el pull funcionaría.
    log_info "Las imágenes precompiladas son de 32 bits (armv7l) y no llevan el lector neuronal de tickets: se compila en local en $ARCH"
else
    log_info "Intentando descargar imágenes precompiladas antes de compilar localmente..."
    if BUILDX_NO_DEFAULT_ATTESTATIONS=1 "${COMPOSE[@]}" pull >> "$LOG_FILE" 2>&1; then
        log_success "Imágenes precompiladas descargadas; se omite el build local"
        BUILD_MODE=0
        PULLED_INSTEAD_OF_BUILD=1
    else
        log_warning "No se pudieron descargar imágenes precompiladas (aún no publicadas o sin red hacia GHCR)."
        log_warning "Se compilará localmente como respaldo."
    fi
fi

step_end

################################################################################
step_start "Construir imágenes"
################################################################################

if [[ "$BUILD_MODE" -eq 0 ]]; then
    [[ "$PULLED_INSTEAD_OF_BUILD" -eq 1 ]] && log_info "Ya se descargaron imágenes precompiladas: se omite la construcción" \
        || log_info "--no-build: se omite la construcción y se reutiliza la imagen actual"
else
    # (La imagen anterior de cada servicio ya se guardó como :rollback en el paso
    # "Guardar las imágenes actuales", antes del pull.)

    # Limpieza automática ANTES de compilar (imágenes huérfanas de builds
    # previos: "docker system prune -f" nunca borra imágenes con tag -incluida
    # ":rollback"- ni volúmenes, así que jamás toca datos de usuario).
    ESPACIO_ANTES_MB="$(df -Pm "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo 0)"
    log_info "Liberando imágenes de Docker sin usar antes de construir..."
    "${DOCKER[@]}" system prune -f >> "$LOG_FILE" 2>&1 || true
    ESPACIO_DESPUES_MB="$(df -Pm "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo 0)"
    log_success "Espacio libre en disco: ${ESPACIO_ANTES_MB}MB -> ${ESPACIO_DESPUES_MB}MB"

    # Pre-descarga con reintentos de las imágenes base: en la Pi la conexión a
    # Docker Hub falla de vez en cuando a mitad de la descarga ("TLS handshake
    # timeout", "context deadline exceeded"). Si eso pasa DENTRO de
    # "compose build" se pierde el build entero (hasta 35 min); aquí solo se
    # pierden unos segundos y `retry` ya reintenta con backoff exponencial.
    for BASE_IMAGE in $(grep -hoE '^FROM [^ ]+' Dockerfile.raspbian Dockerfile.frontend | awk '{print $2}' | sort -u); do
        log_info "Pre-descargando imagen base: $BASE_IMAGE"
        retry "${DOCKER[@]}" pull "$BASE_IMAGE"
    done

    log_info "Construyendo imágenes. En Raspberry Pi el build de Next.js tarda entre 15 y 60 minutos."
    log_info "La salida se muestra en vivo: mientras aparezcan líneas, NO está colgado."

    # Latido cada 2 minutos: `next build` puede pasar 10+ minutos sin imprimir
    # nada y sin esto parece que el proceso se ha quedado muerto. Los traps se
    # limpian dentro del subshell para que no dispare rollback ni el mensaje de
    # interrupción por su cuenta.
    # El `sleep` va en tramos de 5s (no uno de 120s) para que al matar el latido
    # ningún hijo huérfano sobreviva más de 5 segundos.
    ( trap - ERR INT TERM
      while true; do
          for _ in $(seq 1 24); do sleep 5; done
          echo -e "${BLUE}[INFO]${NC} ...sigue construyendo ($(( SECONDS / 60 )) min transcurridos)"
      done ) &
    HEARTBEAT_PID=$!

    # Se construye UN servicio detrás de otro, nunca los dos a la vez: por
    # defecto "compose build" usa buildx bake y compila backend y frontend en
    # paralelo, y en una Raspberry Pi de 4 núcleos / <1GB RAM eso satura la CPU
    # (load average >7) y hace saltar el swap. Bajo esa carga hasta las
    # descargas de Docker Hub fallan por timeout (no es un problema de red:
    # el propio daemon no tiene CPU para atender el handshake TLS a tiempo).
    # Construir en serie deja cada build con la máquina para él solo.
    # --no-cache SIEMPRE (no solo en --reinstall): la caché de capas de Docker
    # (apt-get, pip, npm ci) se purga tras cada build (ver más abajo) para no
    # llenar el disco de la Pi, así que reutilizarla aquí nunca sería posible
    # de todas formas. La velocidad de reinstalar dependencias la da el caché
    # de paquetes de BuildKit (--mount=type=cache en los Dockerfiles), que no
    # se ve afectado por --no-cache ni por la purga posterior.
    BUILD_ARGS=(build --no-cache)

    BUILD_START=$SECONDS
    BUILD_OK=1
    mapfile -t SERVICES < <("${COMPOSE[@]}" config --services 2>/dev/null)
    for SERVICE in "${SERVICES[@]}"; do
        log_info "Construyendo servicio: $SERVICE"
        # BUILDX_NO_DEFAULT_ATTESTATIONS=1: por defecto Buildx genera además
        # un "attestation manifest" de provenance/SBOM por imagen, que exige
        # 2-3 escrituras extra al registro local. Irrelevante para un
        # despliegue de un solo nodo y, en el almacenamiento lento de la Pi,
        # esas escrituras se llevaban entre 15 y 50s extra por imagen (visto
        # en install.log: 12.8s + 14.5s solo en la del frontend).
        # Timeout: 90 minutos por servicio (build típico 15-60 min + margen
        # para I/O lento). Si se agota, mata todo y se hace rollback.
        BUILDX_NO_DEFAULT_ATTESTATIONS=1 \
            timeout 5400 "${COMPOSE[@]}" "${COMPOSE_FLAGS[@]+"${COMPOSE_FLAGS[@]}"}" "${BUILD_ARGS[@]}" "$SERVICE" 2>&1 | tee -a "$LOG_FILE" || { BUILD_OK=0; break; }
    done

    stop_heartbeat

    if [[ "$BUILD_OK" -eq 0 ]]; then
        log_error "El build falló tras $(( (SECONDS - BUILD_START) / 60 )) min. Causas típicas en Raspberry Pi:"
        log_error "  - Memoria insuficiente (OOM) durante 'next build': amplía el swap a 2GB."
        log_error "  - Disco lleno: docker system prune -af"
        log_error "Log completo: $LOG_FILE"
        rollback
        exit 1
    fi
    log_success "Imágenes construidas en $(( (SECONDS - BUILD_START) / 60 )) min"

    # Purga la caché de capas de build (grande, GB) justo después de usarla, ya
    # que con --no-cache arriba nunca se reaprovecha entre ejecuciones. El
    # filtro "type=regular" conserva los cache-mounts de pip/npm declarados con
    # --mount=type=cache en los Dockerfiles (pequeños, MB), que sí siguen
    # acelerando la descarga de dependencias en la próxima actualización.
    log_info "Liberando caché de capas de build (se conserva el caché de paquetes pip/npm)..."
    "${DOCKER[@]}" builder prune -f --filter type=regular >> "$LOG_FILE" 2>&1 || true
fi

step_end

################################################################################
step_start "Iniciar contenedores"
################################################################################

CONTAINERS_TOUCHED=1
log_info "\$ ${COMPOSE[*]} up -d --remove-orphans"
if ! "${COMPOSE[@]}" up -d --remove-orphans 2>&1 | tee -a "$LOG_FILE"; then
    log_error "'compose up' falló. Log completo: $LOG_FILE"
    rollback
    exit 1
fi

step_end

################################################################################
step_start "Verificar que la aplicación responde"
################################################################################

# Esperas ACOTADAS usando el HEALTHCHECK que ya definen los Dockerfiles (que sí
# acepta el 302 de la raíz). Nunca un bucle infinito.
# 90s no bastaba en esta Raspberry Pi: tras un rebuild, la CPU sigue ocupada
# exportando capas de Docker y el backend tarda en dejar de devolver 503,
# provocando rollbacks automáticos sobre una imagen que en realidad estaba
# bien (visto dos veces en producción, se recuperaba solo a los 90-120s).
log_info "Esperando a que el backend esté healthy (máx. 180s)..."
if wait_healthy stockhogar 180; then
    log_success "Backend healthy en el puerto ${STOCKHOGAR_PORT}"
else
    log_error "El backend no llegó a estado healthy. Últimas líneas de log:"
    "${COMPOSE[@]}" logs --tail=40 stockhogar 2>&1 | tee -a "$LOG_FILE" || true
    rollback
    exit 1
fi

# Motores de lectura del escáner de tickets (informativo: no provoca rollback,
# el escáner funciona con cualquiera de los dos). Se comprueba DENTRO del
# contenedor, que es donde corre: un fallo del pip install del lector neuronal
# no rompe el arranque, solo hace que se lea con Tesseract (peor).
OCR_INFO="$(docker exec stockhogar-app python -c "
from stockhogar.integraciones import ocr_rapid
from stockhogar.servicios.ocr.diccionario import obtener
import shutil
print('neuronal' if ocr_rapid.disponible() else 'sin-neuronal', 'tesseract' if shutil.which('tesseract') else 'sin-tesseract', len(obtener().entradas))
" 2>>"$LOG_FILE" || true)"
case "$OCR_INFO" in
    "neuronal tesseract "*) log_success "Escáner de tickets: lector neuronal + Tesseract de respaldo + diccionario (${OCR_INFO##* } artículos)" ;;
    "sin-neuronal tesseract "*)
        if [[ "$ARCH" == armv7l || "$ARCH" == armv6l ]]; then
            log_info "Escáner de tickets: solo Tesseract (esperado en $ARCH)"
        else
            log_warning "El lector neuronal de tickets NO está disponible en el contenedor: se leerá con Tesseract (peor)."
            log_warning "Revisa el build (pip install rapidocr-onnxruntime) en $LOG_FILE y reconstruye con ./install.sh --reinstall"
        fi ;;
    *) log_warning "No se pudo comprobar el escáner de tickets dentro del contenedor (${OCR_INFO:-sin respuesta}). Revisa: docker logs stockhogar-app" ;;
esac

# El frontend tarda más en arrancar y su fallo no justifica un rollback del
# backend: se avisa y se deja al usuario decidir.
log_info "Esperando a que el frontend esté healthy (máx. 120s)..."
if wait_healthy frontend 120; then
    log_success "Frontend healthy en el puerto ${FRONTEND_PORT}"
else
    log_warning "El frontend no responde todavía (estado: $(container_health frontend))."
    log_warning "Puede seguir arrancando. Revisa: ${COMPOSE[*]} logs -f frontend"
fi

step_end

################################################################################
step_start "Configurar auto-actualización"
################################################################################

# El frontend ya trae su propio auto-actualizador (lib/useCacheBuster.ts):
# sondea /api/cache-version cada 15s y recarga solo cuando detecta una versión
# nueva, así que no necesita ningún paso de instalación aparte: viaja dentro
# de la imagen que se acaba de construir.
#
# Lo que sí falta instalar es el cron que dispara ese cambio de versión:
# scripts/auto_update.sh comprueba origin/produccion y hace `install.sh
# --update` cuando hay commits nuevos. Solo tiene sentido en la rama
# "produccion" (que es la que auto_update.sh vigila); en otras ramas se avisa
# y se omite para no dejar un cron que nunca hará nada.
CRON_LINE="*/5 * * * * '$SCRIPT_DIR/scripts/auto_update.sh' >> '$SCRIPT_DIR/logs/auto_update.log' 2>&1"
if [[ -d .git ]] && [[ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" == "produccion" ]]; then
    if check_cmd crontab; then
        if crontab -l 2>/dev/null | grep -qF "scripts/auto_update.sh"; then
            log_info "El cron de auto-actualización ya estaba instalado"
        else
            (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
            log_success "Cron de auto-actualización instalado (cada 5 min, rama produccion)"
        fi
    else
        log_warning "No hay 'crontab' disponible; añade esto manualmente para activar la auto-actualización:"
        log_warning "  $CRON_LINE"
    fi
else
    log_info "Rama actual distinta de 'produccion'; se omite el cron de auto-actualización (actívalo manualmente si lo necesitas)."
fi

# Avisos de caducidad (P-07). scripts/enviar_avisos_caducidad.py se escribió
# para ejecutarse "una vez al día vía cron del sistema" (así lo dice su propio
# docstring), pero ese cron nunca se instaló: activar las notificaciones en
# Ajustes funcionaba y luego no llegaba ningún aviso, porque nadie ejecutaba el
# script. Se lanza dentro del contenedor (container_name fijo en
# docker-compose.yml) porque ahí están las dependencias y la BD montada.
# A diferencia del cron de auto-actualización, este no depende de la rama.
CRON_CADUCIDAD="30 9 * * * docker exec stockhogar-app python scripts/enviar_avisos_caducidad.py >> $SCRIPT_DIR/logs/avisos_caducidad.log 2>&1"
if check_cmd crontab; then
    if crontab -l 2>/dev/null | grep -qF "enviar_avisos_caducidad.py"; then
        log_info "El cron de avisos de caducidad ya estaba instalado"
    else
        (crontab -l 2>/dev/null; echo "$CRON_CADUCIDAD") | crontab -
        log_success "Cron de avisos de caducidad instalado (cada día a las 09:30)"
    fi
else
    log_warning "No hay 'crontab' disponible; añade esto manualmente para que lleguen los avisos de caducidad:"
    log_warning "  $CRON_CADUCIDAD"
fi

# Purga acotada de la caché de build de Docker (scripts/docker_cache_prune.sh):
# sin ella la caché crece durante meses hasta llenar la tarjeta SD. Una vez al
# día de madrugada; nunca toca las imágenes etiquetadas (las ":rollback" incluidas).
CRON_PURGA="15 4 * * * $SCRIPT_DIR/scripts/docker_cache_prune.sh >> $SCRIPT_DIR/logs/docker_cache_prune.log 2>&1"
if check_cmd crontab; then
    if crontab -l 2>/dev/null | grep -qF "docker_cache_prune.sh"; then
        log_info "El cron de purga de la caché de Docker ya estaba instalado"
    else
        (crontab -l 2>/dev/null; echo "$CRON_PURGA") | crontab -
        log_success "Cron de purga de la caché de Docker instalado (cada día a las 04:15)"
    fi
else
    log_warning "No hay 'crontab' disponible; añade esto para que la caché de Docker no llene el disco:"
    log_warning "  $CRON_PURGA"
fi

step_end

################################################################################
step_start "Resumen"
################################################################################

# En la primera instalación el paso de seguridad corrió ANTES de que existieran .env y data/:
# se repite ahora que ya están, con los contenedores arrancados (los ficheros que crean ellos).
if [[ "${DREAME_ENDURECER_SISTEMA:-1}" != "0" ]]; then ajustar_permisos_secretos; fi

IP_ADDRESS="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
IP_ADDRESS="${IP_ADDRESS:-localhost}"
if [[ "$REINSTALL_MODE" -eq 1 ]]; then ACTION="reinstalado desde cero"
elif [[ "$UPDATE_MODE" -eq 1 ]]; then ACTION="actualizado"
else ACTION="instalado"
fi

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  StockHogar ${ACTION} correctamente${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "  ${YELLOW}Frontend (Next.js):${NC}  http://${IP_ADDRESS}:${FRONTEND_PORT}"
echo -e "  ${YELLOW}Backend (Flask API):${NC} http://${IP_ADDRESS}:${STOCKHOGAR_PORT}"
echo ""
echo -e "  ${YELLOW}Comandos útiles:${NC}"
echo -e "    Logs:       ${COMPOSE[*]} logs -f"
echo -e "    Detener:    ${COMPOSE[*]} down"
echo -e "    Reiniciar:  ${COMPOSE[*]} restart"
echo -e "    Actualizar: ./install.sh --update"
echo -e "    Recrear sin rebuild: ./install.sh --no-build"
echo ""
if [[ "${REBOOT_RECOMENDADO:-0}" -eq 1 ]]; then
    echo -e "  ${YELLOW}Reinicia la Raspberry Pi cuando puedas (sudo reboot):${NC} hay ajustes de arranque"
    echo -e "  (memoria de vídeo) que solo surten efecto tras reiniciar."
    echo ""
fi

# Panel de Gestión: proyecto independiente. Si está clonado como carpeta
# hermana, lo instalamos aquí para no obligar a un segundo paso manual.
if PANEL_DIR="$(cd "$SCRIPT_DIR/../StockHogar-Panel" 2>/dev/null && pwd)" && [[ -f "$PANEL_DIR/install.sh" ]]; then
    log_info "Instalando también el Panel de Gestión (StockHogar-Panel)..."
    if (cd "$PANEL_DIR" && bash ./install.sh "$SCRIPT_DIR"); then
        log_success "Panel de Gestión instalado"
    else
        log_warning "El panel no se instaló. Manual: cd \"$PANEL_DIR\" && ./install.sh"
    fi
else
    log_info "StockHogar-Panel no está como carpeta hermana; se omite su instalación."
fi

step_end
log_success "Instalación finalizada. Log completo: $LOG_FILE"
exit 0
