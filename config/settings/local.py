"""Local development settings."""

from .base import *
from .base import STORAGES

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # nosec B104 — dev server only

# Serve static without a hashed manifest so `{% static %}` resolves before any
# `collectstatic` run; the manifest storage stays in production. See ADR-0006.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
