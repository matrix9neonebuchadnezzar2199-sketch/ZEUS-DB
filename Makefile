.PHONY: sync test lint analyze up

sync:
	uv sync --all-groups

test:
	uv run pytest

lint:
	uv run ruff check src tests service
	uv run mypy src tests service

analyze:
	uv run zeusdb analyze $(DB) --carve --json $(OUT)

up:
	uv run uvicorn service.app:app --host 0.0.0.0 --port 8090
