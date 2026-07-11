"""Ninja authenticators for the two principal kinds (see ADR-0003).

- humans authenticate management calls with HTTP Basic (username + password);
- agents authenticate with a bearer API key.

Whichever succeeds, ``request.auth`` is set to the acting :class:`User`, so
downstream code reads the principal uniformly and derives ``submitted_by_agent``
from ``request.auth.is_agent`` — the client never asserts it.
"""

from django.contrib.auth import authenticate
from django.utils import timezone
from ninja.errors import HttpError
from ninja.security import HttpBasicAuth, HttpBearer

from maeval.accounts.models import ApiKey, User


class HumanBasicAuth(HttpBasicAuth):
    """Authenticate a human principal by username + password."""

    def authenticate(self, request, username: str, password: str) -> User | None:
        user = authenticate(request, username=username, password=password)
        # Agents carry unusable passwords, so `authenticate` already excludes
        # them; the explicit guard makes the human-only contract obvious.
        if isinstance(user, User) and user.is_active and not user.is_agent:
            return user
        return None


class ApiKeyAuth(HttpBearer):
    """Authenticate an agent principal by ``Authorization: Bearer mae_…``."""

    def authenticate(self, request, token: str) -> User | None:
        key = ApiKey.resolve(token)
        if key is None:
            return None
        key.last_used_at = timezone.now()
        key.save(update_fields=["last_used_at"])
        # Expose the key so scoped write paths can check `key.scopes` later.
        request.api_key = key  # type: ignore[attr-defined]  # per-request stash
        return key.agent


# Both principal kinds may call shared endpoints (e.g. /me); order is
# irrelevant since Basic and Bearer use different Authorization schemes.
ANY_PRINCIPAL: list[object] = [HumanBasicAuth(), ApiKeyAuth()]


def require_scope(request, scope: str) -> None:
    """Enforce that an agent caller's presenting key carries ``scope``.

    Scopes constrain what an *agent* may do on its principal's behalf; a human
    over Basic auth acts with full authority and is never scope-limited. Agents
    authenticate via :class:`ApiKeyAuth`, which stashes the key on the request,
    so a missing stash means the caller is a human. Raises 403 for an agent
    whose key lacks the scope; call after auth has populated ``request.auth``.
    """
    key = getattr(request, "api_key", None)
    if key is not None and scope not in key.scopes:
        raise HttpError(403, f"missing required scope: {scope}")
