.PHONY: bootstrap up down migrate seed dev test lint format clean logs infra-smoke

PY := uv run python
NODE := pnpm

# Auto-load .env so `make migrate` (and anyone reading LOOP_*_URL etc.) sees
# the operator's port overrides and DB credentials. Without this, sub-commands
# fall back to the in-source defaults (port 5432 / 6379) and collide with
# Homebrew services on a developer laptop.
ifneq (,$(wildcard ./.env))
include .env
export
endif

bootstrap:
	uv sync --all-packages
	$(NODE) -C apps/studio install
	$(NODE) -C apps/docs install
	pre-commit install

up:
	# Pass --env-file explicitly. With `-f infra/docker-compose.yml`,
	# docker compose's "project directory" is `infra/`, so it would
	# normally look for `infra/.env` and miss the repo-root `.env`.
	docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
	@docker compose --env-file .env -f infra/docker-compose.yml ps

down:
	docker compose --env-file .env -f infra/docker-compose.yml down

infra-smoke:
	./tools/infra_smoke.sh

migrate:
	$(PY) -m loop_control_plane.migrations upgrade head
	$(PY) -m loop_data_plane.migrations upgrade head

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
	docker compose --env-file .env -f infra/docker-compose.yml logs -f $(SERVICE)

clean:
	rm -rf .venv node_modules **/__pycache__ .pytest_cache .ruff_cache
