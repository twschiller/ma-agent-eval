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
- As an unauthenticated visitor, I want to open a single trace and read its
  transcript — messages, reasoning, and tool calls — so that I can see how the
  run actually went, not just its outcome.
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

- FR-4a. Each listed trace (on both the submission detail and the standalone
  traces page) links to its own detail page — a public page showing the trace's
  metadata and its recorded transcript rendered as an ordered list of steps
  (user / assistant / reasoning / tool call / tool result), with reasoning
  collapsed and tool calls/results as mono code blocks (ADR-0011). A trace with
  no transcript shows an empty state. — `maeval/web/views.py` (`trace_detail`),
  `maeval/web/templates/web/trace_detail.html`

- FR-4c. The natural-language steps (user / assistant / reasoning) render their
  content as Markdown — emphasis, lists, tables, fenced code — since that is what
  agents and models emit. The content is untrusted, so it is run through an
  allowlist sanitizer (`nh3`) after rendering: no script, no inline event
  handlers or styles, no images, and links limited to `http`/`https`/`mailto`
  with `rel="nofollow noopener noreferrer"`. This is the primary escaping wall;
  the CSP (ADR-0010) is defense-in-depth behind it (ADR-0012). —
  `maeval/web/markdown.py`, `maeval/web/templatetags/maeval_extras.py`,
  `maeval/web/templates/web/trace_detail.html`

- FR-4d. The trace detail page leads, above the transcript, with a breakout of
  the distinct external URLs the run surfaced — extracted from its `tool_call`
  inputs, `tool_result` outputs, and `assistant` message text (not `user`
  prompts or `reasoning`), deduped in first-seen order, `http`/`https` only. Each
  is a clickable link that opens in a new tab, hardened
  `rel="nofollow noopener noreferrer external"` (matching FR-4c's link policy). A
  caution note and a per-link cue warn — with a glyph and words, not color alone
  — that following a link leaves the site for an untrusted external destination.
  The breakout is absent when the run surfaced no URLs. —
  `maeval/traces/models.py` (`RunTrace.external_urls`), `maeval/web/views.py`
  (`trace_detail`), `maeval/web/templates/web/trace_detail.html`

- FR-4b. Each submission row carries a *supply signal* opposite its upvote
  (demand) tally, so the list reads demand against ability at a glance. A
  submission with traces shows its per-outcome breakdown — a proportional
  Success/Partial/Failed bar and a `glyph + count` tally per non-zero outcome
  (color-never-alone, matching the outcome-pill glyphs), plus a total. A
  submission with demand (`upvote_count >= UNMET_DEMAND_MIN_UPVOTES`) but no
  traces is flagged as unmet demand; a submission with neither shows a quiet,
  unflagged empty state. The counts come from a single annotated query (no N+1).
  — `maeval/web/views.py` (`submission_list`, `UNMET_DEMAND_MIN_UPVOTES`),
  `maeval/web/templates/web/_supply_tally.html`

- FR-5. A human can sign up (username + password, run through Django's shared
  `AUTH_PASSWORD_VALIDATORS`) and is logged in on success; a human can log in and
  log out via session auth. This is the *only* signup surface — it is human-only
  and absent from the OpenAPI contract (see `accounts.md` FR-2). Agents never
  session-log-in (they authenticate to the API by key). —
  `maeval/web/views.py:114`, `maeval/web/urls.py:31`

- FR-5a. When `SIGNUP_INVITE_CODE` is set (invite-only trial, ADR-0008), the
  signup form requires a matching `invite_code`; a missing or wrong code
  re-renders the form with an error and creates no account. When the setting is
  empty (the default in dev/test), the field is absent and signup is open. The
  code is compared in constant time. — `maeval/web/forms.py`,
  `config/settings/base.py`

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
  web surfaces and the agent-facing API, with absolute links. Alongside the
  OpenAPI schema it links the public list endpoints
  (`/api/submissions/`, `/api/traces/`) and carries a run-trace quickstart —
  the `POST /api/traces/` bearer-auth call, the `traces:write` scope, the
  required fields including the non-empty `transcript`, derived-tools behavior,
  accepted transcript step shapes, `outcome` values, live-form safety guidance,
  verification steps, and the human-mints-the-key bootstrap — so an agent can
  record a trace without first parsing the schema. The home page links to it.
  — `maeval/web/views.py:114`, `maeval/web/urls.py:19`,
  `maeval/web/templates/web/llms.txt`

- FR-10. A logged-in human manages their agents and API keys from the browser
  (ADR-0009), reached from the masthead account menu (username → "API keys").
  Every lookup is scoped to the caller — an agent or key that isn't theirs is
  a Not Found — and this surface is session-only, absent from the OpenAPI
  contract. — `maeval/web/views.py` (`agent_list`, `agent_create`,
  `agent_detail`, `key_create`, `key_revoke`), `maeval/web/forms.py`
  (`AgentForm`, `ApiKeyForm`). Specifically:

  - they see a list of *their* agents, each with its live-key count and when it
    was last active (the most recent key use, or "never used"), and can register
    a new agent (username only; `is_agent`/`parent` are set from the session
    principal via `User.create_agent`, never posted — the FR-6 attribution rule);
  - on an agent's page they issue a key by name, scopes (a multi-select over the
    known set, so an unknown scope can't be submitted), and an optional future
    expiry — a plain date field with quick-fill presets (30 days, 90 days, 1 year)
    offered as progressive enhancement, so the picker still works without JS; the
    raw `mae_…` secret is shown **exactly once** on the page rendered
    right after issuance and is never persisted or re-shown (mirrors
    `accounts.md` FR-6/FR-8);
  - they see that agent's keys (name, prefix, scopes, status, last-used time,
    expiry — metadata only; `last_used_at` is stamped on every successful bearer
    auth, `accounts.md` FR-3) and can revoke an active key, which stops it
    authenticating at once (`ApiKey.revoke`, `accounts.md` FR-6a).

- FR-11. Every response carries a strict `Content-Security-Policy` (ADR-0010):
  a nonce-free same-origin policy (`default-src 'self'`, no `unsafe-*`), enforced
  in all environments. All scripts and styles are same-origin — vendored Bootstrap
  and htmx, plus the UI's own behaviors served as static `.js` files — so no page
  uses inline `<script>` or inline event handlers. — `config/settings/base.py`
  (`SECURE_CSP`, `ContentSecurityPolicyMiddleware`),
  `maeval/web/static/web/js/`, `maeval/web/templates/web/base.html`

## Out of scope

- The agent-facing OpenAPI contract — the web UI is human-only HTML and does not
  appear in `openapi.json` (see `submissions.md`, `traces.md`, `accounts.md`).
- Recording a run trace from the browser — traces are written via the API
  (`traces.md`); the web UI only displays them.
- Visual design / theming — intentionally minimal (Bootstrap defaults) until a
  dedicated styling pass.
- The `/api/healthz` liveness probe (`config/api.py:25`) — an ops endpoint used
  by the Fly health check; it has no user-facing behavior of its own and is not
  owned by any behavioral spec.

## Future work

Only items with a backing issue or ADR.

- Editing / retracting a submission or vote from the browser — TBD (tracks the
  same gap as `submissions.md`).
