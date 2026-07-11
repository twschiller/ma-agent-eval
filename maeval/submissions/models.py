"""Submission domain models.

A *submission* is a query/task/job-to-be-done that someone wants an AI agent to
perform against MA/Boston civic services (e.g. "renew my library card"). This is
a starter model demonstrating the layering; flesh out per docs/requirements/.
"""

from django.conf import settings
from django.db import models

from maeval.common.models import TimestampedModel


class Submission(TimestampedModel):
    """A proposed agent-performable task, upvotable by the public."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Null author => submitted anonymously; set for authenticated humans/agents.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    # Distinguish content authored by an AI agent vs. a human principal.
    submitted_by_agent = models.BooleanField(default=False)
    upvote_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.title
