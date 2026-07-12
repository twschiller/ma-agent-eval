---
status: accepted
date: 2026-07-12
---

# Rate-limit authentication with django-axes lockout

## Context and Problem Statement

Both authentication paths — the web login form and the API's HTTP Basic path
(ADR-0003) — accepted unlimited credential attempts, leaving human accounts and
the Django admin open to online password brute-force and credential stuffing
(OWASP A07). API-key bearer secrets are 256-bit and not brute-forceable, so this
decision covers only the *password* paths. Signup abuse (mass account creation)
is out of scope here.

## Considered Options

- django-axes (DB-backed failed-attempt tracking + lockout middleware/backend)
- A hand-rolled attempt counter (cache/DB) wired into the auth layer
- Edge rate limiting only (Fly.io / proxy)

## Decision Outcome

Chosen option: "django-axes", because it hooks Django's `authenticate()` once and
so covers *both* the login form and the Ninja HTTP Basic path with no per-view
code, and it ships the attempt store, lockout response, and cooloff we would
otherwise hand-roll. Edge rate limiting is coarse (per-IP, no username notion)
and Fly scale-to-zero makes it an unreliable sole control; it can layer on later.

Lockout is keyed on the `(username, IP)` pair, not IP alone, so a shared
NAT/office IP can't lock out unrelated users while a single account is still
protected. Behind Fly's proxy the client IP is read from `X-Forwarded-For`
(same proxy that terminates TLS). Thresholds are env-tunable
(`DJANGO_AXES_FAILURE_LIMIT`, `DJANGO_AXES_COOLOFF_MINUTES`).

### Consequences

- Good, because one integration protects every password path, present and future,
  that routes through `authenticate()`.
- Good, because a successful login before the limit resets the tally
  (`AXES_RESET_ON_SUCCESS`), so honest users rarely hit a lock.
- Bad, because it adds a second entry to `AUTHENTICATION_BACKENDS`, so
  `login()` calls must name the backend explicitly (done in web signup).
- Bad, because a locked-out API caller gets a bare 401 (Django swallows the
  backend's `PermissionDenied` into "auth failed") rather than a 429; the web
  form does return the configured 429.
- Locks in a `DATA`-store dependency (axes' `AccessAttempt` tables, applied by
  `migrate`). Tests disable axes by default and re-enable it per-case with
  `@override_settings(AXES_ENABLED=True)` (`maeval/accounts/tests/test_lockout.py`).

## More Information

- Extends: ADR-0003 (identity and API keys)
- Files: `config/settings/base.py`, `maeval/web/views.py`,
  `maeval/accounts/tests/test_lockout.py`
- External: <https://django-axes.readthedocs.io/>
