---
status: accepted
date: 2026-07-12
---

# Store run-trace transcripts as a normalized step list

## Context and Problem Statement

A run trace records *that* an agent attempted a task and how it went (model,
harness, tools, outcome), but not *what it did* — the messages, reasoning, and
tool calls of the run. Without that, the catalog can show an outcome pill but
not the evidence behind it, which is most of the point of an eval harness. We
want to capture and display the transcript. The open question is how to
represent it, given that different harnesses (Claude Code ≈ Anthropic Messages;
Codex ≈ OpenAI items) emit different native shapes. This decision covers the
storage representation, the ingest boundary, and that transcripts are public; it
does not cover adjudication/scoring (see `traces.md` out-of-scope) or automated
secret/PII scanning (named as future work).

## Considered Options

- **Normalized step list in a JSONField.** One ordered array of steps, each a
  discriminated `kind` — `user` / `assistant` / `reasoning` / `tool_call` /
  `tool_result`. Agents submit it already-normalized; the API validates the
  shape.
- **Raw provider transcript blob.** Store each harness's native payload verbatim
  and adapt per provider at render time.
- **Relational `TraceStep` model.** A child table, one row per step, with typed
  columns and an ordering key.

## Decision Outcome

Chosen option: "Normalized step list in a JSONField", because the five kinds are
a superset both Anthropic- and OpenAI-shaped harnesses collapse onto, so one
viewer renders everything; and normalizing on the client keeps the ingest
boundary thin and the provider-specific mapping out of our server. The transcript
is **required and non-empty** — the catalog is an eval harness, so a trace exists
to carry evidence; an outcome without steps is not worth recording. Because the
transcript already names every tool call, the run's `tools` are **derived** from
it server-side rather than accepted as a separate body field.

### Consequences

- Good, because the transcript is one self-describing document read and rendered
  in order — no joins, no per-provider branches in the server.
- Good, because the ingest schema (`schemas.TranscriptStep`, a discriminated
  union) rejects malformed steps with `422`, so stored transcripts are
  well-formed by construction; the web viewer can trust the shape.
- Good, because it matches the existing `tools` JSONField precedent — no new
  table, one additive migration.
- Good, because `tools` is derived from the transcript's `tool_call` steps, not
  client-asserted, so the recorded tools can't disagree with the evidence; it is
  stored (not computed on read) so the lean list view keeps it without loading
  the transcript.
- Bad, because requiring a non-empty transcript raises the bar to report a run —
  a harness that can only produce a summary can't submit. We accept this: a
  summary with no evidence isn't the record this catalog is for.
- Bad, because transcripts are not queryable per-step (a relational model would
  be); we accept this — traces are read whole, not searched inside.
- Bad, because the client owns the mapping from its native format to our steps;
  a buggy harness can submit a faithful-looking-but-wrong transcript. Validation
  covers shape, not truthfulness — same trust model as the self-reported
  `outcome`.
- Transcripts are **public** when present. We bound ingest size with a step-count
  cap (`schemas.MAX_TRANSCRIPT_STEPS`) to protect the DB; content-level
  secret/PII scanning that rejects on submission is deliberately deferred
  (`traces.md` future work), so authors must not attach sensitive data yet.
- Locks in the step contract as the agent-facing shape: it appears in
  `openapi.json` (`TraceIn`, `TraceDetailOut`) and is enforced by
  `maeval/traces/tests/test_traces.py`.

## More Information

- Supersedes / superseded by: none
- Files: `maeval/traces/models.py`, `maeval/traces/schemas.py`,
  `maeval/traces/views.py`, `maeval/web/views.py`,
  `maeval/web/templates/web/trace_detail.html`
- Specs: `docs/requirements/traces.md`, `docs/requirements/web.md`
