---
status: accepted
date: 2026-07-12
---

# Enforce a strict same-origin CSP with Django's built-in support

## Context and Problem Statement

The site renders user- and agent-submitted content (submissions, run traces) and
had no Content-Security-Policy — Django's autoescaping was the only wall against
injected script, and `connect-src`/`img-src` were unrestricted, so a single
escaping slip (a stray `|safe`, a future markdown/rich-text feature, an XSS bug)
could execute script or exfiltrate data. We want a strict CSP as defense-in-depth
behind autoescaping. This decision covers the web UI's response headers only; it
does not change how content is stored, escaped, or moderated (ADR-0004).

The surface is favorable: every asset is same-origin. Bootstrap CSS/JS, htmx, and
fonts are vendored and served by WhiteNoise (`web/base.html`), so no third-party
origins need allowlisting. The only obstacles to a nonce-free `'self'` policy are
three inline `<script>` blocks (`base.html`, `key_created.html`, `key_form.html`)
and one inline `onsubmit` handler (`agent_detail.html`).

## Considered Options

- Django 6's built-in CSP (`SECURE_CSP` + `ContentSecurityPolicyMiddleware`),
  nonce-free `'self'`, with the inline scripts refactored out to static files.
- Django's built-in CSP with per-request nonces, keeping scripts inline.
- The third-party `django-csp` package.
- No CSP; rely on autoescaping alone.

## Decision Outcome

Chosen option: "Django's built-in CSP, nonce-free `'self'`", because the runtime
already ships it (Django 6.0) so it needs no dependency, and because our assets
are all same-origin the strictest policy is also the simplest — no `unsafe-*`, no
per-request nonce state to plumb through templates. Since none of the four inline
sites interpolate untrusted data (the CSRF token rides on `hx-headers`, not in a
script), moving them to static `.js` files is mechanical and lets `script-src`
stay `'self'`. Nonces were rejected as carrying per-request machinery we don't
need; `django-csp` as a dependency for something now native; "no CSP" as the
status quo this ADR exists to fix.

The policy is defined once in `config/settings/base.py` and enforced in **every**
environment (dev, test, prod) so the test suite is the ratchet: a reintroduced
inline script fails the CSP assertion locally, not in production.

```text
default-src 'self'; script-src 'self'; style-src 'self';
img-src 'self' data:; font-src 'self'; connect-src 'self';
form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'
```

`frame-ancestors 'none'` layers over the existing `X-Frame-Options` (clickjacking
middleware); `connect-src 'self'` and the restricted `img-src` are the anti-
exfiltration half — the payoff once escaping fails. `SECURE_CSP_REPORT_ONLY` is
the documented lever for the first production soak or any future loosening
investigation: point it at the same dict, unset `SECURE_CSP`, watch, then flip
back.

### Consequences

- Good, because the enforced policy carries no `'unsafe-inline'`/`'unsafe-eval'`,
  so an injected `<script>` or inline handler is blocked outright.
- Good, because no runtime dependency and no nonce plumbing — the header is a
  static settings dict.
- Bad, because inline scripts and inline event handlers are now a build-time
  error surface: new UI JS must live in a static file (or the page must opt into
  a nonce), which is stricter than "drop a `<script>` in the template."
- Locks in: htmx stays on its declarative attributes (`hx-get`/`hx-post`/…),
  which need no `'unsafe-eval'`; adopting `hx-on`/`js:` expressions later would
  force a nonce or a hash. A test in `maeval/web` asserts the header is present
  and free of `unsafe-`; a semgrep rule forbidding inline `<script>`/`on*=` in
  `web/` templates can ratchet it further (follow-up).

## More Information

- Extends: ADR-0006 (server-rendered web UI)
- Files: `config/settings/base.py`,
  `maeval/web/static/web/js/{menu,copy,expiry-presets}.js`,
  `maeval/web/templates/web/{base,key_created,key_form,agent_detail}.html`,
  `docs/requirements/web.md`
- External: <https://docs.djangoproject.com/en/6.0/ref/settings/#secure-csp>,
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP>
