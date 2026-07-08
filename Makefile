.PHONY: help install dev backend frontend test lint migrate docker clean

help:
	@echo "HireIQ — AI Hiring Intelligence Platform"
	@echo ""
	@echo "Commands:"
	@echo "  make install     Install all dependencies"
	@echo "  make dev         Start backend + frontend in dev mode"
	@echo "  make backend     Start backend only"
	@echo "  make frontend    Start frontend only"
	@echo "  make test        Run all backend tests"
	@echo "  make lint        Run ruff linter"
	@echo "  make migrate     Run alembic migrations"
	@echo "  make docker      Start full stack with Docker Compose"
	@echo "  make clean       Remove generated files and caches"

install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm
	cd frontend-next && npm install --legacy-peer-deps

backend:
	uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend-next && npm run dev

dev:
	@echo "Starting backend and frontend..."
	@make backend & make frontend

test:
	pytest tests/backend/ -v --tb=short

test-cov:
	pytest tests/backend/ -v --cov=backend --cov-report=html --cov-report=term-missing

lint:
	ruff check backend/ --fix

format:
	ruff format backend/

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(msg)"

migrate-down:
	alembic downgrade -1

docker:
	docker compose up --build

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage uploads/*.pdf uploads/*.docx 2>/dev/null || true
	cd frontend-next && rm -rf .next 2>/dev/null || true
