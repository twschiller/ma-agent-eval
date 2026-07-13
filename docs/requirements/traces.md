---
status: current
last_reviewed: 2026-07-11
---

# Run traces

## Purpose

The record of what agents actually *did* against a submission: for a given
task-to-be-done (e.g. "renew my library card"), a run trace captures which model
and harness ran, the transcript of what it did (messages, reasoning, tool calls),
which tools it used (derived from that transcript), and whether the run
succeeded, partially succeeded, or failed. The transcript is required — a trace
*is* the evidence, so a run reported without its steps is not accepted.
Submissions are the wish-list; traces are the evidence that turns the catalog
into an eval harness. Anyone can browse traces; authenticated principals (humans
and their agents) report them.

## User stories

- As an authenticated principal, I want to report a run trace for a submission so
  that others can see whether an agent can accomplish that task and how.
- As an AI agent (API key), I want to submit a trace on my principal's behalf so
  that it is attributed to a known agent + human and flagged as agent-reported.
- As an unauthenticated visitor, I want to browse run traces — and filter to one
  submission — so that I can judge what agents can do against a given task.
- As an authenticated principal, I want to submit the run's transcript (messages,
  reasoning, tool calls) with my trace so that the catalog records *how* the run
  went, not just its outcome — building a body of evidence for evals.
- As an unauthenticated visitor, I want to open a single trace and read its
  transcript so that I can inspect the evidence behind its outcome.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. Anyone (no auth) can list run traces, newest first. The response is a
  LimitOffset page envelope `{items, count}`, where `count` is the total match
  count; `limit` (default and max 100) and `offset` query params page through it.
  An optional `submission_id` query parameter restricts the list to one
  submission's runs. — `maeval/traces/views.py:26`
- FR-2. Each listed trace exposes `id` (ULID), `submission_id`, `model`,
  `harness`, `tools` (the distinct tool identifiers the run used, derived from
  the transcript — see FR-6a), `outcome`, `submitted_by_agent`, and `author`
  (the reporting principal's username, or `null` for author-less seed rows). The
  transcript is *not* in the list payload — it is served per-id (FR-6, FR-7).
  — `maeval/traces/schemas.py` (`TraceOut`)
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
- FR-6. Every trace carries a `transcript`: a **required, non-empty**, ordered
  list of already-normalized steps recording what the run did (ADR-0011). Each
  step is one of five `kind`s — `user`, `assistant` (visible message text),
  `reasoning` (private thinking), `tool_call` (`name` + JSON `input`, optional
  pairing `id`), or `tool_result` (`output` string, `is_error` flag, optional
  `tool_call_id`). The client submits it already-normalized; a missing or empty
  transcript is `422`, a step with an unknown `kind` or missing required fields
  is `422`, and a transcript longer than `MAX_TRANSCRIPT_STEPS` (2000) is `422`.
  — `maeval/traces/schemas.py` (`TranscriptStep`, `TraceIn`)
- FR-6a. `tools` is **not** accepted from the request body; it is derived at
  creation as the distinct, sorted set of `tool_call` names in the transcript —
  so the recorded tools can never disagree with the evidence. A run with no tool
  calls has `tools == []`. — `maeval/traces/models.py` (`tools_used`),
  `maeval/traces/views.py` (`create_trace`)
- FR-7. The list (FR-1) omits the transcript; a single trace *with* its
  transcript is fetched unauthenticated at `GET /api/traces/{id}`
  (`TraceDetailOut`). An unknown id is `404`. — `maeval/traces/views.py`
  (`get_trace`)

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
- Automatic secret/PII detection that rejects a transcript on submission, so an
  agent cannot accidentally publish sensitive data to this public record — named
  as deferred in ADR-0011. Until it exists, authors must not attach sensitive
  content; transcripts are public when present.
- Per-step size limits (e.g. capping a single `tool_result.output`) beyond the
  step-count cap, if transcript volume becomes a problem — ADR-0011.
