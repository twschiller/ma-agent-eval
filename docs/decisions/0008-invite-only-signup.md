---
status: accepted
date: 2026-07-12
---

# Gate signup with a shared invite code from the environment

## Context and Problem Statement

We want to put the site live for a trial, but public, open signup on a brand-new
site is spam-bait: nothing yet throttles new-account creation (`django-axes`
covers auth *failures*, not registrations — see `accounts.md` future work). We
need a low-effort way to keep the trial to invited people that we can turn on for
production and leave off for local dev. This ADR covers *only* the human web
signup gate; it does not add per-invite tracking, revocation, or rate limiting.

## Considered Options

- Single shared invite code in an environment variable, checked by the signup form.
- A set of codes (env list), optionally single-use.
- A DB-backed `Invite` model (code, max-uses, expiry, created-by) managed in Django admin.
- Signed, expiring invite links (HMAC via Django `signing`), no DB.

## Decision Outcome

Chosen option: "single shared code in an environment variable", because it is the
least code that actually gates the trial, and it rotates with one
`fly secrets set`. The DB-backed model is the natural upgrade once we need
per-invite tracking or revocation.

### Consequences

- Good, because the gate ships without a migration, a model, or an admin flow.
- Good, because it composes with the existing config pattern: `SIGNUP_INVITE_CODE`
  reads from the environment like every other setting; empty means open signup, so
  dev and the test suite are unaffected by default.
- Bad, because a shared code has no per-person attribution and no revocation short
  of rotating it (which invalidates it for everyone).
- Locks in: the check lives in `SignupForm` and is compared with
  `hmac.compare_digest` (constant time); covered by `maeval/web/tests/test_web.py`.

## More Information

- PRs: TBD
- Files: `maeval/web/forms.py`, `config/settings/base.py`, `docs/requirements/web.md`
- Related: `accounts.md` (signup abuse controls, future work), ADR-0007 (auth lockout)
