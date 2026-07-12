"""Identity models: principals (human + agent users) and their API keys.

A *principal* is anyone who can act against the API. There are two kinds, both
rows in one ``User`` table (see ADR-0003):

- a **human** — ``is_agent = False``, ``parent = None``, authenticates with a
  password;
- an **agent** — ``is_agent = True``, ``parent`` set to the human that operates
  it, authenticates with an :class:`ApiKey`.

Modeling agents as users gives every agent its own username for attribution and
lets content, votes, and traces point at a single ``author`` foreign key
regardless of principal kind.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING, ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from maeval.common.models import new_ulid

if TYPE_CHECKING:
    from datetime import datetime

# Permission scopes an API key may be granted. Kept deliberately small; new
# write paths add their scope here and check it at the view.
SCOPE_SUBMISSIONS_WRITE = "submissions:write"
SCOPE_SUBMISSIONS_VOTE = "submissions:vote"
SCOPE_TRACES_WRITE = "traces:write"
SCOPES: frozenset[str] = frozenset(
    {SCOPE_SUBMISSIONS_WRITE, SCOPE_SUBMISSIONS_VOTE, SCOPE_TRACES_WRITE}
)

# Presented API key looks like ``mae_<prefix>_<secret>``. Both halves are hex,
# so the separator is unambiguous. Only the prefix (lookup) and a SHA-256 of the
# secret are stored; the raw key is shown once and never persisted.
_KEY_NAMESPACE = "mae"
_PREFIX_BYTES = 4  # 8 hex chars
_SECRET_BYTES = 32  # 64 hex chars


class User(AbstractUser):
    """A principal — a human account or one of its AI agents (see ADR-0003)."""

    id = models.CharField(primary_key=True, max_length=26, default=new_ulid, editable=False)
    # True for AI agents. Drives `submitted_by_agent` on authored content; set by
    # the identity layer, never by a client request.
    is_agent = models.BooleanField(default=False)
    # The human that operates this agent. NULL for humans; deleting a human
    # cascades to its agents (moderation deletes a principal and its agents).
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="agents",
    )

    class Meta(AbstractUser.Meta):
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # An agent has a parent; a human has none. Keeps the two principal
            # kinds coherent at the database, not just in application code.
            models.CheckConstraint(
                name="agent_has_parent_human_has_none",
                condition=(
                    models.Q(is_agent=True, parent__isnull=False)
                    | models.Q(is_agent=False, parent__isnull=True)
                ),
            ),
        ]

    @property
    def principal(self) -> User:
        """The human account this identity belongs to (itself, if human)."""
        return self.parent if self.is_agent and self.parent else self

    @classmethod
    def create_agent(cls, *, username: str, parent: User, **extra: object) -> User:
        """Create an agent user owned by ``parent`` (a human principal).

        Agents authenticate only by API key, so the password is left unusable.
        """
        agent = cls(username=username, is_agent=True, parent=parent, **extra)
        agent.set_unusable_password()
        agent.full_clean(exclude=["password"])
        agent.save()
        return agent


class ApiKey(models.Model):
    """A named, scoped credential an agent presents as a bearer token.

    Stored as ``prefix`` (non-secret, for lookup) plus a SHA-256 hash of the
    secret half. The raw key is returned once at creation and never persisted.
    """

    id = models.CharField(primary_key=True, max_length=26, default=new_ulid, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=8, unique=True, editable=False)
    hashed_secret = models.CharField(max_length=64, editable=False)
    scopes = models.JSONField(default=list)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    # When the key stops authenticating. Chosen by the issuing human; NULL means
    # the key never expires. Enforced in `resolve` alongside revocation.
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}…)"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and not self.is_expired

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    @classmethod
    def issue(
        cls,
        *,
        agent: User,
        name: str,
        scopes: list[str],
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """Mint a key for ``agent``; return the row and the one-time raw token.

        ``expires_at`` is optional — omit it for a non-expiring key. The raw
        token carries the ``mae_`` namespace prefix so a leaked key is
        recognizable (e.g. to secret scanners) as one of ours.
        """
        prefix = secrets.token_hex(_PREFIX_BYTES)
        secret = secrets.token_hex(_SECRET_BYTES)
        key = cls.objects.create(
            agent=agent,
            name=name,
            prefix=prefix,
            hashed_secret=cls._hash_secret(secret),
            scopes=scopes,
            expires_at=expires_at,
        )
        raw = f"{_KEY_NAMESPACE}_{prefix}_{secret}"
        return key, raw

    @classmethod
    def resolve(cls, raw: str) -> ApiKey | None:
        """Return the active key matching ``raw``, or None. Constant-time compare."""
        parts = raw.split("_")
        if len(parts) != 3 or parts[0] != _KEY_NAMESPACE:
            return None
        _, prefix, secret = parts
        try:
            key = cls.objects.get(prefix=prefix, revoked_at__isnull=True)
        except cls.DoesNotExist:
            return None
        if not hmac.compare_digest(key.hashed_secret, cls._hash_secret(secret)):
            return None
        if key.is_expired:
            return None
        return key
