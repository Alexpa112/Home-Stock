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
    armv7l|armv6l)  log_success "Arquitectura: $ARCH (soportada, build lento)" ;;
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
    retry curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    run $SUDO sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
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
        log_success ".env creado a partir de .env.example"
    else
        : > ".env"
        log_success ".env creado vacío"
    fi
else
    # El respaldo del .env NO puede vivir en data/backups/: ese directorio lo
    # sirve por HTTP el Panel de Gestion para descargar copias de seguridad, y
    # el .env lleva en claro las credenciales OAuth de Google/Apple, la
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

if ! "${COMPOSE[@]}" config -q 2>>"$LOG_FILE"; then
    log_error "docker-compose.yml (o el .env) no es válido:"
    tail -n 20 "$LOG_FILE"
    exit 1
fi
log_success "docker-compose.yml válido"

step_end

################################################################################
step_start "Descargar imágenes precompiladas (GHCR)"
################################################################################

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
    # Guardamos la imagen anterior de CADA servicio (backend y frontend) como
    # :rollback para poder volver atrás si el arranque falla. Antes solo se
    # respaldaba la primera imagen de la lista ("head -1"): si luego fallaba
    # el build de la otra, esa quedaba sin respaldo y el rollback la dejaba
    # con la versión nueva (rota) en vez de revertirla también.
    mapfile -t IMAGE_NAMES < <("${COMPOSE[@]}" config --images 2>/dev/null)
    IMAGE_NAMES_BACKED_UP=()
    if [[ "${#IMAGE_NAMES[@]}" -eq 0 ]]; then
        log_info "No hay imagen anterior que respaldar (primera instalación)"
    else
        for IMAGE_NAME in "${IMAGE_NAMES[@]}"; do
            if "${DOCKER[@]}" image inspect "$IMAGE_NAME" &> /dev/null; then
                CONTAINERS_TOUCHED=1
                IMAGE_BASE="${IMAGE_NAME%:*}"
                run "${DOCKER[@]}" tag "$IMAGE_NAME" "${IMAGE_BASE}:rollback"
                IMAGE_NAMES_BACKED_UP+=("$IMAGE_NAME")
                log_info "Imagen anterior guardada como ${IMAGE_BASE}:rollback"
            fi
        done
        [[ "${#IMAGE_NAMES_BACKED_UP[@]}" -eq 0 ]] && log_info "No hay imagen anterior que respaldar (primera instalación)"
    fi

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
CRON_LINE="*/5 * * * * $SCRIPT_DIR/scripts/auto_update.sh >> $SCRIPT_DIR/logs/auto_update.log 2>&1"
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

step_end

################################################################################
step_start "Resumen"
################################################################################

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
