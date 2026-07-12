from django.apps import AppConfig


class WebConfig(AppConfig):
    """Server-rendered, human-facing web UI (see ADR-0006).

    Holds no models — it renders the submissions/traces/accounts domains as
    Bootstrap + htmx pages. The API contract (`config/api.py`) is unaffected.
    """

    name = "maeval.web"
    label = "web"
