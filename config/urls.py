"""Root URL configuration. The API (including the health check) lives under
`/api/`; the OpenAPI schema is served at `/api/openapi.json`. The human-facing
web UI (ADR-0006) is served at the site root.
"""

from django.contrib import admin
from django.urls import include, path

from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("maeval.web.urls")),
]
