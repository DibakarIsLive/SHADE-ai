.DEFAULT_GOAL := help

SHELL := /bin/sh

.PHONY: help check-system install setup-env dev dev-tabs dev-single app api-only api ui web-only build check test test-vision test-api compile ci doctor check-health wait-for-api health status show-urls logs open stop restart clean-cache clean --force

API_PORT ?= 8000
WEB_PORT ?= 5173
MONGO_PORT ?= 27017
HOST ?= 127.0.0.1

# `make dev -- --force` is the explicit diagnostic bypass for MongoDB startup.
SHADE_FORCE_FLAG ?= $(if $(filter --force,$(MAKECMDGOALS)),--force,)

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
	@printf '  $(GREEN)make install$(RESET)       Prepare the app and web dependencies\n'
	@printf '  $(GREEN)make setup-env$(RESET)     Create app/.env from app/.env.example\n'
	@printf '  $(GREEN)make dev$(RESET)           Launch MongoDB → backend → frontend in separate Terminal windows\n'
	@printf '  $(GREEN)make dev -- --force$(RESET) Launch diagnostic mode without MongoDB/backend readiness gates\n'
	@printf '  $(GREEN)make stop$(RESET)          Stop both development servers\n'
	@printf '\n$(BOLD)Run$(RESET)\n'
	@printf '  $(CYAN)dev$(RESET)               Start the full development cockpit\n'
	@printf '  $(CYAN)dev-single$(RESET)        Run app and web in one terminal\n'
	@printf '  $(CYAN)app$(RESET)              Start only the Django app (MongoDB required)\n'
	@printf '  $(CYAN)ui$(RESET)               Start only the React web UI (backend required)\n'
	@printf '  $(CYAN)ui -- --force$(RESET)    Start the web UI without the backend gate\n'
	@printf '\n$(BOLD)Quality$(RESET)\n'
	@printf '  $(CYAN)check$(RESET)             Run Django system checks\n'
	@printf '  $(CYAN)test$(RESET)              Run the complete backend suite\n'
	@printf '  $(CYAN)test-vision$(RESET)       Run temporal and pipeline tests\n'
	@printf '  $(CYAN)test-api$(RESET)          Run HTTP contract tests\n'
	@printf '  $(CYAN)build$(RESET)             Build the React application\n'
	@printf '  $(CYAN)ci$(RESET)                Run checks, tests, and the web build\n'
	@printf '\n$(BOLD)Inspect & maintain$(RESET)\n'
	@printf '  $(CYAN)check-health$(RESET)      Verify MongoDB readiness without starting services\n'
	@printf '  $(CYAN)health$(RESET)            Query the running API health endpoint\n'
	@printf '  $(CYAN)status$(RESET)            Show app, web, and MongoDB status\n'
	@printf '  $(CYAN)open$(RESET)              Open the frontend manually\n'
	@printf '  $(CYAN)logs$(RESET)              Tail backend logs\n'
	@printf '  $(CYAN)clean-cache$(RESET)      Remove generated caches\n'
	@printf '  $(CYAN)clean$(RESET)             Remove local dependency environments\n\n'

check-system:
	@printf '\n$(BOLD)$(CYAN)🩺 Checking local tooling$(RESET)\n'
	@command -v python3 >/dev/null 2>&1 || { printf '$(RED)✘ Python 3 is required.$(RESET)\n'; exit 1; }
	@command -v node >/dev/null 2>&1 || { printf '$(RED)✘ Node.js is required.$(RESET)\n'; exit 1; }
	@command -v npm >/dev/null 2>&1 || { printf '$(RED)✘ npm is required.$(RESET)\n'; exit 1; }
	@printf '  Python:  $(GREEN)✔ %s$(RESET)\n' "$$(python3 --version 2>&1)"
	@printf '  Node:    $(GREEN)✔ %s$(RESET)\n' "$$(node --version 2>&1)"
	@printf '  npm:     $(GREEN)✔ %s$(RESET)\n' "$$(npm --version 2>&1)"

install: check-system setup-env
	@printf '\n$(MAGENTA)✦ Installing app dependencies...$(RESET)\n'
	@$(MAKE) -C app install
	@printf '\n$(MAGENTA)✦ Installing web dependencies...$(RESET)\n'
	@$(MAKE) -C web install
	@printf '$(GREEN)✔ SHADE-ai dependencies are ready.$(RESET)\n'

setup-env:
	@$(MAKE) -C app setup-env

