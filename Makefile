.PHONY: dev-backend dev-frontend dev test lint format install install-backend install-frontend build clean docker-up docker-down docker-logs help

BACKEND_DIR = backend
FRONTEND_DIR = frontend
BACKEND_PORT ?= 7860

help:
	@echo "Usage:"
	@echo "  make dev-backend     Start FastAPI (uvicorn) on port $(BACKEND_PORT)"
	@echo "  make dev-frontend    Start Next.js dev server on port 3000"
	@echo "  make dev             Start both backend and frontend concurrently"
	@echo "  make test            Run pytest"
	@echo "  make lint            Run flake8 (backend) + eslint (frontend)"
	@echo "  make format          Auto-format Python with black (backend)"
	@echo "  make install         Install all dependencies (backend + frontend)"
	@echo "  make install-backend Install Python dependencies"
	@echo "  make install-frontend Install Node.js dependencies"
	@echo "  make build           Build frontend for production"
	@echo "  make clean           Remove __pycache__, .next, build artifacts"
	@echo "  make docker-up       Start all Docker services"
	@echo "  make docker-down     Stop all Docker services"
	@echo "  make docker-logs     Tail Docker logs"

dev-backend:
	cd $(BACKEND_DIR) && uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

dev:
	@echo "Starting backend (port $(BACKEND_PORT)) and frontend (port 3000)..."
	$(MAKE) dev-backend & $(MAKE) dev-frontend & wait

test:
	cd $(BACKEND_DIR) && python -m pytest -v

lint:
	cd $(BACKEND_DIR) && flake8 .
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && black .

install: install-backend install-frontend

install-backend:
	pip install -r $(BACKEND_DIR)/requirements.txt

install-frontend:
	cd $(FRONTEND_DIR) && npm install

build:
	cd $(FRONTEND_DIR) && npm run build

clean:
	rm -rf .venv
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/**/__pycache__
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/out
	rm -rf $(FRONTEND_DIR)/build
	rm -rf .pytest_cache

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
