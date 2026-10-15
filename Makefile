.PHONY: install dev test lint up seed down
install:
	pip install -e ".[dev,postgres]"
dev:
	uvicorn app.main:app --reload
test:
	pytest -q
lint:
	ruff check . && ruff format --check .
up:
	docker compose up -d --build
seed:
	python scripts/seed.py
down:
	docker compose down -v
