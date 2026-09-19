.DEFAULT_GOAL := help

.PHONY: help install setup-env dev dev-single app ui build check test test-vision test-api compile doctor health clean-cache clean

API_PORT ?= 8000
WEB_PORT ?= 5173

RESET   := \033[0m
BOLD    := \033[1m
DIM     := \033[2m
CYAN    := \033[36m
BLUE    := \033[34m
GREEN   := \033[32m
YELLOW  := \033[33m
RED     := \033[31m
MAGENTA := \033[35m

PROJECT := $(BOLD)$(CYAN)SHADE-ai$(RESET)

help:
	@printf '\n$(CYAN)╭────────────────────────────────────────────────────────────╮$(RESET)\n'
	@printf '$(CYAN)│  ◈  $(PROJECT)  ·  activity intelligence command center      │$(RESET)\n'
	@printf '$(CYAN)╰────────────────────────────────────────────────────────────╯$(RESET)\n'
	@printf '\n$(BOLD)Quick start$(RESET)\n'
	@printf '  $(GREEN)make install$(RESET)       Install backend and web dependencies\n'
	@printf '  $(GREEN)make setup-env$(RESET)     Create the local backend environment file\n'
	@printf '  $(GREEN)make dev$(RESET)           Launch backend and web in Terminal windows\n'
	@printf '\n$(BOLD)Run$(RESET)\n'
	@printf '  $(CYAN)dev-single$(RESET)        Run backend and web from one terminal\n'
	@printf '  $(CYAN)app$(RESET)              Start only the Django backend\n'
	@printf '  $(CYAN)ui$(RESET)               Start only the React UI\n'
	@printf '\n$(BOLD)Quality$(RESET)\n'
	@printf '  $(CYAN)check$(RESET)             Run Django system checks\n'
	@printf '  $(CYAN)test$(RESET)              Run the complete backend suite\n'
	@printf '  $(CYAN)test-vision$(RESET)       Run temporal and pipeline tests\n'
	@printf '  $(CYAN)test-api$(RESET)          Run HTTP contract tests\n'
	@printf '  $(CYAN)build$(RESET)             Build the React application\n'
	@printf '  $(CYAN)ci$(RESET)                Run checks, tests, and the web build\n'
	@printf '\n$(BOLD)Inspect & clean$(RESET)\n'
	@printf '  $(CYAN)doctor$(RESET)            Inspect local tooling and services\n'
	@printf '  $(CYAN)health$(RESET)            Check the running API\n'
	@printf '  $(CYAN)clean-cache$(RESET)      Remove generated caches\n'
	@printf '  $(CYAN)clean$(RESET)             Remove local dependency environments\n\n'

install: setup-env
	@$(MAKE) -C app install
	@$(MAKE) -C web install
	@printf '$(GREEN)✔ SHADE-ai dependencies are ready.$(RESET)\n'

setup-env:
	@$(MAKE) -C app setup-env

# On macOS, opening separate Terminal windows keeps the API and UI logs readable.
# Other systems use the portable one-terminal runner.
dev:
	@if [ "$$(uname)" = "Darwin" ]; then \
		printf '$(CYAN)✦ Opening API and UI in separate Terminal windows...$(RESET)\n'; \
		osascript -e 'tell application "Terminal" to do script "cd \"$(CURDIR)/app\" && make dev"' >/dev/null; \
		osascript -e 'tell application "Terminal" to do script "cd \"$(CURDIR)/web\" && make dev"' >/dev/null; \
		printf '$(GREEN)✔ Development cockpit launched.$(RESET)\n'; \
	else \
		$(MAKE) dev-single; \
	fi

dev-single:
	@printf '$(MAGENTA)✦ Starting API + UI — press Ctrl-C to stop$(RESET)\n'
	@trap 'kill 0' INT TERM; (cd app && $(MAKE) dev PORT=$(API_PORT)) & (cd web && $(MAKE) dev PORT=$(WEB_PORT)) & wait

app:
	@$(MAKE) -C app dev PORT=$(API_PORT)

ui:
	@$(MAKE) -C web dev PORT=$(WEB_PORT)

build:
	@$(MAKE) -C web build

check:
	@$(MAKE) -C app check

test:
	@$(MAKE) -C app test

test-vision:
	@$(MAKE) -C app test-vision

test-api:
	@$(MAKE) -C app test-api

compile:
	@$(MAKE) -C app compile

ci:
	@$(MAKE) check
	@$(MAKE) test
	@$(MAKE) build
	@printf '$(GREEN)✔ CI checks completed.$(RESET)\n'

doctor:
	@printf '\n$(BOLD)$(CYAN)🩺 SHADE-ai environment doctor$(RESET)\n'
	@printf '  Python:  '; command -v python3 >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$(python3 --version)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  Node:    '; command -v node >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$(node --version)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  npm:     '; command -v npm >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$(npm --version)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  MongoDB: '; lsof -ti:27017 >/dev/null 2>&1 && printf '$(GREEN)✔ detected$(RESET)\n' || printf '$(YELLOW)○ not detected — API health will be degraded$(RESET)\n'
	@printf '  API env: '; test -f app/.env && printf '$(GREEN)✔ present$(RESET)\n' || printf '$(YELLOW)○ missing — run make setup-env$(RESET)\n'
	@printf '  Web deps:'; test -d web/node_modules && printf ' $(GREEN)✔ ready$(RESET)\n' || printf ' $(YELLOW)○ missing — run make install$(RESET)\n'

health:
	@$(MAKE) -C app ping

clean-cache:
	@$(MAKE) -C app clean-cache
	@$(MAKE) -C web clean-cache

clean:
	@printf '$(YELLOW)⚠ Removing app/.venv, web/node_modules, and generated web output.$(RESET)\n'
	@$(MAKE) -C app clean
	@$(MAKE) -C web clean
