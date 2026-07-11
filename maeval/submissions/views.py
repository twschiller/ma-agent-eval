"""HTTP layer for submissions. Depends on schemas + models."""

from ninja import Router

from maeval.submissions.models import Submission
from maeval.submissions.schemas import SubmissionOut

router = Router(tags=["submissions"])


@router.get("/", response=list[SubmissionOut], auth=None)
def list_submissions(request) -> list[Submission]:  # noqa: ARG001
    """Public, unauthenticated list of submissions ordered by newest first."""
    return list(Submission.objects.all())
