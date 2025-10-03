.PHONY: help install install-dev install-prod test test-unit test-integration test-e2e lint format check setup-db migrate upgrade downgrade dev docker-build docker-up docker-down clean worker worker-beat worker-status worker-purge

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install base dependencies
	pip install -r requirements/base.txt

install-dev: ## Install development dependencies
	pip install -r requirements/dev.txt
	pre-commit install

install-prod: ## Install production dependencies
	pip install -r requirements/prod.txt

test: ## Run all tests
	pytest

test-unit: ## Run unit tests
	pytest tests/unit/

test-integration: ## Run integration tests
	pytest tests/integration/

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/

lint: ## Run linting
	flake8 src tests
	mypy src

format: ## Format code
	black src tests
	isort src tests

check: ## Run all checks (lint + format + test)
	pre-commit run --all-files
	pytest

setup-db: ## Set up database
	python scripts/setup_db.py

migrate: ## Create new migration
	python scripts/create_migration.py

upgrade: ## Upgrade database
	alembic upgrade head

downgrade: ## Downgrade database
	alembic downgrade -1

dev: ## Start development environment
	docker-compose up -d

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/

worker: ## Start Celery worker
	celery -A src.workers.celery_app worker --loglevel=info --concurrency=4

worker-beat: ## Start Celery beat scheduler
	celery -A src.workers.celery_app beat --loglevel=info

worker-status: ## Show worker status
	celery -A src.workers.celery_app inspect active
	celery -A src.workers.celery_app inspect registered
	celery -A src.workers.celery_app inspect stats

worker-purge: ## Purge all task queues
	celery -A src.workers.celery_app purge
