"""Test settings — fast, deterministic, no external services required."""

from .base import *

SECRET_KEY = "test-only-not-a-secret"  # nosec B105 — fixed non-secret test key
DEBUG = False

# Cheap password hashing keeps the suite fast.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
