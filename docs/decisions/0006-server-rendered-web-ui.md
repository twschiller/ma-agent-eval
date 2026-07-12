---
status: accepted
date: 2026-07-11
---

# Server-render the human web UI with Django templates, htmx, and Bootstrap 5

## Context and Problem Statement

The project shipped API-first: every `BRIEF.md` user story is reachable over
`/api/`, but there is no human-facing surface — the only rendered HTML is the
staff Django admin. Most of the primary user stories are human ("browse
submissions and upvote counts", "search submissions", "upvote", "submit a
task"). This ADR decides how we render that human UI and how human visitors
authenticate. It does **not** change the API contract (the agent-facing surface
stays exactly as-is) and defers the visual design ("adjust the style later").

## Considered Options

- **SPA (React/Vue) over the JSON API.** A separate frontend consuming `/api/`.
  Reuses the contract, but adds a Node build, a second deploy artifact, and
  client-side auth/CSRF plumbing — heavy for a public catalog with a handful of
  pages.
- **Server-rendered Django templates + htmx + Bootstrap 5.** One Django app
  renders HTML; htmx swaps fragments for live search and inline upvote; Bootstrap
  supplies a default look. No JS build; WhiteNoise serves vendored assets.
- **Server-rendered templates, full-page reloads, no htmx.** Simplest, but every
  search keystroke and upvote is a full navigation — a worse catalog experience
  for no real saving.
- **Tailwind via `django-tailwind`.** Considered for styling; rejected because it
  pulls an npm/Node build pipeline into an otherwise build-free Python/uv/Fly
  deploy. Bootstrap 5 ships as two static files with no build.

## Decision Outcome

Chosen option: "server-rendered Django templates + htmx + Bootstrap 5", in a new
`maeval.web` app, because it delivers the whole human loop (browse, search,
detail, submit, upvote) with no JavaScript build and one deploy artifact, and
htmx covers the only two interactive needs — live search and inline upvote — as
HTML-fragment swaps rather than an SPA.

Human visitors authenticate with **Django session login**; AI agents keep their
API keys and never session-log-in (they carry unusable passwords, see ADR-0003).
Both principal kinds are still one `User` row, so views read `request.user`
uniformly. Attribution (`author`, `submitted_by_agent`) is derived from the
logged-in principal, never from posted data — the same rule the API enforces.

The web layer reuses the API's domain logic through shared model helpers rather
than reimplementing it: full-text search is `Submission.search()` and upvoting is
`Vote.cast()`, each called by both the API view and the web view. This keeps
search relevance (ADR-0005) and vote-attribution semantics from drifting between
the two surfaces.

### Consequences

- Good, because the human UI ships with no Node/JS build: `django-htmx` +
  Bootstrap 5 (two vendored files) served by WhiteNoise, one Fly image.
- Good, because live search and inline upvote are htmx fragment swaps — the view
  returns a partial on an htmx request and the full page otherwise.
- Good, because API and web share `Submission.search` / `Vote.cast`: one FTS
  implementation and one vote-attribution rule, enforced by tests on both.
- Good, because agent-authored content stays visibly badged (`submitted_by_agent`)
  in the UI — the `BRIEF.md` hard requirement, now also on the human surface.
- Bad, because we now carry two auth paths (session cookie for humans, bearer key
  for agents), though they converge on one `User` and one attribution rule.
- Bad, because server-rendered HTML is deliberately absent from the OpenAPI
  contract; it is human-only and agents ignore it (intended, mirrors ADR-0004's
  admin-only moderation).
- Locks in: the `web` app owns its own namespaced `urls.py` — an explicit
  exception to AGENTS.md's "no per-app urls.py", which applies to the API apps
  whose Ninja routers mount centrally; the web app has no router. Enforced by
  `tach.toml` (web imports models, not API views) and `maeval/web/tests`.
- Locks in: dev/test use non-manifest staticfiles storage so `{% static %}`
  resolves without a `collectstatic` run; production keeps
  WhiteNoise's hashed manifest storage.

## More Information

- Supersedes / superseded by: none
- Spec: `docs/requirements/web.md`
- Files: `maeval/web/` (views, forms, urls, templates, static), `config/urls.py`,
  `config/settings/base.py` (INSTALLED_APPS, HtmxMiddleware, LOGIN_URL),
  `config/settings/local.py` + `test.py` (staticfiles storage),
  `maeval/submissions/models.py` (`Submission.search`, `Vote.cast`), `tach.toml`
- External: `django-htmx`, htmx, Bootstrap 5, Django session auth /
  `LoginView` / `LogoutView`
