# Self-documenting entry point for common tasks. Everything runs through uv.
.PHONY: install migrate run test lint boundaries semgrep schema deploy

install:  ## Sync dependencies into .venv
	uv sync

migrate:  ## Apply database migrations
	uv run python manage.py migrate

run:  ## Run the dev server
	uv run python manage.py runserver

test:  ## Run the test suite
	uv run pytest

lint:  ## Run all pre-commit hooks
	uv run pre-commit run --all-files

boundaries:  ## Check module/layer boundaries
	uv run tach check

semgrep:  ## Run project static-analysis rules
	uv run semgrep scan --config .semgrep --error

schema:  ## Regenerate and lint the OpenAPI schema
	uv run python tools/export_openapi.py
	npx @stoplight/spectral-cli@6.16.0 lint openapi.json

deploy:  ## Deploy to Fly.io
	fly deploy
