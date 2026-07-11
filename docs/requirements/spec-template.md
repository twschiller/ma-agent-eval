---
status: current
last_reviewed: YYYY-MM-DD
---

# {Area name}

One spec per behavioral domain (auth, submissions, billing), NOT per file. The
spec describes observable behavior; how the code is laid out belongs in
AGENTS.md. A spec that disagrees with the code is a bug — fix both in the same
PR.

## Purpose

One paragraph: what this area exists to do, in product terms.

## User stories

- As a {human role}, I want {capability} so that {outcome}.
- As an {AI agent / API client}, I want {capability} so that {outcome}.

## Behavior

Numbered, verifiable requirements. Cite the code that backs each one by
`path:line` and quantify where you can ("≤ 300ms p95", not "fast").

- FR-1. The system {observable behavior}. — `app/foo/views.py:42`
- FR-2. {…}

## Out of scope

- {Explicit non-goal}, handled instead by {pointer elsewhere or "nobody yet"}.

## Future work

Only items with a backing issue or ADR.

- {Planned change} — #NNN / ADR-NNNN
