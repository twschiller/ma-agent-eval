"""Test settings — fast, deterministic, no external services required."""

from .base import *
from .base import STORAGES

SECRET_KEY = "test-only-not-a-secret"  # nosec B105 — fixed non-secret test key
DEBUG = False

# Cheap password hashing keeps the suite fast.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Render `{% static %}` without a hashed manifest so template tests don't
# require a `collectstatic` run. See ADR-0006.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
