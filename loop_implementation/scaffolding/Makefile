.PHONY: bootstrap up down migrate seed dev test lint format clean logs

PY := uv run python
NODE := pnpm

bootstrap:
	uv sync --all-packages
	$(NODE) -C apps/studio install
	$(NODE) -C apps/docs install
	pre-commit install

up:
	docker compose -f infra/docker-compose.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker compose -f infra/docker-compose.yml ps

down:
	docker compose -f infra/docker-compose.yml down

migrate:
	$(PY) -m loop.cp_migrations upgrade head
	$(PY) -m loop.dp_migrations upgrade head

seed:
	$(PY) tools/seed_dev.py

dev:
	@command -v tmux >/dev/null || { echo "tmux required"; exit 1; }
	./tools/dev.sh

test:
	uv run pytest -q
	$(NODE) -C apps/studio test

lint:
	uv run ruff check .
	uv run pyright
	$(NODE) -C apps/studio lint
	cd cli && golangci-lint run

format:
	uv run ruff format .
	uv run ruff check --fix .
	$(NODE) -C apps/studio format

logs:
	docker compose -f infra/docker-compose.yml logs -f $(SERVICE)

clean:
	rm -rf .venv node_modules **/__pycache__ .pytest_cache .ruff_cache
