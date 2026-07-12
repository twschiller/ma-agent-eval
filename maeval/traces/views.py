"""HTTP layer for run traces. Depends on schemas + models + accounts auth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.responses import Status

from maeval.accounts.auth import ANY_PRINCIPAL, require_scope
from maeval.accounts.models import SCOPE_TRACES_WRITE, User
from maeval.submissions.models import Submission
from maeval.traces.models import RunTrace
from maeval.traces.schemas import TraceIn, TraceOut

if TYPE_CHECKING:
    from django.db.models import QuerySet

router = Router(tags=["traces"])


@router.get("/", response=list[TraceOut], auth=None)
@paginate
def list_traces(request, submission_id: str | None = None) -> QuerySet[RunTrace]:  # noqa: ARG001
    """Public, unauthenticated, LimitOffset-paginated list of run traces, newest first.

    Pass ``submission_id`` to see only the runs recorded against one task.
    """
    traces = RunTrace.objects.select_related("author")
    if submission_id is not None:
        traces = traces.filter(submission_id=submission_id)
    return traces


@router.post("/", response={201: TraceOut}, auth=ANY_PRINCIPAL)
def create_trace(request, payload: TraceIn) -> Status[RunTrace]:
    """Record a run trace attributed to the authenticated principal.

    An agent needs the ``traces:write`` scope; a human is unrestricted.
    ``submitted_by_agent`` is derived from the caller, not the request body.
    """
    require_scope(request, SCOPE_TRACES_WRITE)
    principal: User = request.auth
    submission = get_object_or_404(Submission, pk=payload.submission_id)
    trace = RunTrace.objects.create(
        submission=submission,
        author=principal,
        submitted_by_agent=principal.is_agent,
        model=payload.model,
        harness=payload.harness,
        tools=payload.tools,
        outcome=payload.outcome,
    )
    return Status(201, trace)
