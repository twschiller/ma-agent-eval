"""Template filters for the web UI.

Kept deliberately small: presentation-only helpers the templates can't express
directly. Nothing here reaches the DB or holds business logic.
"""

import json

from django import template

register = template.Library()


@register.filter(name="to_json")
def to_json(value: object) -> str:
    """Pretty-print a JSON-native value for display (e.g. a tool call's input).

    Output is a plain string rendered inside a ``<pre>``; it is *not* marked
    safe, so Django autoescapes it — untrusted transcript content can't inject
    markup. ``ensure_ascii=False`` keeps non-Latin text readable rather than
    ``\\uXXXX``-escaped.
    """
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
