# AGENTS.md

Source of truth for the engineering context an agent needs to work safely here.
Keep it about how the code is *shaped* (layout, what owns what, commands,
conventions) — behavior lives in `docs/requirements/`, decisions in
`docs/decisions/`.

> Claude Code reads `CLAUDE.md`. Keep `CLAUDE.md` a one-line stub — `@AGENTS.md`
> — so there is a single source and every agent reads the same thing.

## What this is

A public catalog + eval harness for AI agents acting on Massachusetts / Boston
civic services: humans and agents submit tasks-to-be-done ("renew my library
card"), the public upvotes them, and agents submit run traces (model, harness,
tools, outcome). See `BRIEF.md` for the working-group context.

## Stack

- Python 3.14, managed by `uv` (`pyproject.toml` + `uv.lock`).
- Django 6 + Django Ninja for the HTTP/API surface (mounted at `/api/`).
- Postgres (Neon in prod, local Postgres for dev) via `dj-database-url`.
- pyright (types), ruff (lint + format), semgrep (project static analysis),
  bandit (Python security), tach (import boundaries), pytest, pre-commit.
- Deployed to Fly.io (one always-warm machine); static assets served by WhiteNoise.

## Layout

```text
config/                 # composition root: settings/, api.py, urls, asgi/wsgi
  settings/             # base / local / production / test
  api.py                # NinjaAPI; mounts app routers; /api/healthz
maeval/                 # domain apps
  common/               # shared infra (ULID-pk TimestampedModel) — import anywhere
  submissions/          # one app per domain: models -> schemas -> views
  web/                  # human-facing server-rendered UI (templates+htmx+Bootstrap)
tools/                  # standalone scripts (export_openapi.py)
docs/decisions/         # ADRs (MADR-minimal), README.md index
docs/requirements/      # golden specs, one per behavioral area
docs/deployment.md      # sysadmin runbook: first-time Fly.io + Neon setup, ops
.semgrep/               # project static-analysis rules (add incrementally)
```

Each API app is layered `views -> schemas -> models` (Ninja routers live in
`views.py`, mounted in `config/api.py`); `tach.toml` enforces it. No per-app
`urls.py` — *except* `maeval/web`, the human-facing UI (ADR-0006), which has no
Ninja router and so owns a namespaced `urls.py` included at the site root. The
web app renders existing domains as HTML (templates+htmx+Bootstrap 5) and is
absent from the OpenAPI contract; humans use session login, agents use API keys.

## Commands

All commands run through `uv run`. `DATABASE_URL` must be set for anything that
touches the DB.

- `make install` — `uv sync`
- `make run` — dev server
- `make test` — `uv run pytest`
- `make lint` — `uv run pre-commit run --all-files`
- `make boundaries` — `uv run tach check`
- `make semgrep` — project static-analysis rules
- `make schema` — regenerate + lint `openapi.json`
- `make migrate` — apply migrations
- `make deploy` — `fly deploy` (first-time setup + ops: `docs/deployment.md`)

## Conventions

- Catch as `exc`, never `e` (enforced by a pre-commit pygrep hook).
- Every suppression (`# noqa`, `# type: ignore[code]`, `# nosemgrep`,
  `# pragma: no cover`) carries a reason explaining *why*.
- Use `django.utils.timezone.now()`, never naive `datetime.now()`.
- ULID primary keys via `common`'s `TimestampedModel`.
- Content authored by an AI agent must be distinguishable from human content
  (`submitted_by_agent`) — a hard requirement from `BRIEF.md`.
- The API is the agent-facing contract: regenerate `openapi.json` (`make schema`)
  when endpoints change; the change shows up in the diff.
- New behavior or a contract change updates the matching spec in
  `docs/requirements/` in the same PR.
- Architecturally significant decisions get an ADR before the code merges.
- Static-analysis plumbing (semgrep, bandit, ruff, tach, pyright) is already
  wired — add rules incrementally, don't bolt on new tools piecemeal.

## Design system

The human web UI (`maeval/web`) follows a committed design system, not ad-hoc
styling. `PRODUCT.md` (audience, brand, principles) and `DESIGN.md` ("The Public
Ledger" — tokens, type, components, named rules) at the repo root are the source
of truth; they're realized in `maeval/web/static/web/css/maeval.css` and the
`web/` templates. Keep `DESIGN.md` and the CSS in step — new tokens or type steps
get documented in `DESIGN.md` rather than dropped in as one-off literals.

Design work is done with the **impeccable** skill (design/critique/audit/polish
flows and a UI-change detector hook). It is *not* vendored — install it
per-developer with `npx impeccable` (see <https://impeccable.style>); the skill
dirs and its local hook config are gitignored. Only its *outputs* — `PRODUCT.md`,
`DESIGN.md`, and `.impeccable/` — are committed.
