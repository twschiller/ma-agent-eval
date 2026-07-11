"""Base settings shared by every environment.

Environment-specific modules (`local`, `production`, `test`) import `*` from
here and override. Read config from the environment via django-environ; never
hardcode secrets.
"""

import os
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
    # Local apps
    "maeval.common",
    "maeval.submissions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
