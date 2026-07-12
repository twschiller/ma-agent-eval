"""Submission domain models.

A *submission* is a query/task/job-to-be-done that someone wants an AI agent to
perform against MA/Boston civic services (e.g. "renew my library card"). See
`docs/requirements/submissions.md` for the behavioral contract.
"""

from typing import ClassVar

from django.conf import settings
from django.db import models

from maeval.common.models import TimestampedModel


class Submission(TimestampedModel):
    """A proposed agent-performable task, upvotable by the public."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # The authoring principal. Set at creation from the authenticated caller;
    # for an agent it points at the agent user (whose username attributes the
    # content). Deleting the principal cascades to its content — how moderation
    # removes a bad actor's submissions (see ADR-0004). Nullable only for
    # author-less rows created directly (seed/tests), never via the API.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    # Distinguish content authored by an AI agent vs. a human principal. Derived
    # from the caller (`author.is_agent`), never asserted by the request body.
    submitted_by_agent = models.BooleanField(default=False)
    # Denormalized count of related Vote rows, kept in step on each upvote.
    upvote_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.title


class Vote(TimestampedModel):
    """One principal's upvote of one submission.

    Votes attribute to the human *principal* (an agent's vote counts for the
    human that operates it), so a human and its agents together upvote a given
    submission at most once — enforced by the unique constraint below.
    """

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="votes")
    # `votes_cast`, not `votes`, so `user.votes_cast` (votes a principal made)
    # reads distinctly from `submission.votes` (votes on a submission).
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes_cast"
    )

    class Meta(TimestampedModel.Meta):
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["submission", "voter"], name="one_vote_per_voter_per_submission"
            ),
        ]

    def __str__(self) -> str:
        return f"vote {self.pk}"
