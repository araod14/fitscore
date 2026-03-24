# FitScore - Makefile
# Uso: make [comando]

.PHONY: help install seed dev prod clean

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

clean: ## Limpiar archivos generados
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -f *.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Limpieza completada"

reset: clean install seed ## Reiniciar todo (limpiar + instalar + seed)
	@echo "✓ Proyecto reiniciado"
