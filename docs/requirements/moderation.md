---
status: current
last_reviewed: 2026-07-11
---

# Moderation

## Purpose

Give a trusted operator a way to remove abusive or unwanted content and the
account behind it. The brief scopes this to one capability: an admin can delete
all content submitted by a human account and its AI agents. It runs through the
Django admin, not the public/agent API — moderation is a rare, high-trust action,
deliberately kept off the agent-facing OpenAPI contract (ADR-0004).

## User stories

- As a staff admin, I want to delete a human principal so that the human, its
  agents, their API keys, and all of their submissions, traces, and votes are
  removed together — in one reviewed action.

## Behavior

Numbered, verifiable requirements. Cite backing code by `path:line`.

- FR-1. The domain models are registered in the Django admin, so a staff user
  can find and delete a principal. — `maeval/accounts/admin.py`,
  `maeval/submissions/admin.py`, `maeval/traces/admin.py`
- FR-2. Only staff (`is_staff`) reach the admin, and deleting a model requires
  its Django `delete` permission. Authorization is Django's, not custom.
- FR-3. Deleting a human principal cascades to its agents (via `parent`) and to
  every agent's API keys. — `maeval/accounts/models.py:62`,
  `maeval/accounts/tests/test_moderation.py`
- FR-4. Deleting a principal deletes all content authored by it or its agents —
  submissions, run traces, and votes — rather than tombstoning it; content
  `author` foreign keys `CASCADE`. — `maeval/submissions/models.py`,
  `maeval/traces/models.py`, `maeval/accounts/tests/test_moderation.py`
- FR-5. Deletion is scoped to the targeted principal: other principals' accounts
  and content are untouched. —
  `maeval/accounts/tests/test_moderation.py::test_moderation_is_scoped_to_one_principal`
- FR-6. Because a submission owns its traces and votes (`on_delete=CASCADE`),
  deleting one principal's submission also removes traces and votes that other
  principals attached to it — an accepted, intended blast radius (ADR-0004).

## Out of scope

- A public or agent-facing moderation endpoint — moderation is admin-only and
  absent from the OpenAPI contract (ADR-0004).
- Soft-delete, reversal, appeals, and audit logging — deletion is hard and
  irreversible for now; revisit with an ADR if reversibility is needed.
- Per-item takedown (delete one submission but keep the account) — an admin can
  still do this ad hoc in the admin, but it is not a specified capability here.

## Future work

Only items with a backing issue or ADR.

- Reversible moderation / audit trail — TBD (needs an ADR).