# macOS launches the app and web processes in separate Terminal windows.
# The web child owns browser opening; the app child never opens a browser.
# Normal startup follows MongoDB -> backend -> frontend. `--force` keeps both
# service-level dependency gates explicit while allowing diagnostic startup.
dev: check-health
	@printf '\n$(BOLD)$(MAGENTA)╔══════════════════════════════════════════╗$(RESET)\n'
	@printf '$(BOLD)$(MAGENTA)║    🚀 STARTING SHADE-ai                  ║$(RESET)\n'
	@printf '$(BOLD)$(MAGENTA)╚══════════════════════════════════════════╝$(RESET)\n\n'
	@if [ "$$(uname)" = "Darwin" ]; then \
		$(MAKE) dev-tabs SHADE_FORCE_FLAG=$(SHADE_FORCE_FLAG); \
	else \
		$(MAKE) dev-single SHADE_FORCE_FLAG=$(SHADE_FORCE_FLAG); \
	fi

dev-tabs:
	@if [ "$$(uname)" != "Darwin" ]; then \
		printf '$(YELLOW)⚠ Separate Terminal windows are macOS-specific; using one-terminal mode.$(RESET)\n'; \
		$(MAKE) dev-single; \
		exit 0; \
	fi
	@printf '$(CYAN)🖥️  Opening Backend in new Terminal window...$(RESET)\n'
	@osascript -e 'tell application "Terminal" to do script "cd \"$(CURDIR)/app\" && make dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) HOST=$(HOST) PORT=$(API_PORT)"' >/dev/null
	@printf '$(CYAN)⏳ Waiting for the backend health endpoint...$(RESET)\n'
	@$(MAKE) wait-for-api SHADE_FORCE_FLAG=$(SHADE_FORCE_FLAG)
	@printf '$(CYAN)🎨 Opening Frontend in new Terminal window...$(RESET)\n'
	@osascript -e 'tell application "Terminal" to do script "cd \"$(CURDIR)/web\" && make dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) PORT=$(WEB_PORT) API_URL=http://$(HOST):$(API_PORT)"' >/dev/null
	@sleep 2
	@printf '\n$(GREEN)✅ Development cockpit launched.$(RESET)\n\n'
	@$(MAKE) show-urls
	@printf '\n$(DIM)The frontend terminal opens the browser automatically; the backend terminal stays browser-free.$(RESET)\n'
	@printf '$(YELLOW)💡 Use `make stop` to stop both servers.$(RESET)\n\n'

dev-single: check-health
	@printf '$(MAGENTA)✦ Starting app + web in one terminal — press Ctrl-C to stop$(RESET)\n'
	@$(MAKE) show-urls
	@trap 'kill $$APP_PID $$WEB_PID 2>/dev/null || true' INT TERM; \
		(cd app && $(MAKE) dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) HOST=$(HOST) PORT=$(API_PORT)) & APP_PID=$$!; \
		printf '$(CYAN)⏳ Waiting for the backend health endpoint...$(RESET)\n'; \
		$(MAKE) wait-for-api SHADE_FORCE_FLAG=$(SHADE_FORCE_FLAG); \
		(cd web && $(MAKE) dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) PORT=$(WEB_PORT) API_URL=http://$(HOST):$(API_PORT)) & WEB_PID=$$!; \
		wait $$APP_PID $$WEB_PID

app api-only api:
	@$(MAKE) -C app dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) HOST=$(HOST) PORT=$(API_PORT)

ui web-only:
	@$(MAKE) -C web dev$(if $(SHADE_FORCE_FLAG), -- $(SHADE_FORCE_FLAG),) PORT=$(WEB_PORT) API_URL=http://$(HOST):$(API_PORT)

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
	@printf '\n$(MAGENTA)╭─ CI runway ────────────────────────────────────────────────╮$(RESET)\n'
	@$(MAKE) check
	@$(MAKE) test
	@$(MAKE) compile
	@$(MAKE) build
	@printf '$(GREEN)╰─ ✔ CI runway clear ────────────────────────────────────────╯$(RESET)\n\n'

wait-for-api:
	@if [ "$(SHADE_FORCE_FLAG)" = "--force" ]; then \
		printf '$(YELLOW)⚠ Backend readiness wait bypassed via --force$(RESET)\n'; \
	else \
		attempt=0; \
		until curl --fail --silent --show-error --connect-timeout 1 --max-time 3 "http://$(HOST):$(API_PORT)/api/health/" >/dev/null 2>&1; do \
			attempt=$$((attempt + 1)); \
			if [ $$attempt -ge 30 ]; then \
				printf '$(RED)✘ Backend did not become ready within 30 seconds.$(RESET)\n'; \
				exit 1; \
			fi; \
			sleep 1; \
		done; \
		printf '$(GREEN)✓ Backend health endpoint is ready$(RESET)\n'; \
	fi

