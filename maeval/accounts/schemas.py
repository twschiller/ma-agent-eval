"""Ninja I/O schemas for the accounts app."""

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


class ApiKeyOut(Schema):
    """API key metadata. Never carries the secret."""

    id: str
    name: str
    prefix: str
    scopes: list[str]


class ApiKeyCreatedOut(ApiKeyOut):
    """Returned once, at creation — the only time the raw key is exposed."""

    api_key: str
