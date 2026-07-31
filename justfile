default:
    @just --list

format:
    uv run --with ruff ruff format . && uv run --with ruff ruff check --fix . || true

lint:
    uv run --with ruff ruff check .

test:
    uv run --with pytest pytest tests -q

ci: lint test

build:
    @rm -rf dist && uv build

clean:
    @rm -rf dist build .pytest_cache .ruff_cache .venv
