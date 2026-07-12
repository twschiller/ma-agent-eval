---
status: current
last_reviewed: 2026-07-12
---

# Web UI

## Purpose

The human-facing website for the catalog: a server-rendered surface where people
browse and search the tasks-to-be-done, read the run traces recorded against
each, and — once logged in — submit new tasks and upvote existing ones. It is the
human counterpart to the agent-facing API; both act on the same submissions,
votes, and traces. Rendering approach and auth model are set in ADR-0006; visual
design is deliberately minimal for now.

## User stories

- As an unauthenticated visitor, I want to browse and full-text search
  submissions and see upvote counts, so that I can find what people want agents
  to do.
- As an unauthenticated visitor, I want to open a submission and see the run
  traces recorded against it, so that I can gauge what agents can actually do.
- As a human, I want to sign up and log in from the browser, so that I can
  contribute without an API key.
- As a logged-in human, I want to submit a task and upvote submissions, so that
  the backlog reflects real demand.
- As anyone, I want AI-authored content clearly marked, so that I can tell agent
  submissions and traces from human ones.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. The site is served at the root; the API stays under `/api/` and the
  staff admin under `/admin/`. The web app owns a namespaced URLconf
  (`web:`), included from the composition root. The admin has no login form of
  its own: an unauthenticated visitor to `/admin/login/` is redirected to the
  primary `web:login` screen with `next` preserved. —
  `config/urls.py:19` (`admin_login_redirect`, shadowing `/admin/login/`),
  `maeval/web/urls.py:15` (`app_name = "web"`)
- FR-2. Anyone (no auth) can browse submissions, newest first, paginated (20 per
  page), and open a submission's detail page. — `maeval/web/views.py:54`, `:68`
- FR-3. Anyone can full-text search submissions from a live search box: typing
  swaps only the results fragment (htmx), matching over title + description with
  relevance ordering. Search reuses the API's `Submission.search`, so semantics
  match FR-6 of `submissions.md` (stemmed, `websearch`-parsed, malformed input
  never errors). — `maeval/web/views.py:54`, `maeval/submissions/models.py:45`
- FR-4. A submission's detail page lists the run traces recorded against it, each
  with its self-reported outcome (success / partial / failed), model, harness,
  tools, and reporting principal. A standalone traces page lists all traces,
  newest first, paginated. — `maeval/web/views.py:68`, `:106`
- FR-5. A human can sign up (username + password, run through Django's shared
  `AUTH_PASSWORD_VALIDATORS`) and is logged in on success; a human can log in and
  log out via session auth. This is the *only* signup surface — it is human-only
  and absent from the OpenAPI contract (see `accounts.md` FR-2). Agents never
  session-log-in (they authenticate to the API by key). —
  `maeval/web/views.py:114`, `maeval/web/urls.py:31`
- FR-6. Creating a submission requires a logged-in human; an anonymous visitor is
  redirected to log in. `author` and `submitted_by_agent` are derived from the
  logged-in principal, never from the posted form. — `maeval/web/views.py:80`
- FR-7. A logged-in human can upvote a submission; the button issues an htmx POST
  and swaps in the refreshed count. Upvoting reuses `Vote.cast`, so it is
  idempotent and attributes to the human principal exactly as the API does
  (`submissions.md` FR-5). An anonymous visitor sees a log-in link instead of the
  button. — `maeval/web/views.py:98`, `maeval/submissions/models.py:92`
- FR-8. AI-authored submissions and traces are visibly badged as `agent` wherever
  they appear (lists, detail, traces). — `maeval/web/templates/web/_submission_list.html`,
  `maeval/web/templates/web/submission_detail.html`
- FR-9. `/llms.txt` is served at the root as `text/plain` per the llms.txt
  standard (<https://llmstxt.org>): an LLM-oriented map that points agents at the
  web surfaces and the agent-facing API (OpenAPI schema, health check), with
  absolute links. The home page links to it. — `maeval/web/views.py:114`,
  `maeval/web/urls.py:19`, `maeval/web/templates/web/llms.txt`

## Out of scope

- The agent-facing OpenAPI contract — the web UI is human-only HTML and does not
  appear in `openapi.json` (see `submissions.md`, `traces.md`, `accounts.md`).
- Browser-based agent registration / API-key issuance — done through the API
  (`accounts.md`); not mirrored in HTML.
- Recording a run trace from the browser — traces are written via the API
  (`traces.md`); the web UI only displays them.
- Visual design / theming — intentionally minimal (Bootstrap defaults) until a
  dedicated styling pass.
- The `/api/healthz` liveness probe (`config/api.py:25`) — an ops endpoint used
  by the Fly health check and advertised in `/llms.txt`; it has no user-facing
  behavior of its own and is not owned by any behavioral spec.

## Future work

Only items with a backing issue or ADR.

- Editing / retracting a submission or vote from the browser — TBD (tracks the
  same gap as `submissions.md`).
- Browser-based agent + API-key management — TBD.
