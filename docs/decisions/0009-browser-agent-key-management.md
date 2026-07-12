---
status: accepted
date: 2026-07-12
---

# Manage agents and API keys from the human web UI

## Context and Problem Statement

ADR-0006 shipped the human web UI but deliberately left agent registration and
API-key issuance API-only (`web.md` "out of scope"; `accounts.md` future work).
In practice a human cannot be expected to hand-craft HTTP Basic requests with
`curl` just to mint a key for their agent — the one credential they need to do
anything useful. This ADR adds a browser self-serve surface for the agent/key
lifecycle. It does **not** change the API contract (still the agent-facing
surface, unchanged) and does not add new API endpoints.

## Considered Options

- **Keep it API-only, document `curl`.** Zero new UI, but the primary onboarding
  step stays behind a terminal — a wall for the non-technical humans the catalog
  is for.
- **Browser UI in `maeval/web`, reusing the model helpers.** Session-authed views
  for listing/creating agents and issuing/listing/revoking keys, calling
  `User.create_agent` / `ApiKey.issue` / `ApiKey.revoke` — the same helpers the
  API calls, so behavior can't drift.
- **Build a JSON UI against the existing API.** A client that calls `/api/` from
  the browser; re-introduces the SPA/CSRF/token plumbing ADR-0006 rejected, for
  five pages.

## Decision Outcome

Chosen option: "browser UI in `maeval/web`, reusing the model helpers", because
it closes the onboarding gap on the same server-rendered, session-authed stack as
the rest of the human UI (ADR-0006) and shares the identity logic with the API
rather than reimplementing it. A human reaches it from an **account dropdown** in
the masthead (username → "API keys" / "Log out"). The raw key is revealed exactly
once, on the page rendered right after issuance — never persisted, never
re-derivable, mirroring the API's one-time return.

Revocation needed a shared helper, so `ApiKey.revoke()` is added (idempotent;
`resolve` stays the single place that decides whether a key is live). Listing and
revocation now exist in the **web** surface; equivalent **API** endpoints remain
future work (`accounts.md`) — the web UI reads the model directly.

Ownership is enforced on every lookup: agents are fetched by `parent=request.user`
and keys by `agent__parent=request.user`, so a human can only ever see or revoke
their own agents' keys (404 otherwise), the same rule as `issue_key`.

### Consequences

- Good, because a human can go from signup to a working API key without leaving
  the browser or touching the API.
- Good, because web and API share `User.create_agent` / `ApiKey.issue` /
  `ApiKey.revoke`; there is one issuance and one revocation path, tested on both.
- Good, because the raw secret still appears exactly once and only a hash is
  stored — the ADR-0003 invariant is unchanged.
- Bad, because key *listing/revocation* now live in the web UI before the matching
  API endpoints exist, a temporary asymmetry between the two surfaces.
- Reverses the "browser-based agent registration / API-key issuance — out of
  scope" note in ADR-0006 / `web.md`; those are updated in the same PR.
- Locks in: the account menu is the only interactive dropdown; agent/key views
  are session-only and absent from the OpenAPI contract (like the rest of `web`).

## More Information

- Supersedes / superseded by: refines ADR-0006 (adds the deferred management UI);
  builds on ADR-0003 (identity + key model)
- Spec: `docs/requirements/web.md` (FR-10), `docs/requirements/accounts.md`
- Files: `maeval/web/views.py`, `maeval/web/forms.py`, `maeval/web/urls.py`,
  `maeval/web/templates/web/{agent_list,agent_form,agent_detail,key_form,key_created}.html`,
  `maeval/web/templates/web/base.html`, `maeval/accounts/models.py`
  (`ApiKey.revoke`), `maeval/web/static/web/css/maeval.css`, `DESIGN.md`
