"""Submission domain models.

A *submission* is a query/task/job-to-be-done that someone wants an AI agent to
perform against MA/Boston civic services (e.g. "renew my library card"). See
`docs/requirements/submissions.md` for the behavioral contract.
"""

from typing import ClassVar

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models, transaction
from django.db.models import F

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

    @classmethod
    def search(cls, q: str | None) -> models.QuerySet[Submission]:
        """Full-text matches on title + description, ranked by relevance.

        Empty/None ``q`` is a no-op (returns all, newest-first) so browse and
        search share one path. Uses `websearch` parsing so arbitrary user input
        can't raise; the `english` config pins stemming. See ADR-0005. Shared by
        the API list endpoint and the web list view — one FTS implementation, no
        drift.
        """
        submissions = cls.objects.all()
        if not q:
            # Explicit ordering (the Meta default), not just implicit: a caller
            # that annotates aggregates onto this queryset adds a GROUP BY, which
            # makes Django treat an implicitly-ordered queryset as unordered (a
            # spurious Paginator warning) even though `-created_at` still applies.
            return submissions.order_by("-created_at")
        query = SearchQuery(q, search_type="websearch", config="english")
        vector = SearchVector("title", "description", config="english")
        # Filter on the `@@` match operator (`vector=query`), not `rank > 0`:
        # for a phrase query that doesn't match, Postgres `ts_rank` returns a
        # tiny non-zero (~1e-20), so a `rank__gt=0` filter would let every row
        # through. `@@` is the correct membership test; rank only orders.
        return (
            submissions.annotate(search=vector, rank=SearchRank(vector, query))
            .filter(search=query)
            .order_by("-rank", "-created_at")
        )


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

    @classmethod
    def cast(cls, *, submission: Submission, caller: object) -> None:
        """Record ``caller``'s principal upvote of ``submission``.

        Idempotent: the vote attributes to the caller's human *principal*, so a
        human and its agents together count at most once, and the denormalized
        ``upvote_count`` is bumped only on a first vote. Shared by the API
        upvote endpoint and the web upvote view so the vote-attribution
        semantics can't drift. ``caller`` is the acting principal (``User``);
        callers refresh ``submission`` if they need the updated count.
        """
        with transaction.atomic():
            _vote, created = cls.objects.get_or_create(
                submission=submission,
                voter=caller.principal,  # type: ignore[attr-defined]  # User.principal
            )
            if created:
                Submission.objects.filter(pk=submission.pk).update(
                    upvote_count=F("upvote_count") + 1
                )
