##
# NTUST AOI — Makefile
# Unified command interface for development, testing, and deployment.
# Always activate the conda environment first: conda activate aoi_env
##

.PHONY: help setup install start stop restart test check-api \
        db-up db-down db-reset db-mock db-check \
        api ui-dev plc-sim camera-sim shopfloor-sim controller \
        ui-build lint-py update-docs git-check check-db check-ui

## ─── Defaults ────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ─── Setup ───────────────────────────────────────────────────────────────────

setup: install ## Alias for install — conda env must be active first (conda activate aoi_env)

install: ## Install all Python and Node dependencies
	@echo "==> Installing Python dependencies..."
	pip install -r ntust_aoi_pcb_db/requirements.txt
	@echo "==> Installing Node dependencies..."
	cd NTUST-AOI-UI && npm install
	@echo "Done. Activate environment: conda activate aoi_env"

## ─── System Lifecycle ────────────────────────────────────────────────────────

start: ## Start full system: DB (Docker) + FastAPI + React UI + all simulators
	python headless_runner.py start

stop: ## Stop all services cleanly (Docker, Python, Node processes)
	python headless_runner.py stop

restart: stop start ## Stop then restart all services

## ─── Database ────────────────────────────────────────────────────────────────

db-up: ## Start PostgreSQL + pgAdmin + Nginx (Docker only)
	cd ntust_aoi_pcb_db && docker compose up -d
	@echo "PostgreSQL: localhost:5433 | pgAdmin: http://localhost:5050 | Nginx: http://localhost:8080"

db-down: ## Stop and remove Docker containers
	cd ntust_aoi_pcb_db && docker compose down

db-reset: ## DANGER: Truncate all database tables (dev only)
	@echo "WARNING: This will delete all data. Press Ctrl+C to abort, or Enter to continue."
	@read confirm
	cd ntust_aoi_pcb_db && python scripts/reset_db.py

db-mock: ## Seed database with mock data for UI development
	cd ntust_aoi_pcb_db && python scripts/generate_mock_data.py

## ─── Individual Services ─────────────────────────────────────────────────────

api: ## Start FastAPI backend only (DB must be running first)
	cd ntust_aoi_pcb_db && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui-dev: ## Start React dev server only (API must be running first)
	cd NTUST-AOI-UI && npm run dev

plc-sim: ## Start PLC simulator only (port 15000)
	cd simulation && python plc_sim.py --host 127.0.0.1 --port 15000

camera-sim: ## Start camera simulator only (port 16000)
	cd simulation && python camera_sim.py --host 127.0.0.1 --port 16000

shopfloor-sim: ## Start MES/Shopfloor API simulator only (port 9090)
	cd simulation && python shopfloor_sim.py

controller: ## Start PC controller (connects to simulators by default)
	cd machine_control && python pc_controller.py --mode semi-auto --api-mode fixture

## ─── Testing & Verification ──────────────────────────────────────────────────

test: ## Run end-to-end integration test (system must be running: make start)
	@echo "==> Running E2E integration test..."
	python test_sn5434.py

check-api: ## Quick API health check: hits /system/status and /runs/
	@echo "==> GET /system/status"
	curl -s http://localhost:8000/system/status | python -m json.tool
	@echo ""
	@echo "==> GET /runs/ (first 3)"
	curl -s "http://localhost:8000/runs/?limit=3" | python -m json.tool

check-db: ## Check if PostgreSQL is accepting connections (reads credentials from .env)
	@set -a && . ./.env && set +a && \
	python -c "import psycopg2, os; conn = psycopg2.connect(\
	  dbname=os.environ['DB_NAME'], \
	  user=os.environ['DB_USER'], \
	  password=os.environ['DB_PASSWORD'], \
	  host=os.environ.get('DB_HOST','127.0.0.1'), \
	  port=os.environ.get('DB_PORT','5433')); print('DB OK'); conn.close()"

check-ui: ## Check if React UI is responding
	curl -s -o /dev/null -w "UI HTTP status: %{http_code}\n" http://localhost:3001

## ─── Build (Production) ──────────────────────────────────────────────────────

ui-build: ## Build React UI for production (outputs to NTUST-AOI-UI/dist/)
	cd NTUST-AOI-UI && npm run build
	@echo "Build output: NTUST-AOI-UI/dist/"

## ─── Code Quality ────────────────────────────────────────────────────────────

lint-py: ## Run flake8 linter on Python modules
	flake8 machine_control/ ntust_aoi_pcb_db/api/ simulation/ --max-line-length=120 --ignore=E501,W503

## ─── Documentation ───────────────────────────────────────────────────────────

update-docs: ## Show which docs need updating based on current git changes (run after modifying code)
	@echo "==> Files changed since last commit:"
	@git diff --name-only HEAD 2>/dev/null || echo "  (no git changes detected)"
	@echo ""
	@echo "==> Documentation to update:"
	@git diff --name-only HEAD 2>/dev/null | grep -q "machine_control/" \
	  && echo "  → machine_control/README.md" \
	  && echo "  → machine_control/ARCHITECTURE.md" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "ntust_aoi_pcb_db/api/" \
	  && echo "  → ntust_aoi_pcb_db/README.md" \
	  && echo "  → ntust_aoi_pcb_db/ARCHITECTURE.md" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "ntust_aoi_pcb_db/sql/" \
	  && echo "  → ntust_aoi_pcb_db/ARCHITECTURE.md" \
	  && echo "  → docs/reference/DATABASE_SCHEMA.md" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "NTUST-AOI-UI/" \
	  && echo "  → NTUST-AOI-UI/README.md" \
	  && echo "  → NTUST-AOI-UI/ARCHITECTURE.md" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "simulation/" \
	  && echo "  → simulation/README.md" \
	  && echo "  → simulation/ARCHITECTURE.md" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "Makefile" \
	  && echo "  → README.md (Makefile command reference table)" || true
	@git diff --name-only HEAD 2>/dev/null | grep -q "docker-compose.yml" \
	  && echo "  → ntust_aoi_pcb_db/README.md" \
	  && echo "  → ARCHITECTURE.md" || true
	@echo "  → PROGRESS.md (always — if a new feature or fix was added)"
	@echo ""
	@echo "  NOTE: docs/system architect overall/ is HUMAN-ONLY. Never edit with AI."

## ─── Git Safety ──────────────────────────────────────────────────────────────

git-check: ## Pre-work safety check: branch, status, recent commits, conflict markers
	@echo "==> Current branch:"
	@BRANCH=$$(git branch --show-current 2>/dev/null || echo "unknown"); \
	echo "  $$BRANCH"; \
	if [ "$$BRANCH" = "main" ]; then \
	  echo "  ⚠️  WARNING: You are on 'main'! Create a feature branch before making changes."; \
	  echo "  Run: git checkout -b feat/<description>"; \
	fi
	@echo ""
	@echo "==> Recent commits:"
	@git log --oneline -5 2>/dev/null || echo "  (no commits yet)"
	@echo ""
	@echo "==> Working tree status:"
	@git status --short 2>/dev/null || echo "  (not a git repository)"
	@echo ""
	@echo "==> Conflict markers (unresolved merges):"
	@CONFLICTS=$$(git diff --name-only --diff-filter=U 2>/dev/null); \
	if [ -n "$$CONFLICTS" ]; then \
	  echo "  ⛔ CONFLICTS DETECTED — human must resolve:"; \
	  echo "$$CONFLICTS" | sed 's/^/    /'; \
	  git diff --diff-filter=U 2>/dev/null; \
	else \
	  echo "  None found."; \
	fi
