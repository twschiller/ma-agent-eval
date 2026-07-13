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
from maeval.traces.schemas import TraceDetailOut, TraceIn, TraceOut

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


@router.get("/{trace_id}", response=TraceDetailOut, auth=None)
def get_trace(request, trace_id: str) -> RunTrace:  # noqa: ARG001
    """Public, unauthenticated fetch of one trace *with* its transcript.

    The list endpoint stays lean (`TraceOut`); the transcript — which can be
    large — is served only here, per-id.
    """
    return get_object_or_404(RunTrace.objects.select_related("author"), pk=trace_id)


@router.post("/", response={201: TraceOut}, auth=ANY_PRINCIPAL)
def create_trace(request, payload: TraceIn) -> Status[RunTrace]:
    """Record a run trace attributed to the authenticated principal.

    An agent needs the ``traces:write`` scope; a human is unrestricted.
    ``submitted_by_agent`` is derived from the caller, not the request body.
    """
    require_scope(request, SCOPE_TRACES_WRITE)
    principal: User = request.auth
    submission = get_object_or_404(Submission, pk=payload.submission_id)
    # Already validated by the discriminated union on `TraceIn`; store the
    # plain-dict form (JSON-native) rather than the pydantic step models.
    transcript = [step.model_dump() for step in payload.transcript]
    trace = RunTrace.objects.create(
        submission=submission,
        author=principal,
        submitted_by_agent=principal.is_agent,
        model=payload.model,
        harness=payload.harness,
        # Derived from the transcript, not the request body (ADR-0011).
        tools=RunTrace.tools_used(transcript),
        outcome=payload.outcome,
        transcript=transcript,
    )
    return Status(201, trace)
