"""Render agent/human transcript prose as Markdown, then sanitize to a strict
allowlist (ADR-0012).

Transcript content is untrusted — authored by agents and humans, stored
verbatim (ADR-0011). Markdown-to-HTML is an escaping-loss surface exactly like
the one ADR-0010's CSP was written to backstop, so we never trust the Markdown
library's output: every render is run through ``nh3`` (Rust/ammonia) against an
explicit tag/attribute allowlist. The CSP is defense-in-depth *behind* this, not
instead of it.

The allowlist is deliberately narrow — the tags Python-Markdown emits for the
subset of extensions we enable, minus anything that loads an external resource
(`img`), carries interactivity/attributes (`attr_list`, inline styles), or lets
content escape the flow. Links are capped to safe schemes and get
``rel="nofollow noopener noreferrer"``. Anything outside the allowlist is
stripped, so an enabled-but-abused extension (e.g. `attr_list` classes/ids) is
neutralized even if it slips in.
"""

from __future__ import annotations

import markdown as md
import nh3

# The subset we render. Each extension maps onto tags that are in the allowlist
# below; adding one means widening the allowlist to match.
#   fenced_code — ``` blocks (agents paste code/JSON) -> <pre><code>
#   tables      — pipe tables -> <table>…
#   sane_lists  — don't fold loose text into adjacent lists
#   nl2br       — treat a single newline as <br>, matching the prior
#                 `linebreaksbr` behavior transcript readers expect
_EXTENSIONS = ["fenced_code", "tables", "sane_lists", "nl2br"]

# Exactly the tags the extensions above produce. No `img` (external fetch /
# tracking, and CSP img-src would block it anyway), no `attr_list`-style
# attributes, no inline styles.
_ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "hr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "em",
        "b",
        "i",
        "del",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "a",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)

# Links keep only href/title; everything else (target, class, id, on*) is dropped.
_ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}

# No `javascript:`/`data:` URLs — only what a transcript legitimately links to.
_ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})


def render_markdown(text: str) -> str:
    """Render ``text`` as Markdown and return sanitized, safe-to-emit HTML.

    The return value has already passed the allowlist sanitizer, so callers
    mark it safe for the template. Never feed the raw Markdown-library output to
    a template without this step.
    """
    # A fresh converter per call: the Markdown instance is stateful across
    # conversions (it accumulates footnote/reference state), and traces render
    # independently.
    html = md.markdown(text, extensions=_EXTENSIONS, output_format="html")
    return nh3.clean(
        html,
        tags=set(_ALLOWED_TAGS),
        attributes={tag: set(attrs) for tag, attrs in _ALLOWED_ATTRIBUTES.items()},
        url_schemes=set(_ALLOWED_URL_SCHEMES),
        link_rel="nofollow noopener noreferrer",
    )
