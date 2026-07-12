"""Root URL configuration. The API (including the health check) lives under
`/api/`; the OpenAPI schema is served at `/api/openapi.json`. The human-facing
web UI (ADR-0006) is served at the site root.
"""

from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url
from django.urls import include, path

from config.api import api

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def admin_login_redirect(request: HttpRequest) -> HttpResponse:
    """Route the admin's own login form through the primary session login.

    The staff admin has a single login surface — the site's `web:login` page —
    so an unauthenticated admin visitor is sent there (via `settings.LOGIN_URL`)
    with `next` preserved so they land back in the admin afterward.
    """
    return redirect_to_login(request.GET.get("next") or resolve_url("admin:index"))


urlpatterns = [
    # Must precede `admin/` so it shadows the admin app's built-in login view.
    path("admin/login/", admin_login_redirect),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("maeval.web.urls")),
]
