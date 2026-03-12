.PHONY: install run worker fmt lint test migrate

install:
	uv sync

run:
	mkdir -p ./media
	docker compose up -d
	uv run uvicorn main:app --reload --app-dir src

worker:
	cd src && uv run celery -A celery_app worker --loglevel=info --pool=gevent --concurrency=1

fmt:
	uv run ruff format src

lint:
	uv run ruff check src

test:
	uv run pytest

migrate:
	uv run alembic upgrade head
