.DEFAULT_GOAL := help

.PHONY: help install setup-env dev runserver check test test-vision test-api shell urls ping compile doctor status clean-cache clean freeze security-check

PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PY := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
MANAGE := $(PY) manage.py
PORT ?= 8000
HOST ?= 127.0.0.1

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
	@printf '  $(GREEN)make install$(RESET)       Create the backend virtual environment and install dependencies\n'
	@printf '  $(GREEN)make dev$(RESET)           Start the Django backend\n'
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
	@printf '  $(CYAN)freeze$(RESET)            Export installed packages\n'
	@printf '  $(CYAN)security-check$(RESET)   Validate installed dependencies\n'
	@printf '  $(CYAN)clean$(RESET)             Remove caches and .venv\n\n'

$(PY):
	@printf '$(MAGENTA)✦ Creating app virtual environment...$(RESET)\n'
	@command -v $(PYTHON) >/dev/null 2>&1 || { printf '$(RED)✘ Python not found: $(PYTHON)$(RESET)\n'; exit 1; }
	$(PYTHON) -m venv $(VENV)
	@$(PIP) install --upgrade pip --disable-pip-version-check >/dev/null
	@printf '$(GREEN)✔ Virtual environment ready.$(RESET)\n'

install: $(PY) setup-env
	@printf '$(MAGENTA)✦ Installing backend dependencies...$(RESET)\n'
	@$(PIP) install -r requirements.txt --disable-pip-version-check
	@printf '$(GREEN)✔ Backend dependencies installed.$(RESET)\n'

setup-env:
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env; printf '$(GREEN)✔ Created .env from .env.example$(RESET)\n'; else printf '$(DIM)· Environment file already configured.$(RESET)\n'; fi

dev: $(PY)
	@printf '\n$(BOLD)$(BLUE)🚀 SHADE-ai Django app$(RESET)  →  http://$(HOST):$(PORT)/api/\n'
	@printf '$(DIM)MongoDB is optional for boot; health reports persistence readiness.$(RESET)\n'
	@printf '$(DIM)Press Ctrl-C to stop the server.$(RESET)\n\n'
	@$(MANAGE) runserver $(HOST):$(PORT)

runserver: dev

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
	@printf '$(CYAN)♥ Pinging SHADE-ai health endpoint...$(RESET)\n'
	@curl --fail --silent --show-error http://$(HOST):$(PORT)/api/health/ | python3 -m json.tool

compile:
	@printf '$(MAGENTA)✦ Compile-checking Python files...$(RESET)\n'
	@$(PYTHON) -m compileall -q .
	@printf '$(GREEN)✔ Python compilation passed.$(RESET)\n'

doctor:
	@printf '\n$(BOLD)$(BLUE)🩺 SHADE-ai backend doctor$(RESET)\n'
	@printf '  Python:  '; command -v $(PYTHON) >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$($(PYTHON) --version 2>&1)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  Venv:    '; test -x $(PY) && printf '$(GREEN)✔ ready$(RESET)\n' || printf '$(YELLOW)○ missing — run make install$(RESET)\n'
	@printf '  Django:  '; test -x $(PY) && $(PY) -c 'import django' 2>/dev/null && printf '$(GREEN)✔ installed$(RESET)\n' || printf '$(YELLOW)○ unavailable$(RESET)\n'
	@printf '  MongoDB: '; lsof -ti:27017 >/dev/null 2>&1 && printf '$(GREEN)✔ detected$(RESET)\n' || printf '$(YELLOW)○ not detected — backend will run in degraded mode$(RESET)\n'

status: doctor

clean-cache:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@rm -rf .pytest_cache .coverage htmlcov
	@printf '$(GREEN)✔ Backend caches removed.$(RESET)\n'

clean: clean-cache
	@rm -rf $(VENV)
	@printf '$(GREEN)✔ Backend virtual environment removed.$(RESET)\n'

freeze: $(PY)
	@$(PIP) freeze > requirements-freeze.txt
	@printf '$(GREEN)✔ Wrote requirements-freeze.txt$(RESET)\n'

security-check: $(PY)
	@$(PIP) check
	@printf '$(GREEN)✔ Python dependency check passed.$(RESET)\n'
