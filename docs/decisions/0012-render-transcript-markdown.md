---
status: accepted
date: 2026-07-12
---

# Render transcript prose as Markdown behind an allowlist sanitizer

## Context and Problem Statement

Run-trace transcripts (ADR-0011) store the natural-language steps — `user`,
`assistant`, `reasoning` — as plain text, rendered with `linebreaksbr`. But
agents and models emit Markdown: headings, lists, tables, fenced code, emphasis.
Shown raw, that reads as a wall of asterisks and pipes instead of the structured
output it is, which undercuts the point of a transcript viewer. We want to render
it as Markdown. The content is **untrusted** — authored by agents/humans and
stored verbatim — so the question is how to render rich text without opening the
injection hole that Django's autoescaping currently closes. ADR-0010 named this
exact case ("a future markdown/rich-text feature") as why the CSP exists. This
decision covers rendering + sanitization of the three prose step kinds; the
`tool_call`/`tool_result` steps stay mono code blocks (machine data, unchanged).

## Considered Options

- **Python-Markdown + `nh3`, allowlist-sanitized, at render time.** Most-used
  Python Markdown library; `nh3` (Rust/ammonia) is the maintained successor to
  the now-archived `bleach`. Render to HTML, then strip everything outside an
  explicit tag/attribute allowlist before it reaches the template.
- **`bleach` as the sanitizer** instead of `nh3` — historically the most-used
  sanitizer, but archived/unmaintained since 2023.
- **Sanitize once on ingest, store HTML.** Render + clean when the trace is
  submitted; store the safe HTML.
- **Client-side rendering** (ship the Markdown, render in JS).
- **Keep plain text** (`linebreaksbr`, the status quo).

## Decision Outcome

Chosen option: "Python-Markdown + `nh3`, sanitized at render time", because it
pairs the most popular renderer with a *maintained* allowlist sanitizer, and
sanitizing on read keeps the stored transcript the verbatim evidence ADR-0011
requires (re-sanitizing on read also means an allowlist tightening applies to
already-stored traces, no backfill). `bleach` was rejected as an EOL dependency
this security-conscious repo shouldn't adopt. Client-side rendering was rejected
because it needs inline/eval script the CSP forbids (ADR-0010) and moves a
security boundary into the browser. Plain text is the gap this closes.

The render never trusts the Markdown library: `maeval/web/markdown.py` runs every
conversion through `nh3` against a narrow allowlist — the tags the enabled
extensions (`fenced_code`, `tables`, `sane_lists`, `nl2br`) actually emit, and
nothing that fetches an external resource (`img`), carries inline
styles/attributes (`attr_list`), or executes. Links are capped to
`http`/`https`/`mailto` and rewritten with `rel="nofollow noopener noreferrer"`.
The template filter (`maeval_extras.markdown`) only `mark_safe`s output that has
already passed the sanitizer. The CSP is defense-in-depth *behind* this, not the
primary wall.

### Consequences

- Good, because transcripts render as the structured Markdown agents emit, so the
  viewer shows evidence the way it was produced.
- Good, because sanitization is a single choke point (`render_markdown`) with an
  explicit allowlist — the abusable Markdown extensions (`attr_list` ids/classes,
  raw HTML) are neutralized even if enabled, and links can't carry `javascript:`.
- Good, because rendering on read keeps the stored step verbatim (ADR-0011) and
  lets a future allowlist change cover existing traces without a migration.
- Bad, because Markdown is rendered on every page view rather than cached; the
  transcript step cap (ADR-0011) bounds the work, so we accept it until it shows.
- Bad, because we now own a rendering + sanitization surface: a new Markdown
  extension means widening the allowlist in lockstep, or its tags get stripped.
- Locks in: the allowlist is enforced by tests in `maeval/web/tests/test_web.py`
  (script/event-handler/`javascript:`-scheme/image stripping, link hardening); a
  regression that emits unsanitized HTML fails them. `mark_safe` is confined to
  the one filter that wraps sanitizer output.

## More Information

- Extends: ADR-0011 (run-trace transcripts), ADR-0010 (content-security-policy)
- Files: `maeval/web/markdown.py`, `maeval/web/templatetags/maeval_extras.py`,
  `maeval/web/templates/web/trace_detail.html`,
  `maeval/web/static/web/css/maeval.css`, `docs/requirements/web.md`
- External: <https://python-markdown.github.io/>, <https://nh3.readthedocs.io/>,
  bleach deprecation: <https://github.com/mozilla/bleach>
