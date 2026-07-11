"""HTTP layer for submissions. Depends on schemas + models."""

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.responses import Status

from maeval.accounts.auth import ANY_PRINCIPAL, require_scope
from maeval.accounts.models import SCOPE_SUBMISSIONS_VOTE, SCOPE_SUBMISSIONS_WRITE, User
from maeval.submissions.models import Submission, Vote
from maeval.submissions.schemas import SubmissionIn, SubmissionOut

router = Router(tags=["submissions"])


@router.get("/", response=list[SubmissionOut], auth=None)
def list_submissions(request) -> list[Submission]:  # noqa: ARG001
    """Public, unauthenticated list of submissions ordered by newest first."""
    return list(Submission.objects.select_related("author").all())


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
