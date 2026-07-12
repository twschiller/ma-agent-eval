"""Ninja I/O schemas for the accounts app."""

# Runtime (not type-only) import: `datetime` is a pydantic field type on the
# schemas below, so it must resolve at runtime — a TYPE_CHECKING block would
# break Ninja's request parsing/validation.
from datetime import datetime  # noqa: TC003

from ninja import Schema
from pydantic import Field


class SignupIn(Schema):
    username: str
    password: str
    email: str = ""


class UserOut(Schema):
    id: str
    username: str
    email: str
    is_agent: bool
    # The human principal that owns an agent; null for human accounts.
    parent_id: str | None = None


class AgentIn(Schema):
    username: str


class ApiKeyIn(Schema):
    name: str
    scopes: list[str] = Field(default_factory=list)
    # Optional expiry chosen by the issuing human; omit for a non-expiring key.
    # Must be in the future — the view rejects a past instant.
    expires_at: datetime | None = None


class ApiKeyOut(Schema):
    """API key metadata. Never carries the secret."""

    id: str
    name: str
    prefix: str
    scopes: list[str]
    # Null for a non-expiring key.
    expires_at: datetime | None = None


class ApiKeyCreatedOut(ApiKeyOut):
    """Returned once, at creation — the only time the raw key is exposed."""

    api_key: str
