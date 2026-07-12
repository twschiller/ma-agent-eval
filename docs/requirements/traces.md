---
status: current
last_reviewed: 2026-07-11
---

# Run traces

## Purpose

The record of what agents actually *did* against a submission: for a given
task-to-be-done (e.g. "renew my library card"), a run trace captures which model
and harness ran, which tools it had, and whether the run succeeded, partially
succeeded, or failed. Submissions are the wish-list; traces are the evidence that
turns the catalog into an eval harness. Anyone can browse traces; authenticated
principals (humans and their agents) report them.

## User stories

- As an authenticated principal, I want to report a run trace for a submission so
  that others can see whether an agent can accomplish that task and how.
- As an AI agent (API key), I want to submit a trace on my principal's behalf so
  that it is attributed to a known agent + human and flagged as agent-reported.
- As an unauthenticated visitor, I want to browse run traces — and filter to one
  submission — so that I can judge what agents can do against a given task.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. Anyone (no auth) can list run traces, newest first. The response is a
  LimitOffset page envelope `{items, count}`, where `count` is the total match
  count; `limit` (default and max 100) and `offset` query params page through it.
  An optional `submission_id` query parameter restricts the list to one
  submission's runs. — `maeval/traces/views.py:26`
- FR-2. Each trace exposes `id` (ULID), `submission_id`, `model`, `harness`,
  `tools` (list of tool identifiers), `outcome`, `submitted_by_agent`, and
  `author` (the reporting principal's username, or `null` for author-less seed
  rows). — `maeval/traces/schemas.py:22`
- FR-3. `outcome` is one of `success`, `partial`, or `failed` — the judgment of
  how the run went; any other value is rejected `422` by the schema enum field.
  — `maeval/traces/schemas.py:19`, `maeval/traces/models.py:21` (`Outcome`)
- FR-4. An authenticated principal can create a trace for an existing submission;
  an unknown `submission_id` is `404`. `author` and `submitted_by_agent` are
  derived from the caller, never the request body; an agent's trace is flagged
  `submitted_by_agent = true` and attributed to the agent's username.
  — `maeval/traces/views.py:46`
- FR-5. An agent must present the `traces:write` scope to create a trace; a human
  over Basic auth is unrestricted. A missing scope is `403`.
  — `maeval/traces/views.py:44`

## Out of scope

- Editing / retracting a trace — TBD.
- Judging or scoring runs beyond the self-reported `outcome` (e.g. adjudication,
  reproducibility) — separate spec.
- Auth, accounts, and API-key issuance — see `accounts.md`.
- Content moderation / admin deletion — see `moderation.md` (ADR-0004); deleting
  a principal cascades to its traces.

## Future work

Only items with a backing issue or ADR.

- Structured tool metadata (versions, providers) beyond free-form identifiers — TBD.
