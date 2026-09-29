.DEFAULT_GOAL := help

SHELL := /bin/sh

.PHONY: help install setup-env dev runserver check-mongodb check test test-vision test-api shell urls ping compile doctor status logs stop clean-cache clean freeze security-check --force

PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PY := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
MANAGE := $(PY) manage.py
PORT ?= 8000
HOST ?= 127.0.0.1

# BSD Make treats `--force` as an option unless it follows the `--` separator.
# This keeps the user-facing bypass flag explicit without using FORCE=1.
SHADE_FORCE_FLAG ?= $(if $(filter --force,$(MAKECMDGOALS)),--force,)
RUNSERVER_FORCE := $(if $(filter --force,$(SHADE_FORCE_FLAG)),--force,)

RESET   := \033[0m
BOLD    := \033[1m
DIM     := \033[2m
CYAN    := \033[36m
BLUE    := \033[34m
GREEN   := \033[32m
YELLOW  := \033[33m
RED     := \033[31m
MAGENTA := \033[35m
TITLE   := $(BOLD)$(BLUE)APP$(RESET)

help:
	@printf '\n$(BLUE)╭────────────────────────────────────────────────────────────╮$(RESET)\n'
	@printf '$(BLUE)│  🐍  $(TITLE)  ·  Django + MongoEngine control room             │$(RESET)\n'
	@printf '$(BLUE)╰────────────────────────────────────────────────────────────╯$(RESET)\n'
	@printf '\n$(BOLD)Quick start$(RESET)\n'
	@printf '  $(GREEN)make install$(RESET)       Create the app virtual environment and install dependencies\n'
	@printf '  $(GREEN)make dev$(RESET)           Start the Django app on port $(PORT) (MongoDB required)\n'
	@printf '  $(GREEN)make dev -- --force$(RESET) Start diagnostic mode without the MongoDB startup check\n'
	@printf '  $(GREEN)make doctor$(RESET)        Inspect backend readiness\n'
	@printf '\n$(BOLD)Quality$(RESET)\n'
	@printf '  $(CYAN)check$(RESET)             Run Django system checks\n'
	@printf '  $(CYAN)test$(RESET)              Run the complete pytest suite\n'
	@printf '  $(CYAN)test-vision$(RESET)       Test temporal verification and pipeline behavior\n'
	@printf '  $(CYAN)test-api$(RESET)          Test HTTP endpoint contracts\n'
	@printf '  $(CYAN)compile$(RESET)           Compile-check Python files\n'
	@printf '\n$(BOLD)Develop & maintain$(RESET)\n'
	@printf '  $(CYAN)shell$(RESET)             Open a Django shell\n'
	@printf '  $(CYAN)urls$(RESET)              Validate registered URLs\n'
	@printf '  $(CYAN)ping$(RESET)              Call the API health endpoint\n'
	@printf '  $(CYAN)status$(RESET)            Show app environment status\n'
	@printf '  $(CYAN)logs$(RESET)              Tail recent backend logs\n'
	@printf '  $(CYAN)stop$(RESET)              Stop the app process on port $(PORT)\n'
	@printf '  $(CYAN)freeze$(RESET)            Export installed packages\n'
	@printf '  $(CYAN)security-check$(RESET)   Validate installed dependencies\n'
	@printf '  $(CYAN)clean$(RESET)             Remove caches and .venv\n\n'

$(PY):
	@printf '$(MAGENTA)✦ Creating app virtual environment...$(RESET)\n'
	@command -v $(PYTHON) >/dev/null 2>&1 || { printf '$(RED)✘ Python not found: $(PYTHON)$(RESET)\n'; exit 1; }
	$(PYTHON) -m venv $(VENV)
	@$(PY) -m pip install --upgrade pip --disable-pip-version-check >/dev/null
	@printf '$(GREEN)✔ Virtual environment ready.$(RESET)\n'

install: setup-env
	@printf '$(MAGENTA)✦ Checking app virtual environment...$(RESET)\n'
	@venv_path=$$(cd "$(VENV)" 2>/dev/null && pwd -P); \
	recreate=0; \
	if [ ! -x "$(PY)" ] || [ ! -f "$(VENV)/pyvenv.cfg" ] || [ -z "$$venv_path" ] || \
		! "$(PY)" -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)' >/dev/null 2>&1 || \
		! grep -Fq "$$venv_path" "$(VENV)/pyvenv.cfg"; then recreate=1; fi; \
	if [ $$recreate -eq 0 ] && ! "$(PIP)" --version >/dev/null 2>&1; then recreate=1; fi; \
	if [ $$recreate -eq 1 ]; then \
		printf '$(YELLOW)⚠ App virtual environment is missing, moved, or unusable; recreating it.$(RESET)\n'; \
		command -v $(PYTHON) >/dev/null 2>&1 || { printf '$(RED)✘ Python not found: $(PYTHON)$(RESET)\n'; exit 1; }; \
		$(PYTHON) -m venv --clear "$(VENV)" || exit $$?; \
	fi
	@printf '$(MAGENTA)✦ Installing app dependencies...$(RESET)\n'
	@$(PY) -m pip install --upgrade pip --disable-pip-version-check >/dev/null
	@$(PY) -m pip install -r requirements.txt --disable-pip-version-check
	@printf '$(GREEN)✔ App dependencies installed.$(RESET)\n'

setup-env:
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env; printf '$(GREEN)✔ Created .env from .env.example$(RESET)\n'; else printf '$(DIM)· Environment file already configured.$(RESET)\n'; fi

dev: $(PY) check-mongodb
	@$(PY) -c 'import django' >/dev/null 2>&1 || { printf '$(RED)✘ Django is not installed; run `make install` inside app/.$(RESET)\n'; exit 1; }
	@printf '\n$(BOLD)$(BLUE)╔══════════════════════════════════════════╗$(RESET)\n'
	@printf '$(BOLD)$(BLUE)║       🐍 SHADE-ai Django app             ║$(RESET)\n'
	@printf '$(BOLD)$(BLUE)╚══════════════════════════════════════════╝$(RESET)\n'
	@printf '$(CYAN)Backend:  http://localhost:$(PORT)$(RESET)\n'
	@printf '$(CYAN)API:      http://localhost:$(PORT)/api/$(RESET)\n'
	@printf '$(CYAN)Health:   http://localhost:$(PORT)/api/health/$(RESET)\n'
	@printf '$(DIM)Normal startup requires MongoDB; use `make dev -- --force` only for diagnostics.$(RESET)\n'
	@printf '$(DIM)Browser opening is intentionally owned by web/Makefile.$(RESET)\n\n'
	@$(MANAGE) runserver $(HOST):$(PORT) $(RUNSERVER_FORCE)

runserver: dev

check-mongodb: $(PY)
	@if [ "$(SHADE_FORCE_FLAG)" = "--force" ]; then \
		printf '$(YELLOW)⚠ MongoDB startup check bypassed via --force.$(RESET)\n'; \
	elif $(PY) -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development"); from config.database import database_available; raise SystemExit(0 if database_available() else 1)' >/dev/null 2>&1; then \
		printf '$(GREEN)✓ MongoDB running and reachable.$(RESET)\n'; \
	else \
		printf '$(RED)✘ MongoDB is required for normal SHADE-ai backend startup.$(RESET)\n'; \
		printf '$(YELLOW)  Start MongoDB, or use `make dev -- --force` for diagnostic mode.$(RESET)\n'; \
		exit 1; \
	fi

check: $(PY)
	@printf '$(MAGENTA)✦ Running Django checks...$(RESET)\n'
	@$(MANAGE) check
	@printf '$(GREEN)✔ Django checks passed.$(RESET)\n'

test: $(PY)
	@printf '$(MAGENTA)✦ Running backend tests...$(RESET)\n'
	@$(PY) -m pytest -q
	@printf '$(GREEN)✔ Backend tests passed.$(RESET)\n'

test-vision: $(PY)
	@$(PY) -m pytest -q tests/test_temporal_engine.py tests/test_pipeline.py

test-api: $(PY)
	@$(PY) -m pytest -q tests/test_api_contracts.py

shell: $(PY)
	@$(MANAGE) shell

urls: $(PY)
	@$(MANAGE) check
	@printf '$(CYAN)Registered URL configuration validated by Django.$(RESET)\n'

ping:
	@command -v curl >/dev/null 2>&1 || { printf '$(RED)✘ curl is required.$(RESET)\n'; exit 1; }
	@printf '$(CYAN)♥ Pinging SHADE-ai health endpoint...$(RESET)\n'
	@curl --fail --silent --show-error http://$(HOST):$(PORT)/api/health/ | $(PYTHON) -m json.tool

compile:
	@printf '$(MAGENTA)✦ Compile-checking Python files...$(RESET)\n'
	@$(PYTHON) -m compileall -q .
	@printf '$(GREEN)✔ Python compilation passed.$(RESET)\n'

doctor:
	@printf '\n$(BOLD)$(BLUE)🩺 SHADE-ai backend doctor$(RESET)\n'
	@printf '  Python:  '; command -v $(PYTHON) >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$($(PYTHON) --version 2>&1)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  Venv:    '; test -x $(PY) && printf '$(GREEN)✔ ready$(RESET)\n' || printf '$(YELLOW)○ missing — run make install$(RESET)\n'
	@printf '  Django:  '; test -x $(PY) && $(PY) -c 'import django' 2>/dev/null && printf '$(GREEN)✔ installed$(RESET)\n' || printf '$(YELLOW)○ unavailable$(RESET)\n'
	@printf '  MongoDB: '; if $(PY) -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development"); from config.database import database_available; raise SystemExit(0 if database_available() else 1)' >/dev/null 2>&1; then printf '$(GREEN)✔ reachable$(RESET)\n'; else printf '$(RED)✘ required / not reachable$(RESET)\n'; fi
	@printf '  .env:    '; test -f .env && printf '$(GREEN)✔ present$(RESET)\n' || printf '$(YELLOW)○ missing — run make setup-env$(RESET)\n'

status: doctor

logs:
	@if [ -f logs/shade-ai.log ]; then tail -n 80 logs/shade-ai.log; else printf '$(YELLOW)No backend log file exists yet.$(RESET)\n'; fi

stop:
	@printf '$(RED)🛑 Stopping the app process on port $(PORT)...$(RESET)\n'
	@if command -v lsof >/dev/null 2>&1; then \
		for pid in $$(lsof -ti:$(PORT) 2>/dev/null); do kill $$pid 2>/dev/null || true; done; \
		sleep 1; \
		for pid in $$(lsof -ti:$(PORT) 2>/dev/null); do kill -9 $$pid 2>/dev/null || true; done; \
	fi
	@printf '$(GREEN)✔ App process stopped.$(RESET)\n'

clean-cache:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@rm -rf .pytest_cache .coverage htmlcov
	@printf '$(GREEN)✔ App caches removed.$(RESET)\n'

clean: clean-cache
	@rm -rf $(VENV)
	@printf '$(GREEN)✔ App virtual environment removed.$(RESET)\n'

freeze: $(PY)
	@$(PIP) freeze > requirements-freeze.txt
	@printf '$(GREEN)✔ Wrote requirements-freeze.txt$(RESET)\n'

security-check: $(PY)
	@$(PIP) check
	@printf '$(GREEN)✔ Python dependency check passed.$(RESET)\n'

# `make dev -- --force` passes `--force` after BSD Make's option separator.
--force:
	@:
