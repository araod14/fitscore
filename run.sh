#!/bin/bash
# FitScore - Script de ejecución
# Uso: ./run.sh [dev|prod|seed|install]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PORT="${PORT:-8000}"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python no encontrado. Instala Python 3.11+"
        exit 1
    fi
    log_info "Usando: $($PYTHON_CMD --version)"
}

# Crear entorno virtual
create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creando entorno virtual..."
        $PYTHON_CMD -m venv $VENV_DIR
    fi
}

# Activar entorno virtual
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        log_error "No se encontró el entorno virtual"
        exit 1
    fi
}

# Instalar dependencias
install_deps() {
    log_info "Instalando dependencias..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    log_info "Dependencias instaladas correctamente"
}

# Ejecutar seed
run_seed() {
    log_info "Creando datos de prueba..."
    python seed.py
}

# Ejecutar en modo desarrollo
run_dev() {
    log_info "Iniciando FitScore en modo DESARROLLO..."
    log_info "URL: http://localhost:$PORT"
    log_info "Docs: http://localhost:$PORT/api/docs"
    echo ""
    uvicorn main:app --reload --host 0.0.0.0 --port $PORT
}

# Ejecutar en modo producción
run_prod() {
    log_info "Iniciando FitScore en modo PRODUCCIÓN..."
    log_info "URL: http://localhost:$PORT"
    echo ""
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
}

# Mostrar ayuda
show_help() {
    echo "FitScore - Sistema de Gestión de Competencias CrossFit"
    echo ""
    echo "Uso: ./run.sh [comando]"
    echo ""
    echo "Comandos:"
    echo "  install    Instalar dependencias"
    echo "  seed       Crear datos de prueba"
    echo "  dev        Ejecutar en modo desarrollo (default)"
    echo "  prod       Ejecutar en modo producción"
    echo "  help       Mostrar esta ayuda"
    echo ""
    echo "Variables de entorno:"
    echo "  PORT       Puerto del servidor (default: 8000)"
    echo ""
    echo "Ejemplos:"
    echo "  ./run.sh              # Ejecutar en desarrollo"
    echo "  ./run.sh install      # Solo instalar dependencias"
    echo "  ./run.sh seed         # Crear datos de prueba"
    echo "  PORT=3000 ./run.sh    # Ejecutar en puerto 3000"
}

# Main
main() {
    check_python
    create_venv
    activate_venv

    case "${1:-dev}" in
        install)
            install_deps
            ;;
        seed)
            install_deps
            run_seed
            ;;
        dev)
            install_deps
            run_dev
            ;;
        prod)
            install_deps
            run_prod
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Comando desconocido: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
