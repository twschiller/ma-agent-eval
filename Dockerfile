# Multi-stage build for a uv-managed Django app deployed to Fly.io.
# Stage 1 installs deps into /app/.venv with the cache mounted; stage 2 is a
# slim runtime that copies the venv and runs gunicorn as a non-root user.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev
# Collect static assets (served by WhiteNoise) at build time.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DATABASE_URL=postgres://build:build@localhost/build \
    DJANGO_SECRET_KEY=build-only \
    DJANGO_ALLOWED_HOSTS=build.invalid \
    /app/.venv/bin/python manage.py collectstatic --noinput

FROM python:3.14-slim-bookworm AS runtime
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
# Unbuffered stdout/stderr so logs reach `fly logs` promptly.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
