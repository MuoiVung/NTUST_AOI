##
# NTUST AOI — Makefile
# Unified command interface for development, testing, and deployment.
# Always activate the conda environment first: conda activate aoi_env
##

.PHONY: help install start stop restart test check-api db-up db-down ui-dev lint-py

## ─── Defaults ────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ─── Setup ───────────────────────────────────────────────────────────────────

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

check-db: ## Check if PostgreSQL is accepting connections
	python -c "import psycopg2; conn = psycopg2.connect(dbname='pcb_aoi_db', user='admin', password='aoi123!', host='127.0.0.1', port=5433); print('DB OK'); conn.close()"

check-ui: ## Check if React UI is responding
	curl -s -o /dev/null -w "UI HTTP status: %{http_code}\n" http://localhost:3001

## ─── Build (Production) ──────────────────────────────────────────────────────

ui-build: ## Build React UI for production (outputs to NTUST-AOI-UI/dist/)
	cd NTUST-AOI-UI && npm run build
	@echo "Build output: NTUST-AOI-UI/dist/"

## ─── Code Quality ────────────────────────────────────────────────────────────

lint-py: ## Run flake8 linter on Python modules
	flake8 machine_control/ ntust_aoi_pcb_db/api/ simulation/ --max-line-length=120 --ignore=E501,W503

## ─── Documentation Check ─────────────────────────────────────────────────────

check-docs: ## Remind to update docs after code changes (P4: docs live with code)
	@echo "==> Documentation checklist:"
	@echo "  - Did you modify machine_control/?   Update machine_control/README.md"
	@echo "  - Did you modify ntust_aoi_pcb_db/?  Update ntust_aoi_pcb_db/README.md + docs/reference/DATABASE_SCHEMA.md"
	@echo "  - Did you modify NTUST-AOI-UI/?      Update NTUST-AOI-UI/README.md"
	@echo "  - Did you modify simulation/?         Update simulation/README.md"
	@echo "  - Did you add a feature?              Update PROGRESS.md"
	@echo ""
	@echo "  Run 'git diff --name-only HEAD' to see what files changed."
