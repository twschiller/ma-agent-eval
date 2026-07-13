"""Template filters for the web UI.

Kept deliberately small: presentation-only helpers the templates can't express
directly. Nothing here reaches the DB or holds business logic.
"""

import json

from django import template
from django.utils.safestring import SafeString, mark_safe

from maeval.web.markdown import render_markdown

register = template.Library()


@register.filter(name="markdown")
def markdown(value: str | None) -> SafeString:
    """Render untrusted transcript prose as sanitized Markdown (ADR-0012).

    The heavy lifting — render then allowlist-sanitize — lives in
    ``maeval.web.markdown``; this only marks the already-sanitized HTML safe so
    the template emits it as markup. ``mark_safe`` here is sound precisely
    *because* ``render_markdown`` returns sanitizer output, never raw HTML.
    """
    # noqa/nosec: mark_safe is sound here because render_markdown returns
    # allowlist-sanitized (nh3) HTML, never raw input — the reason this filter exists.
    return mark_safe(render_markdown(value or ""))  # noqa: S308  # nosec B308 B703


@register.filter(name="to_json")
def to_json(value: object) -> str:
    """Pretty-print a JSON-native value for display (e.g. a tool call's input).

    Output is a plain string rendered inside a ``<pre>``; it is *not* marked
    safe, so Django autoescapes it — untrusted transcript content can't inject
    markup. ``ensure_ascii=False`` keeps non-Latin text readable rather than
    ``\\uXXXX``-escaped.
    """
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
