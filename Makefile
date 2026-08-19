.PHONY: dev test migrations up psql

dev:
	uv run python main.py --interface cli

test:
	uv run python -m unittest

migrations:
	uv run python main.py --migrate

up:
	docker compose up

psql:
	docker compose exec -it postgres psql -U pensabot
