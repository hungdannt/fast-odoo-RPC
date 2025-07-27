# OdooFlow Development Makefile

.PHONY: help install test test-cache test-redis test-transaction test-all setup-redis stop-redis clean-redis lint format

# Default target
help:
	@echo "🚀 OdooFlow Development Commands"
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  install          Install dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test             Run all tests"
	@echo "  test-core        Run core tests (models, query, cache, batch, etc.)"
	@echo "  test-cache       Run cache tests"
	@echo "  test-redis       Run Redis cache tests (requires Redis)"
	@echo "  test-transaction Run transaction tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  upload-coverage  Upload coverage to Codecov"
	@echo ""
	@echo "🐳 Redis Testing:"
	@echo "  setup-redis      Start Redis test container"
	@echo "  stop-redis       Stop Redis test container"
	@echo "  clean-redis      Remove Redis test container and data"
	@echo "  redis-status     Check Redis container status"
	@echo ""
	@echo "🔧 Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code"
	@echo "  type-check       Run type checking"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean            Clean build artifacts"
	@echo "  clean-all        Clean everything including Redis"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"
	pip install aioredis  # For Redis cache testing

# Core testing
test:
	python -m pytest --tb=short

test-core:
	python -m pytest tests/test_models.py tests/test_query_builder.py tests/test_query_cache.py tests/test_batch_execution.py tests/test_circuit_breaker.py tests/test_retry_mechanism.py tests/test_phase4_features.py -v

test-cache:
	python -m pytest tests/test_cache_comprehensive.py -v

test-redis: setup-redis
	@echo "🧪 Running Redis cache tests..."
	python -m pytest tests/test_cache_comprehensive.py::TestRedisCache -v

test-transaction:
	python -m pytest tests/test_transaction_comprehensive.py -v

test-coverage:
	python -m pytest tests/ --cov=src/zenoo_rpc --cov-report=xml --cov-report=html --cov-report=term-missing --ignore=tests/performance/test_zenoo_vs_odoorpc_benchmark.py --tb=short

upload-coverage:
	@echo "📤 Uploading coverage to Codecov..."
	./scripts/upload_coverage.sh

# Redis management
setup-redis:
	@echo "🐳 Setting up Redis test container..."
	@if ! docker info > /dev/null 2>&1; then \
		echo "❌ Docker is not running. Please start Docker first."; \
		exit 1; \
	fi
	docker compose -f docker-compose.test.yml up -d redis-test
	@echo "⏳ Waiting for Redis to be ready..."
	@timeout=30; counter=0; \
	while [ $$counter -lt $$timeout ]; do \
		if docker exec odooflow-redis-test redis-cli ping > /dev/null 2>&1; then \
			echo "✅ Redis is ready on port 6380!"; \
			break; \
		fi; \
		echo "⏳ Waiting for Redis... ($$counter/$$timeout)"; \
		sleep 1; \
		counter=$$((counter + 1)); \
	done; \
	if [ $$counter -eq $$timeout ]; then \
		echo "❌ Redis failed to start within $$timeout seconds"; \
		docker compose -f docker-compose.test.yml logs redis-test; \
		exit 1; \
	fi

stop-redis:
	@echo "🛑 Stopping Redis test container..."
	docker compose -f docker-compose.test.yml stop redis-test

clean-redis:
	@echo "🧹 Cleaning Redis test container and data..."
	docker compose -f docker-compose.test.yml down -v
	docker volume rm odooflow_redis_test_data 2>/dev/null || true

redis-status:
	@echo "📊 Redis container status:"
	@docker compose -f docker-compose.test.yml ps redis-test || echo "Redis container not found"
	@if docker exec odooflow-redis-test redis-cli ping > /dev/null 2>&1; then \
		echo "✅ Redis is responding"; \
		echo "📊 Redis info:"; \
		docker exec odooflow-redis-test redis-cli info server | grep redis_version; \
		docker exec odooflow-redis-test redis-cli info memory | grep used_memory_human; \
	else \
		echo "❌ Redis is not responding"; \
	fi

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/zenoo_rpc

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean clean-redis
