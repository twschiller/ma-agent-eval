"""Shared model infrastructure. Importable from anywhere (utility layer)."""

from typing import ClassVar

from django.db import models
from ulid import ULID


def new_ulid() -> str:
    """Return a fresh lexicographically-sortable ULID as a 26-char string."""
    return str(ULID())


class TimestampedModel(models.Model):
    """Abstract base: ULID primary key plus created/updated timestamps.

    ULIDs sort by creation time and don't leak row counts the way sequential
    integer ids do — useful for a public, agent-facing API.
    """

    id = models.CharField(primary_key=True, max_length=26, default=new_ulid, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering: ClassVar[list[str]] = ["-created_at"]
