"""Base settings shared by every environment.

Environment-specific modules (`local`, `production`, `test`) import `*` from
here and override. Read config from the environment via django-environ; never
hardcode secrets.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def env_required(key: str) -> str:
    """Return an env var or raise — for prod settings with no safe default."""
    value = os.environ.get(key)
    if value is None:
        raise ImproperlyConfigured(f"Set the {key} environment variable")
    return value


def env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: list[str]) -> list[str]:
    raw = os.environ.get(key)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# Optionally load a local .env file (guarded so prod never reads one).
if env_bool("DJANGO_READ_DOT_ENV_FILE"):
    environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "insecure-dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Postgres full-text search lookups (SearchVector/SearchRank); Postgres in
    # every environment, so no SQLite fallback to design around. See ADR-0005.
    "django.contrib.postgres",
    # Third-party
    "django_htmx",
    # Brute-force / credential-stuffing protection for the login + HTTP Basic
    # auth paths (records failed attempts, locks out after a threshold).
    "axes",
    # Local apps
    "maeval.common",
    "maeval.accounts",
    "maeval.submissions",
    "maeval.traces",
    "maeval.web",
]

# Agents and humans are both rows in this custom user model (see ADR-0003).
AUTH_USER_MODEL = "accounts.User"

# Every list endpoint is LimitOffset-paginated with a {items, count} envelope
# (Ninja's default pagination class). Cap the page size so an agent client can't
# request an unbounded page; the default limit when none is given is 100.
NINJA_PAGINATION_MAX_LIMIT = 100

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Sets `request.htmx` for the web UI; needs the session/auth middleware
    # above it. See ADR-0006.
    "django_htmx.middleware.HtmxMiddleware",
    # Must come last and after AuthenticationMiddleware: axes wraps the login
    # flow to record failures and short-circuit locked-out callers.
    "axes.middleware.AxesMiddleware",
]

# django-axes plugs in as an authentication backend (checked first) so a
# locked-out principal is rejected before the real backend runs. AxesStandalone
# only enforces the lockout; ModelBackend still verifies the password.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Brute-force lockout policy (django-axes). Lock on the (username, IP) pair so a
# shared NAT / office IP can't lock out unrelated users, while still stopping a
# password-guessing run against one account. Applies to the web login form and
# the API's HTTP Basic path — both route through Django's `authenticate()`.
AXES_FAILURE_LIMIT = env_int("DJANGO_AXES_FAILURE_LIMIT", 5)
AXES_COOLOFF_TIME = timedelta(minutes=env_int("DJANGO_AXES_COOLOFF_MINUTES", 30))
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_HTTP_RESPONSE_CODE = 429
# Behind Fly's proxy the client IP arrives in X-Forwarded-For; trust it for
# attribution (the same proxy already terminates TLS, see SECURE_PROXY_SSL_HEADER
# in production settings). REMOTE_ADDR is the local fallback for dev.
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]

ROOT_URLCONF = "config.urls"

# Web UI session auth (ADR-0006). Agents never session-log-in; they use API
# keys. `next`-less redirects land on the submissions catalog / home.
LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:submission_list"
LOGOUT_REDIRECT_URL = "web:home"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# dj-database-url parses DATABASE_URL (Postgres in every environment).
DATABASES = {
    "default": dj_database_url.parse(
        env_str("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/app"),
        conn_max_age=600,
    ),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
