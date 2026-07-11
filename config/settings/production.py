"""Production settings (Fly.io + Neon).

Secrets arrive via `fly secrets set`. `DJANGO_SECRET_KEY`, `DATABASE_URL`, and
`DJANGO_ALLOWED_HOSTS` are required — no insecure defaults leak through.
"""

from .base import *
from .base import env_list, env_required

DEBUG = False

SECRET_KEY = env_required("DJANGO_SECRET_KEY")  # fail loudly if unset
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [])

# HTTPS / security hardening. Fly terminates TLS and sets X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host != "*"]