check-health:
	@printf '\n$(BOLD)$(MAGENTA)✦ Quick health check...$(RESET)\n'
	@if [ "$(SHADE_FORCE_FLAG)" = "--force" ]; then \
		printf '$(YELLOW)⚠ MongoDB startup check bypassed via --force$(RESET)\n'; \
	elif $(MAKE) -C app check-mongodb >/dev/null; then \
		printf '$(GREEN)✓ MongoDB running and reachable$(RESET)\n'; \
	else \
		printf '$(RED)✘ MongoDB is required before starting SHADE-ai$(RESET)\n'; \
		printf '$(YELLOW)  Start MongoDB, or use `make dev -- --force` for diagnostic mode.$(RESET)\n'; \
		exit 1; \
	fi

health:
	@$(MAKE) -C app ping HOST=$(HOST) PORT=$(API_PORT)

show-urls:
	@printf '$(CYAN)╔════════════════════════════════════════════╗$(RESET)\n'
	@printf '$(CYAN)║              🌐 SHADE-ai URLS              ║$(RESET)\n'
	@printf '$(CYAN)╠════════════════════════════════════════════╣$(RESET)\n'
	@printf '$(CYAN)║  Frontend:  http://localhost:$(WEB_PORT)           ║$(RESET)\n'
	@printf '$(CYAN)║  Backend:   http://localhost:$(API_PORT)           ║$(RESET)\n'
	@printf '$(CYAN)║  API:       http://localhost:$(API_PORT)/api/      ║$(RESET)\n'
	@printf '$(CYAN)║  Health:    http://localhost:$(API_PORT)/api/health/ ║$(RESET)\n'
	@printf '$(CYAN)║  WebSocket: ws://localhost:$(API_PORT)/ws/monitoring/ ║$(RESET)\n'
	@printf '$(CYAN)╚════════════════════════════════════════════╝$(RESET)\n'

status:
	@printf '\n$(BOLD)$(CYAN)📡 SHADE-ai service status$(RESET)\n'
	@if command -v lsof >/dev/null 2>&1 && lsof -ti:$(MONGO_PORT) >/dev/null 2>&1; then printf '  MongoDB:  $(GREEN)✔ running on :$(MONGO_PORT)$(RESET)\n'; else printf '  MongoDB:  $(YELLOW)○ not detected$(RESET)\n'; fi
	@if command -v lsof >/dev/null 2>&1 && lsof -ti:$(API_PORT) >/dev/null 2>&1; then printf '  Backend:   $(GREEN)✔ running on :$(API_PORT)$(RESET)\n'; else printf '  Backend:   $(YELLOW)○ stopped$(RESET)\n'; fi
	@if command -v lsof >/dev/null 2>&1 && lsof -ti:$(WEB_PORT) >/dev/null 2>&1; then printf '  Frontend:  $(GREEN)✔ running on :$(WEB_PORT)$(RESET)\n'; else printf '  Frontend:  $(YELLOW)○ stopped$(RESET)\n'; fi
	@printf '\n$(BOLD)Backend environment$(RESET)\n'
	@$(MAKE) -C app doctor
	@printf '\n$(BOLD)Frontend environment$(RESET)\n'
	@$(MAKE) -C web doctor

logs:
	@if [ -f app/logs/shade-ai.log ]; then tail -n 80 app/logs/shade-ai.log; else printf '$(YELLOW)No backend log file exists yet. Start the app first.$(RESET)\n'; fi

open:
	@if [ "$$(uname)" = "Darwin" ]; then open "http://localhost:$(WEB_PORT)"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$(WEB_PORT)"; else printf 'Frontend: http://localhost:$(WEB_PORT)\n'; fi

# Stop only the configured SHADE-ai ports; do not kill unrelated project processes.
stop:
	@printf '$(RED)🛑 Stopping SHADE-ai development servers...$(RESET)\n'
	@if command -v lsof >/dev/null 2>&1; then \
		for port in $(API_PORT) $(WEB_PORT); do \
			for pid in $$(lsof -ti:$$port 2>/dev/null); do kill $$pid 2>/dev/null || true; done; \
		done; \
		sleep 1; \
		for port in $(API_PORT) $(WEB_PORT); do \
			for pid in $$(lsof -ti:$$port 2>/dev/null); do kill -9 $$pid 2>/dev/null || true; done; \
		done; \
	fi
	@printf '$(GREEN)✔ Development servers stopped. Terminal windows remain available.$(RESET)\n'

restart: stop install
	@$(MAKE) dev

clean-cache:
	@$(MAKE) -C app clean-cache
	@$(MAKE) -C web clean-cache

clean:
	@printf '$(YELLOW)⚠ Removing app/.venv, web/node_modules, and generated build output.$(RESET)\n'
	@$(MAKE) -C app clean
	@$(MAKE) -C web clean

# `make dev -- --force` passes the explicit diagnostic flag to the app child.
--force:
	@:
