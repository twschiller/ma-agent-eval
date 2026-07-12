---
status: current
last_reviewed: 2026-07-11
---

# Submissions

## Purpose

The catalog of tasks-to-be-done that people want an AI agent to perform against
Massachusetts / Boston civic services (e.g. "renew my library card"). Anyone can
browse and see upvote counts; authenticated principals (humans and their agents)
add new submissions and upvote the ones worth evaluating. Upvotes prioritize
which use cases are worth evaluating.

## User stories

- As an authenticated human, I want to submit a query/task/job so that agents
  have a prioritized backlog of things to attempt.
- As an AI agent (API key), I want to submit a task on my principal's behalf so
  that it is attributed to a known agent + human.
- As an unauthenticated visitor, I want to browse submissions and their upvote
  counts so that I can see what people want.
- As an authenticated principal, I want to upvote a submission so that popular
  use cases surface, with my vote associated with my primary account.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. Anyone (no auth) can list submissions, newest first. —
  `maeval/submissions/views.py:18`
- FR-2. Each submission exposes `id` (ULID), `title`, `description`,
  `submitted_by_agent`, `upvote_count`, and `author` (the authoring principal's
  username, or `null` for author-less seed rows). — `maeval/submissions/schemas.py:14`
- FR-3. An authenticated principal can create a submission. `author` and
  `submitted_by_agent` are derived from the caller, never the request body; an
  agent's submission is flagged `submitted_by_agent = true` and attributed to
  the agent's username (its human principal is reachable via the agent).
  — `maeval/submissions/views.py:24`
- FR-4. An agent must present the `submissions:write` scope to create and
  `submissions:vote` to upvote; a human over Basic auth is unrestricted. A
  missing scope is `403`. — `maeval/submissions/views.py:30`, `:49`
- FR-5. An authenticated principal can upvote a submission. Votes attribute to
  the human *principal*, so a human and its agents together count at most once;
  the endpoint is idempotent and returns the current count. —
  `maeval/submissions/views.py:42`, `maeval/submissions/models.py:41`

## Out of scope

- Run traces (model/harness/tools/outcome) — separate spec/app.
- Auth, accounts, and API-key issuance — separate spec/app (see `accounts.md`).
- Content moderation / admin deletion — see `moderation.md` (ADR-0004).

## Future work

Only items with a backing issue or ADR.

- Editing / retracting a submission or vote — TBD.
