.PHONY: install dev test lint type-check ci clean build-www

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest --cov=viznoir --cov-report=term-missing -q

lint:
	ruff check src/ tests/

lint-fix:
	ruff check src/ tests/ --fix

type-check:
	mypy src/viznoir/ --ignore-missing-imports

ci: lint type-check test

build-www:
	cd www && npm install && npm run build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
