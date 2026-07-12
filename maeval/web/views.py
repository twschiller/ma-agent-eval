"""Server-rendered views for the human-facing web UI (see ADR-0006).

Read paths (home, list, search, detail, traces) are public. Write paths
(create submission, upvote) require a logged-in human principal — enforced by
``login_required`` and Django's session auth. Attribution (`author`,
`submitted_by_agent`) is derived from ``request.user``, never from posted data,
mirroring the API. Search and upvote reuse the shared model helpers
(`Submission.search`, `Vote.cast`) so behavior can't drift from the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from maeval.submissions.models import Submission, Vote
from maeval.traces.models import RunTrace
from maeval.web.forms import SignupForm, SubmissionForm

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from django_htmx.middleware import HtmxDetails

    from maeval.accounts.models import User

    class HtmxHttpRequest(HttpRequest):
        """The request as seen by these views: HtmxMiddleware adds ``htmx``."""

        htmx: HtmxDetails


# Keep pages small; the catalog is human-scale (see ADR-0005).
PAGE_SIZE = 20


def _has_voted(request: HtmxHttpRequest, submission: Submission) -> bool:
    """Whether the logged-in principal has already upvoted ``submission``."""
    if not request.user.is_authenticated:
        return False
    principal = cast("User", request.user).principal
    return Vote.objects.filter(submission=submission, voter=principal).exists()


def home(request: HtmxHttpRequest) -> HttpResponse:
    """Landing page with the most-upvoted tasks as a teaser."""
    top = Submission.objects.order_by("-upvote_count", "-created_at").select_related("author")[:5]
    return render(request, "web/home.html", {"top_submissions": top})


def submission_list(request: HtmxHttpRequest) -> HttpResponse:
    """Browse + full-text search submissions, paginated.

    An htmx request (the live search box, pagination links) gets just the
    results fragment; a normal request gets the full page.
    """
    q = request.GET.get("q", "").strip()
    submissions = Submission.search(q).select_related("author")
    page = Paginator(submissions, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {"page_obj": page, "q": q}
    template = "web/_submission_list.html" if request.htmx else "web/submission_list.html"
    return render(request, template, context)


def submission_detail(request: HtmxHttpRequest, submission_id: str) -> HttpResponse:
    """One task, its upvote control, and the run traces recorded against it."""
    submission = get_object_or_404(Submission.objects.select_related("author"), pk=submission_id)
    traces = RunTrace.objects.filter(submission=submission).select_related("author")
    return render(
        request,
        "web/submission_detail.html",
        {"submission": submission, "traces": traces, "has_voted": _has_voted(request, submission)},
    )


@login_required
def submission_create(request: HtmxHttpRequest) -> HttpResponse:
    """Create a submission attributed to the logged-in human principal."""
    if request.method == "POST":
        form = SubmissionForm(request.POST)
        if form.is_valid():
            user = cast("User", request.user)
            submission = form.save(commit=False)
            submission.author = user
            submission.submitted_by_agent = user.is_agent
            submission.save()
            return redirect("web:submission_detail", submission_id=submission.pk)
    else:
        form = SubmissionForm()
    return render(request, "web/submission_form.html", {"form": form})


@require_POST
@login_required
def submission_upvote(request: HtmxHttpRequest, submission_id: str) -> HttpResponse:
    """Upvote a submission (idempotent); returns the refreshed upvote control."""
    submission = get_object_or_404(Submission, pk=submission_id)
    Vote.cast(submission=submission, caller=request.user)
    submission.refresh_from_db(fields=["upvote_count"])
    return render(request, "web/_upvote.html", {"submission": submission, "has_voted": True})


def trace_list(request: HtmxHttpRequest) -> HttpResponse:
    """All recorded run traces, newest first, paginated."""
    traces = RunTrace.objects.select_related("author", "submission")
    page = Paginator(traces, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "web/trace_list.html", {"page_obj": page})


def signup(request: HtmxHttpRequest) -> HttpResponse:
    """Register a human principal and log them in."""
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("web:submission_list")
    else:
        form = SignupForm()
    return render(request, "web/signup.html", {"form": form})
