.DEFAULT_GOAL := help

.PHONY: help install dev build preview test-api health status doctor clean-build clean-cache clean deps-check audit

NPM ?= npm
PORT ?= 5173
API_URL ?= http://127.0.0.1:8000

RESET   := \033[0m
BOLD    := \033[1m
DIM     := \033[2m
CYAN    := \033[36m
BLUE    := \033[34m
GREEN   := \033[32m
YELLOW  := \033[33m
RED     := \033[31m
MAGENTA := \033[35m
TITLE   := $(BOLD)$(MAGENTA)WEB$(RESET)

help:
	@printf '\n$(MAGENTA)╭────────────────────────────────────────────────────────────╮$(RESET)\n'
	@printf '$(MAGENTA)│  ⚛  $(TITLE)  ·  React + Vite operations deck                   │$(RESET)\n'
	@printf '$(MAGENTA)╰────────────────────────────────────────────────────────────╯$(RESET)\n'
	@printf '\n$(BOLD)Quick start$(RESET)\n'
	@printf '  $(GREEN)make install$(RESET)       Install npm dependencies\n'
	@printf '  $(GREEN)make dev$(RESET)           Start the Vite development server\n'
	@printf '  $(GREEN)make doctor$(RESET)        Inspect UI readiness\n'
	@printf '\n$(BOLD)Quality & inspect$(RESET)\n'
	@printf '  $(CYAN)build$(RESET)              Create a production build\n'
	@printf '  $(CYAN)preview$(RESET)            Preview the production build\n'
	@printf '  $(CYAN)test-api$(RESET)          Check the API health endpoint\n'
	@printf '  $(CYAN)health$(RESET)             Show dependency, build, and API status\n'
	@printf '  $(CYAN)audit$(RESET)             Run npm security audit\n'
	@printf '\n$(BOLD)Maintain$(RESET)\n'
	@printf '  $(CYAN)clean$(RESET)              Remove dependencies and generated files\n\n'

install:
	@printf '$(MAGENTA)✦ Installing UI dependencies...$(RESET)\n'
	@$(NPM) install --no-audit --no-fund
	@printf '$(GREEN)✔ UI dependencies installed.$(RESET)\n'

dev:
	@if [ ! -d node_modules ]; then printf '$(RED)✘ node_modules is missing; run make install first.$(RESET)\n'; exit 1; fi
	@printf '\n$(BOLD)$(MAGENTA)⚛ SHADE-ai UI$(RESET)  →  http://localhost:$(PORT)/\n'
	@printf '$(DIM)API proxy target: $(API_URL)/api/$(RESET)\n\n'
	@$(NPM) run dev -- --host 127.0.0.1 --port $(PORT)

build:
	@printf '$(MAGENTA)✦ Building the React UI...$(RESET)\n'
	@$(NPM) run build
	@test -d dist
	@printf '$(GREEN)✔ UI build completed in web/dist/.$(RESET)\n'

preview:
	@if [ ! -d dist ]; then printf '$(RED)✘ dist/ is missing; run make build first.$(RESET)\n'; exit 1; fi
	@$(NPM) run preview -- --host 127.0.0.1 --port $(PORT)

test-api:
	@command -v curl >/dev/null 2>&1 || { printf '$(RED)✘ curl is required.$(RESET)\n'; exit 1; }
	@curl --fail --silent --show-error $(API_URL)/api/health/ | python3 -m json.tool

health:
	@printf '\n$(BOLD)$(MAGENTA)💓 SHADE-ai UI health$(RESET)\n'
	@printf '  Dependencies: '; test -d node_modules && printf '$(GREEN)ready$(RESET)\n' || printf '$(YELLOW)missing$(RESET)\n'
	@printf '  Build:        '; test -d dist && printf '$(GREEN)present$(RESET)\n' || printf '$(DIM)not created$(RESET)\n'
	@printf '  API:          '; curl --silent --fail $(API_URL)/api/health/ >/dev/null 2>&1 && printf '$(GREEN)reachable$(RESET)\n' || printf '$(YELLOW)unavailable$(RESET)\n'

status: health

doctor:
	@printf '\n$(BOLD)$(MAGENTA)🩺 SHADE-ai UI doctor$(RESET)\n'
	@printf '  Node:         '; command -v node >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$(node --version)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  npm:          '; command -v npm >/dev/null 2>&1 && printf '$(GREEN)✔ %s$(RESET)\n' "$$(npm --version)" || printf '$(RED)✘ missing$(RESET)\n'
	@printf '  node_modules: '; test -d node_modules && printf '$(GREEN)✔ ready$(RESET)\n' || printf '$(YELLOW)○ run make install$(RESET)\n'
	@printf '  package lock: '; test -f package-lock.json && printf '$(GREEN)✔ present$(RESET)\n' || printf '$(YELLOW)○ missing$(RESET)\n'

clean-build:
	@rm -rf dist .vite
	@printf '$(GREEN)✔ UI build files removed.$(RESET)\n'

clean-cache:
	@rm -rf .vite node_modules/.vite
	@printf '$(GREEN)✔ Vite caches removed.$(RESET)\n'

clean: clean-build clean-cache
	@rm -rf node_modules package-lock.json
	@printf '$(GREEN)✔ UI dependencies and lockfile removed.$(RESET)\n'

deps-check:
	@$(NPM) outdated || test $$? -eq 1

audit:
	@$(NPM) audit
