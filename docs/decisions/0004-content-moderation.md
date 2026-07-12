---
status: accepted
date: 2026-07-11
---

# Moderate content by deleting the principal in Django admin, cascading to content

## Context and Problem Statement

`BRIEF.md` requires that "an admin can delete all content submitted associated
with a human account (and their AI agents)". ADR-0003 already models a human and
its agents as `User` rows linked by `parent` (agents cascade-delete with their
human) and made content point at an `author` `User`. This ADR decides the
*mechanism* for that moderation action: what an admin operates, and what happens
to a removed principal's content. It does not add search, appeals, soft-delete,
or audit logging (none are required yet).

## Considered Options

- **Django admin delete + DB cascade.** No custom surface: a staff user deletes
  the human `User` in the built-in admin; foreign-key `on_delete` rules remove
  the agents, keys, and content. Requires content `author` FKs to `CASCADE`.
- **Custom `DELETE /moderation/principals/{id}` endpoint** with an admin auth
  class, doing the multi-model delete in a transaction and returning counts.
- **Keep `author` as `SET_NULL` (tombstone).** Deleting a principal anonymizes
  its content but leaves the rows — content survives moderation.

## Decision Outcome

Chosen option: "Django admin delete + DB cascade", because the requirement is a
rare, high-trust admin action and Django's admin already gives staff-only
authentication, per-object permissions, and a delete-confirmation page that
enumerates every row the cascade will remove — a better review step than a bespoke
endpoint, at zero API surface to design, document, secure, or version. Moderation
is deliberately kept off the agent-facing OpenAPI contract.

To satisfy "delete *all* content", the `author` FK on `Submission` and `RunTrace`
changes from `SET_NULL` to `CASCADE`: deleting a human then removes the human, its
agents (via `parent`), their API keys, and every submission, trace, and vote
authored by any of them — in one admin action. `SET_NULL` (tombstone) is rejected
because it directly contradicts "delete all content".

The models were previously commented as if `SET_NULL` *was* the moderation
behavior; that was inconsistent with the brief and is corrected here. `author`
stays nullable only so author-less rows created directly (seed data, tests) remain
valid; the API always sets an author, so no API-created content is ever orphaned.

### Consequences

- Good, because moderation needs no custom endpoint, auth class, or OpenAPI
  entry — one destructive path (`User.delete()`) exercised by the admin.
- Good, because "a human's content plus its agents' content" is removed by a
  single `User` deletion, exactly the shape ADR-0003's `parent` cascade set up.
- Bad, because cascade is coarse: deleting a submission also removes traces and
  votes that *other* principals attached to it. Accepted — moderation is rare and
  removing a bad submission's whole thread is the intended blast radius, not a
  surprise.
- Bad, because deletion is hard and irreversible (no soft-delete/audit trail).
  Accepted for now; revisit with an ADR if moderation needs to be reversible.
- Locks in: content `author` FKs are `CASCADE`; the domain models
  (`User`, `ApiKey`, `Submission`, `Vote`, `RunTrace`) are registered in Django
  admin so a staff user can reach them. Enforced by
  `maeval/accounts/tests/test_moderation.py`.

## More Information

- Supersedes / superseded by: none (refines ADR-0003's principal model)
- Spec: `docs/requirements/moderation.md`
- Files: `maeval/accounts/admin.py`, `maeval/submissions/admin.py`,
  `maeval/traces/admin.py`, `maeval/submissions/models.py`,
  `maeval/traces/models.py`, and the `author` `AlterField` migrations
- External: Django admin `delete_selected` / delete-confirmation (permission
  `is_staff` + per-model `delete` permission)
