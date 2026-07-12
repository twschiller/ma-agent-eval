"""HTTP layer for submissions. Depends on schemas + models."""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import transaction
from django.db.models import F, QuerySet
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.responses import Status

from maeval.accounts.auth import ANY_PRINCIPAL, require_scope
from maeval.accounts.models import SCOPE_SUBMISSIONS_VOTE, SCOPE_SUBMISSIONS_WRITE, User
from maeval.submissions.models import Submission, Vote
from maeval.submissions.schemas import SubmissionIn, SubmissionOut

router = Router(tags=["submissions"])


@router.get("/", response=list[SubmissionOut], auth=None)
@paginate
def list_submissions(request, q: str | None = None) -> QuerySet[Submission]:  # noqa: ARG001
    """Public, unauthenticated, LimitOffset-paginated list of submissions.

    Newest first by default. Pass ``q`` for a full-text search over title and
    description, in which case results are ordered by relevance (see ADR-0005).
    """
    submissions = Submission.objects.select_related("author")
    if q:
        # `websearch` parses arbitrary user input safely (quotes, OR, -term)
        # without raising on syntax, so the public search box can't 500.
        # Pin `english` so stemming (library/libraries) is deterministic rather
        # than depending on the DB's default_text_search_config.
        query = SearchQuery(q, search_type="websearch", config="english")
        vector = SearchVector("title", "description", config="english")
        return (
            submissions.annotate(rank=SearchRank(vector, query))
            .filter(rank__gt=0)
            .order_by("-rank", "-created_at")
        )
    return submissions.all()


@router.post("/", response={201: SubmissionOut}, auth=ANY_PRINCIPAL)
def create_submission(request, payload: SubmissionIn) -> Status[Submission]:
    """Create a submission attributed to the authenticated principal.

    An agent needs the ``submissions:write`` scope; a human is unrestricted.
    ``submitted_by_agent`` is derived from the caller, not the request body.
    """
    require_scope(request, SCOPE_SUBMISSIONS_WRITE)
    principal: User = request.auth
    submission = Submission.objects.create(
        title=payload.title,
        description=payload.description,
        author=principal,
        submitted_by_agent=principal.is_agent,
    )
    return Status(201, submission)


@router.post("/{submission_id}/upvote", response=SubmissionOut, auth=ANY_PRINCIPAL)
def upvote_submission(request, submission_id: str) -> Submission:
    """Upvote a submission on behalf of the caller's human principal.

    Idempotent: a principal (a human and its agents together) counts once per
    submission, so a repeat call returns the current count without inflating it.
    An agent needs the ``submissions:vote`` scope.
    """
    require_scope(request, SCOPE_SUBMISSIONS_VOTE)
    caller: User = request.auth
    submission = get_object_or_404(Submission, pk=submission_id)
    with transaction.atomic():
        _vote, created = Vote.objects.get_or_create(submission=submission, voter=caller.principal)
        if created:
            Submission.objects.filter(pk=submission.pk).update(upvote_count=F("upvote_count") + 1)
    submission.refresh_from_db(fields=["upvote_count"])
    return submission
