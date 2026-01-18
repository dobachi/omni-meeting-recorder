.PHONY: all lint typecheck test check clean install dev-install help

# Default target
all: check

# Install dependencies
install:
	uv sync

# Install with dev dependencies
dev-install:
	uv sync --extra dev

# Run linter (ruff)
lint:
	uv run ruff check src/ tests/

# Run linter with auto-fix
lint-fix:
	uv run ruff check --fix src/ tests/

# Run type checker (mypy)
typecheck:
	uv run mypy src/

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=src/omr --cov-report=term-missing

# Run all checks (lint + typecheck + test)
check: lint typecheck test

# Format code
format:
	uv run ruff format src/ tests/

# Clean up cache files
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Show help
help:
	@echo "Available targets:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev-install  - Install with dev dependencies"
	@echo "  make lint         - Run ruff linter"
	@echo "  make lint-fix     - Run ruff linter with auto-fix"
	@echo "  make typecheck    - Run mypy type checker"
	@echo "  make test         - Run pytest"
	@echo "  make test-cov     - Run pytest with coverage"
	@echo "  make check        - Run all checks (lint + typecheck + test)"
	@echo "  make format       - Format code with ruff"
	@echo "  make clean        - Clean up cache files"
