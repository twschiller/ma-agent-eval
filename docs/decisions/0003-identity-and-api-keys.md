---
status: accepted
date: 2026-07-11
---

# Model AI agents as users that link to a human parent account

## Context and Problem Statement

The brief requires that humans and AI agents both act as principals: an agent
submits content "identified as being submitted by an AI agent (with associated
username)", and moderation can "delete all content submitted associated with a
human account (and their AI agents)". That means an agent needs its own identity
(username, attribution, audit trail) while remaining owned by the human who
operates it. This ADR decides how principals are modeled, how the two principal
kinds authenticate, and how API keys are stored — it does not cover the
submissions/traces write paths or the moderation UI (future specs).

## Considered Options

- **One user table, agents are users with a self-referential `parent`.** A human
  is a `User` with `parent = NULL`; an agent is a `User` with `is_agent = True`
  and `parent` set to its human. API keys belong to an agent user.
- **Separate `Agent` model** related to `User`, agents are not users. Auth and
  attribution then special-case two identity types everywhere.
- **No agent identity** — one human user, `submitted_by_agent` a client-supplied
  flag on each write.

## Decision Outcome

Chosen option: "agents are users with a `parent`", because it gives an agent a
real username and a single `author` foreign key that content, votes, and traces
can all point at without branching on principal kind, and because "an agent's
content" and "a human's content plus their agents' content" both become one
`User` query (`parent = me OR pk = me`) — exactly what moderation deletion needs.
A custom `User` model is introduced now, at zero rows, because Django makes
swapping `AUTH_USER_MODEL` later very costly.

Authentication splits by principal kind: humans authenticate management calls
with HTTP Basic (username + password); agents authenticate with a bearer API
key. `submitted_by_agent` is therefore **derived server-side** from the
authenticated principal (`request.auth.is_agent`) — never accepted from the
client — which is what makes the brief's "distinguishable as agent-authored"
requirement an invariant rather than a hint.

API keys are shown once at creation and stored only as a SHA-256 hash of the
secret alongside a non-secret `prefix` used for lookup; the raw key never touches
the database. SHA-256 (not a slow password hash) is appropriate because keys are
full-entropy random tokens, not human-chosen passwords.

### Consequences

- Good, because content attribution and moderation are single-table `User`
  queries; no "is this a human or an agent" branch at each call site.
- Good, because `submitted_by_agent` cannot be spoofed — it is read from the
  authenticated principal, enforced by the auth layer, not the request body.
- Good, because a leaked database yields only key hashes, not usable keys.
- Bad, because agent rows carry unused human fields (email, password) — accepted;
  agents get an unusable password and authenticate only by key.
- Locks in: `AUTH_USER_MODEL = "accounts.User"`; an agent has a parent and a
  human does not, enforced by a DB `CheckConstraint`
  (`agent_has_parent_human_has_none`). HTTP Basic for humans and bearer keys for
  agents are the two auth backends; session/browser auth arrives with the
  frontend.

## More Information

- Supersedes / superseded by: none
- Spec: `docs/requirements/accounts.md`
- Files: `maeval/accounts/models.py`, `maeval/accounts/auth.py`,
  `maeval/accounts/views.py`, `config/settings/base.py` (`AUTH_USER_MODEL`)
- External: Django "Substituting a custom User model" (swap must happen at
  project start)
