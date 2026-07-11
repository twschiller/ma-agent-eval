---
status: accepted
date: 2026-07-11
---

# Record architecture decisions in ADRs

## Context and Problem Statement

We need a durable, low-friction place to capture architecturally significant
decisions — the ones that constrain the shape of the code or lock in an
invariant — so the rationale survives turnover and is citable in review.

## Considered Options

- Architecture Decision Records (one Markdown file per decision)
- A single long DECISIONS.md
- Tribal knowledge / commit messages / PR descriptions only

## Decision Outcome

Chosen option: "Architecture Decision Records", because per-file records sort
lexically, are cheap to diff and cite (`ADR-0007`), and keep each decision's
rationale in one reviewable unit.

### Consequences

- Good, because every load-bearing decision has one canonical rationale store.
- Good, because ADRs are append-only — superseded ones are marked, never
  deleted, so history stays legible.
- Bad, because there is a small write tax on each significant decision.
- ADRs live in `docs/decisions/NNNN-slug.md` using MADR-minimal format (this
  file's structure). `docs/decisions/README.md` indexes them.

## More Information

- Format: <https://adr.github.io/madr/>
