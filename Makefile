# FitScore - Makefile
# Uso: make [comando]

.PHONY: help install seed dev prod clean test migrate deploy setup-vps

PYTHON := python3
VENV := venv
PORT := 8000

# Detectar sistema operativo
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
	PYTHON_VENV := $(VENV_BIN)/python
else
	VENV_BIN := $(VENV)/bin
	PYTHON_VENV := $(VENV_BIN)/python
endif

help: ## Mostrar ayuda
	@echo "FitScore - Comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

$(VENV): ## Crear entorno virtual
	$(PYTHON) -m venv $(VENV)

install: $(VENV) ## Instalar dependencias
	$(PYTHON_VENV) -m pip install --upgrade pip
	$(PYTHON_VENV) -m pip install -r requirements.txt
	@echo "✓ Dependencias instaladas"

seed: install ## Crear datos de prueba
	$(PYTHON_VENV) seed.py

dev: install ## Ejecutar en modo desarrollo
	@echo "Iniciando FitScore en http://localhost:$(PORT)"
	@echo "API Docs en http://localhost:$(PORT)/api/docs"
	$(VENV_BIN)/uvicorn main:app --reload --host 0.0.0.0 --port $(PORT)

prod: install ## Ejecutar en modo producción
	@echo "Iniciando FitScore en modo producción..."
	$(VENV_BIN)/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$(PORT)

run: dev ## Alias para dev

migrate: install ## Ejecutar migraciones
	$(VENV_BIN)/alembic upgrade head

test: install ## Ejecutar tests
	$(VENV_BIN)/pytest tests/ -v

clean: ## Limpiar archivos generados
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -f *.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Limpieza completada"

reset: clean install seed ## Reiniciar todo (limpiar + instalar + seed)
	@echo "✓ Proyecto reiniciado"

deploy: ## Desplegar en VPS (git pull + instalar deps + migraciones + reiniciar servicio)
	@echo "🚀 Desplegando FitScore en VPS..."
	git pull origin main
	$(PYTHON_VENV) -m pip install --upgrade -r requirements.txt
	$(VENV_BIN)/alembic upgrade head
	@echo "✓ Dependencias actualizadas y migraciones ejecutadas"
	@echo "🔄 Para reiniciar el servicio systemd:"
	@echo "   sudo systemctl restart fitscore"

setup-vps: ## Setup inicial para VPS (ejecutar una sola vez)
	@echo "📦 Setup inicial del VPS..."
	$(PYTHON) -m venv $(VENV)
	$(PYTHON_VENV) -m pip install --upgrade pip
	$(PYTHON_VENV) -m pip install -r requirements.txt
	$(VENV_BIN)/alembic upgrade head
	@echo ""
	@echo "✓ Setup completado. Próximos pasos:"
	@echo ""
	@echo "1. Configurar variables de entorno en .env:"
	@echo "   SECRET_KEY=<clave-segura>"
	@echo "   DEBUG=False"
	@echo ""
	@echo "2. Crear archivo systemd en /etc/systemd/system/fitscore.service"
	@echo "   (Ver plantilla en documentación)"
	@echo ""
	@echo "3. Iniciar servicio:"
	@echo "   sudo systemctl start fitscore"
	@echo "   sudo systemctl enable fitscore"
