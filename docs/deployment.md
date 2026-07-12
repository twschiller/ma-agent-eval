# Deployment & sysadmin guide

First-time setup and day-two operations for running this app on **Fly.io** with
**Neon** Postgres. Behavior lives in `docs/requirements/`; the *why* behind these
choices lives in `docs/decisions/`. This file is the *how*.

The authoritative config is the code, not this prose: `fly.toml` (app/scaling),
`Dockerfile` (image), `config/settings/production.py` (Django prod settings), and
`.env.example` (the env-var contract). If this guide and those disagree, they
win — fix this guide.

## Prerequisites

- [`flyctl`](https://fly.io/docs/flyctl/install/) installed and `fly auth login`.
- A Fly.io org you can deploy to, and billing enabled.
- A [Neon](https://neon.tech) project (the Postgres database — see below). We do
  **not** use `fly postgres`.
- `uv` for running management commands locally (`make install`).

## Architecture at a glance

- **One Fly app** (`ma-agent-eval`, region `iad`), scale-to-zero:
  `min_machines_running = 0`, so the first request after idle pays a cold start.
- **Gunicorn** serves `config.wsgi` on port 8000; Fly terminates TLS and forces
  HTTPS. Static assets are served in-process by **WhiteNoise** (no bucket, no CDN),
  collected at image-build time.
- **Neon** is the database, reached over `DATABASE_URL`. Migrations run
  automatically on every deploy via the `release_command` in `fly.toml`.
- **Health check**: Fly polls `GET /api/healthz` (unauthenticated, returns
  `{"status": "ok"}`).

## First-time setup

### 1. Provision the database (Neon)

1. Create a Neon project; create a database (e.g. `maeval`).
2. Copy the **pooled** connection string. It must keep `sslmode=require`:
   `postgres://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require`.

Use the pooled endpoint, not the direct one — scale-to-zero means bursty,
short-lived connections.

### 2. Create the Fly app

```sh
fly launch --no-deploy      # creates the app; keep the committed fly.toml
```

`fly.toml` is already written (app name, region, scaling, health check, release
command). If `fly launch` offers to overwrite it or provision a Postgres cluster,
**decline both** — the file is the source of truth and Neon is the database.

### 3. Set secrets

Secrets are injected at runtime via `fly secrets set` (never committed, never in
`fly.toml`'s `[env]`). Production fails loudly if `DJANGO_SECRET_KEY`,
`DATABASE_URL`, or `DJANGO_ALLOWED_HOSTS` are missing.

```sh
# Database (from Neon, step 1)
fly secrets set DATABASE_URL='postgres://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require'

# Django secret key (generate a fresh one)
fly secrets set DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"

# Invite-only signup gate (ADR-0008). Set a shared code to gate the trial;
# leave unset for open signup. Rotating it invalidates it for everyone.
fly secrets set SIGNUP_INVITE_CODE="$(python -c 'import secrets; print(secrets.token_urlsafe(12))')"
```

`DJANGO_SETTINGS_MODULE`, `DJANGO_ALLOWED_HOSTS`, and other non-secret config are
already set in `fly.toml`'s `[env]`. If you serve a custom domain, add it to
`DJANGO_ALLOWED_HOSTS` there (comma-separated) — `CSRF_TRUSTED_ORIGINS` is derived
from it automatically.

### 4. Deploy

```sh
make deploy      # == fly deploy
```

The build runs migrations via `release_command` before the new machines take
traffic. First deploy creates the schema.

### 5. Create the first admin user

The Django admin has no separate login — it routes through the site's session
login (ADR/`config/urls.py`), so you need a real superuser account:

```sh
fly ssh console -C "python manage.py createsuperuser"
```

Then sign in at `/admin/` (you'll be redirected through `/login/`). Admin is where
content moderation happens (ADR-0004).

## Day-two operations

| Task                      | Command                                           |
| ------------------------- | ------------------------------------------------- |
| Deploy                    | `make deploy`                                     |
| Tail logs                 | `fly logs`                                        |
| Open a shell              | `fly ssh console`                                 |
| Run a management command  | `fly ssh console -C "python manage.py <cmd>"`     |
| Django shell              | `fly ssh console -C "python manage.py shell"`     |
| App status / machines     | `fly status`                                      |
| List secrets (names only) | `fly secrets list`                                |
| Rotate a secret           | `fly secrets set KEY=value` (triggers a redeploy) |
| Rotate the invite code    | `fly secrets set SIGNUP_INVITE_CODE=...`          |

### Migrations

Applied automatically on deploy (`release_command = "python manage.py migrate --noinput"`). If a release fails during migration, the deploy aborts and the old
version keeps serving. To run one out of band:
`fly ssh console -C "python manage.py migrate"`.

### Database backups

Backups and point-in-time recovery are managed in the **Neon** console, not Fly.
Confirm PITR/retention is configured there.

## Troubleshooting

- **Deploy fails at the release step** — almost always a migration or a bad
  `DATABASE_URL`. Check `fly logs`; verify the secret with `fly secrets list` and
  that the Neon endpoint is reachable.
- **`DisallowedHost` / 400 on a new domain** — add the host to
  `DJANGO_ALLOWED_HOSTS` in `fly.toml` and redeploy.
- **Static assets 404** — `collectstatic` runs at image build (see `Dockerfile`);
  a failure there surfaces in the build logs, not at runtime. Rebuild.
- **First request is slow** — expected cold start from scale-to-zero
  (`min_machines_running = 0`). Raise it to `1` in `fly.toml` to keep one warm.
- **Signup unexpectedly open or closed** — check whether `SIGNUP_INVITE_CODE` is
  set (`fly secrets list`); empty means open signup (ADR-0008).

## Environment variables

The full contract is `.env.example` (local) and `config/settings/`. Production
requires, at minimum:

| Variable                 | Where set          | Purpose                                      |
| ------------------------ | ------------------ | -------------------------------------------- |
| `DATABASE_URL`           | secret             | Neon pooled Postgres URL (`sslmode=require`) |
| `DJANGO_SECRET_KEY`      | secret             | Django cryptographic signing key             |
| `DJANGO_ALLOWED_HOSTS`   | `fly.toml` `[env]` | Comma-separated allowed hosts                |
| `DJANGO_SETTINGS_MODULE` | `fly.toml` `[env]` | `config.settings.production`                 |
| `SIGNUP_INVITE_CODE`     | secret (optional)  | Gates web signup; empty = open (ADR-0008)    |
