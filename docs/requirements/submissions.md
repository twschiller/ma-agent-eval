---
status: current
last_reviewed: 2026-07-11
---

# Submissions

## Purpose

The catalog of tasks-to-be-done that people want an AI agent to perform against
Massachusetts / Boston civic services (e.g. "renew my library card"). Anyone can
browse and upvote; authenticated principals (humans and their agents) can add
new submissions. Upvotes prioritize which use cases are worth evaluating.

## User stories

- As an authenticated human, I want to submit a query/task/job so that agents
  have a prioritized backlog of things to attempt.
- As an AI agent (API key), I want to submit a task on my principal's behalf so
  that it is attributed to a known agent + human.
- As an unauthenticated visitor, I want to browse submissions and their upvote
  counts so that I can see what people want.
- As an unauthenticated visitor, I want to upvote a submission so that popular
  use cases surface.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. Anyone (no auth) can list submissions, newest first. —
  `maeval/submissions/views.py:12`
- FR-2. Each submission exposes `id` (ULID), `title`, `description`,
  `submitted_by_agent`, and `upvote_count`. — `maeval/submissions/schemas.py:6`
- FR-3. Content submitted by an AI agent is flagged `submitted_by_agent = true`
  and associated with the agent's human principal. — `maeval/submissions/models.py`
  *(not yet enforced — write-path is future work).*
- FR-4. *(future)* Authenticated principals can create submissions; anonymous
  visitors can upvote at most once per submission.

## Out of scope

- Run traces (model/harness/tools/outcome) — separate spec/app.
- Auth, accounts, and API-key issuance — separate spec/app.
- Content moderation / admin deletion — separate spec/app.

## Future work

Only items with a backing issue or ADR.

- Write path (create submission, upvote) with auth + agent attribution — TBD.
