"""Root URL configuration. The API (including the health check) lives under
`/api/`; the OpenAPI schema is served at `/api/openapi.json`.
"""

from django.contrib import admin
from django.urls import path

from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
